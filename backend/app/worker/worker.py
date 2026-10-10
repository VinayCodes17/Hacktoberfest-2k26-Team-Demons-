import asyncio
import json
import logging
from dataclasses import dataclass
from time import monotonic
from uuid import uuid4

from sqlalchemy import Engine

from app.contracts import Taxonomy, require_classification_taxonomy
from app.persistence.database import schema_ready
from app.persistence.repository import claim_job_row_lease, record_prediction
from app.routing.ontology import OntologyProvider
from app.schemas import CanonicalTransaction, ModelProposal
from app.settings import Settings
from app.verification.verifier import VERIFIER_VERSION, Verifier, meaningful_missing
from app.worker.llm import generate_classification
from app.worker.prompt import build_prompt

logger = logging.getLogger(__name__)


@dataclass
class WorkerState:
    last_tick: float = 0
    running: bool = False
    error: bool = False

    @property
    def ready(self):
        return self.running and not self.error and monotonic() - self.last_tick < 180


def process_job_row(engine: Engine, settings: Settings, worker_id: str):
    lease = claim_job_row_lease(engine, worker_id, lease_duration_seconds=300)
    if not lease:
        return False
    row, source, job, attempt, previous_error = lease
    try:
        transaction = CanonicalTransaction.model_validate_json(json.dumps(source.payload))
        if transaction.id != source.id or any(
            s.dataset_id != source.dataset_id
            or s.sheet != source.sheet
            or s.physical_row != source.physical_row
            for s in transaction.sources
        ):
            raise ValueError("SOURCE_IDENTITY_MISMATCH")
        taxonomy = Taxonomy.model_validate(job.harness_snapshot["taxonomy"])
        require_classification_taxonomy(taxonomy)
        if job.harness_snapshot["model_digest"] != settings.gemma_model_digest:
            raise ValueError("HARNESS_MODEL_MISMATCH")
        ontology = OntologyProvider.from_taxonomy(taxonomy)
        verifier = Verifier(ontology)
        prompt = build_prompt(transaction.model_dump(mode="json"), job.mapping_snapshot, taxonomy, previous_error)
        proposal = ModelProposal.model_validate(generate_classification(prompt, settings))
        proposal.missing_evidence = meaningful_missing(proposal.missing_evidence)
        status, reasons = verifier.verify(proposal, transaction)
        if not proposal.evidence_paths and status == "accepted":
            status, reasons = "review", ["NO_OBSERVED_EVIDENCE"]
        decision = {
            **proposal.model_dump(),
            "status": status,
            "reason_codes": reasons,
            "attempts": attempt,
            "trace_id": f"{job.id}:{source.id}",
            "harness_id": job.harness_id,
            "verification_version": VERIFIER_VERSION,
            "prompt_version": "direct-v3",
        }
        if status == "error":
            record_prediction(
                engine, job.id, source.id, attempt, error="INVALID_PROPOSAL", worker_id=worker_id
            )
        else:
            record_prediction(engine, job.id, source.id, attempt, payload=decision, worker_id=worker_id)
    except Exception:
        logger.warning("classification_attempt_failed")
        record_prediction(
            engine, job.id, source.id, attempt, error="CLASSIFICATION_ATTEMPT_FAILED", worker_id=worker_id
        )
    return True


async def run_worker(
    engine: Engine, settings: Settings, worker_id: str | None = None, state: WorkerState | None = None
):
    state = state or WorkerState()
    worker_id = worker_id or f"worker-{uuid4()}"
    state.running = True
    try:
        while True:
            try:
                if not await asyncio.to_thread(schema_ready, engine):
                    raise ValueError("DATABASE_NOT_READY")
                state.error = False
                state.last_tick = monotonic()
                processed = await asyncio.to_thread(process_job_row, engine, settings, worker_id)
                state.last_tick = monotonic()
                if not processed:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception:
                state.error = True
                logger.warning("classification_worker_unavailable")
                await asyncio.sleep(2)
    finally:
        state.running = False
