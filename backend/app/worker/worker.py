import asyncio
import logging
from uuid import uuid4
from pathlib import Path

from sqlalchemy import Engine

from app.persistence.repository import claim_job_row_lease, record_prediction
from app.settings import Settings
from app.verification.verifier import Verifier
from app.routing.ontology import OntologyProvider
from app.schemas import ModelProposal, CanonicalTransaction, SourceRow
from app.worker.llm import OllamaAdapterError, generate_classification
from app.worker.prompt import build_prompt

logger = logging.getLogger(__name__)


def process_job_row(engine: Engine, settings: Settings, worker_id: str):
    """Attempt to claim and process a single job row."""
    lease_result = claim_job_row_lease(engine, worker_id, lease_duration_seconds=300)
    if not lease_result:
        return False

    row, source_record, job, attempt_number = lease_result

    max_attempts = 2

    # Instantiate properly with the DB session in a real flow
    verifier = Verifier(OntologyProvider(Path("ontology/workbook-seed.json")))

    # Create dummy CanonicalTransaction (real flow would parse source_record.payload)
    transaction = CanonicalTransaction(
        id=str(source_record.id),
        sources=[SourceRow(
            dataset_id="mock", sheet="mock", physical_row=1,
            source_sha256="a" * 64, cells=[]
        )]
    )

    try:
        # Build prompt using the raw source record and mapping snapshot
        prompt = build_prompt(transaction=source_record.payload, mapping_snapshot=job.mapping_snapshot)

        # Call LLM
        prediction_payload = generate_classification(prompt, settings)
        
        proposal = ModelProposal(**prediction_payload)
        status, reason_codes = verifier.verify(proposal, transaction)

        if status == "error" and attempt_number < max_attempts:
            # Recovery loop
            recovery_prompt = (
                prompt + f"\n\nYOUR PREVIOUS OUTPUT HAD ERRORS: {reason_codes}. PLEASE FIX THEM."
            )
            prediction_payload = generate_classification(recovery_prompt, settings)
            proposal = ModelProposal(**prediction_payload)
            status, reason_codes = verifier.verify(proposal, transaction)
            attempt_number += 1

        decision = {
            "status": status,
            "reason_codes": reason_codes,
            "attempts": attempt_number,
            "trace_id": f"trace-{source_record.id}",
            "harness_id": job.harness_id,
            "proposed_label": proposal.proposed_label
        }

        # Save prediction
        record_prediction(engine, job.id, source_record.id, attempt_number, payload=decision, error=None)
        logger.info(
            f"Successfully processed transaction {source_record.id} for job {job.id} with status {status}"
        )

    except OllamaAdapterError as e:
        logger.error(f"Ollama adapter error for transaction {source_record.id}: {e}")
        record_prediction(engine, job.id, source_record.id, attempt_number, payload=None, error=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error processing transaction {source_record.id}")
        record_prediction(engine, job.id, source_record.id, attempt_number, payload=None, error=str(e))

    return True


async def run_worker(engine: Engine, settings: Settings, worker_id: str | None = None):
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
