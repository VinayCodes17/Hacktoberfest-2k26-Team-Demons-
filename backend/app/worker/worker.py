import asyncio
import logging
from uuid import uuid4

from sqlalchemy import Engine

from app.persistence.repository import claim_job_row_lease, record_prediction
from app.settings import Settings
from app.worker.llm import generate_classification, OllamaAdapterError
from app.worker.prompt import build_prompt


logger = logging.getLogger(__name__)


def process_job_row(engine: Engine, settings: Settings, worker_id: str):
    """Attempt to claim and process a single job row."""
    lease_result = claim_job_row_lease(engine, worker_id, lease_duration_seconds=300)
    if not lease_result:
        return False

    row, source_record, job, attempt_number = lease_result

    try:
        # Build prompt using the raw source record and mapping snapshot
        # For a robust system, we just pass the payload directly and let the LLM map it
        # using the provided mapping snapshot.
        prompt = build_prompt(transaction=source_record.payload, mapping_snapshot=job.mapping_snapshot)

        # Call LLM
        prediction = generate_classification(prompt, settings)

        # Save prediction
        record_prediction(engine, job.id, source_record.id, attempt_number, payload=prediction, error=None)
        logger.info(f"Successfully processed transaction {source_record.id} for job {job.id}")

    except OllamaAdapterError as e:
        logger.error(f"Ollama adapter error for transaction {source_record.id}: {e}")
        record_prediction(engine, job.id, source_record.id, attempt_number, payload=None, error=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error processing transaction {source_record.id}")
        record_prediction(engine, job.id, source_record.id, attempt_number, payload=None, error=str(e))

    return True


async def run_worker(engine: Engine, settings: Settings, worker_id: str = None):
    """Background loop to continuously poll for available job rows."""
    if not worker_id:
        worker_id = f"worker-{uuid4()}"

    logger.info(f"Starting worker {worker_id}")

    while True:
        try:
            processed_any = await asyncio.to_thread(process_job_row, engine, settings, worker_id)
            if not processed_any:
                # No jobs available, sleep briefly
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            logger.info("Worker cancelled")
            break
        except Exception as e:
            logger.error(f"Worker encountered a fatal error: {e}")
            await asyncio.sleep(5)  # backoff
