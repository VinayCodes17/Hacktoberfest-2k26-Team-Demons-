"""Short transactions only. This module never calls an inference service."""
import copy
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.persistence.models import Dataset, HarnessRecord, Job, MappingRecord
from app.schemas import JobCreate, JobView


class VersionConflict(ValueError):
    pass


def as_view(job: Job) -> JobView:
    return JobView.model_validate({field: getattr(job, field) for field in JobView.model_fields})


def create_job(engine: Engine, request: JobCreate) -> JobView:
    with Session(engine) as session:
        # Serialize the idempotency read + write across processes as well as threads.
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        try:
            existing = session.scalar(select(Job).where(Job.idempotency_key == request.idempotency_key))
            if existing is not None:
                if any(getattr(existing, key) != getattr(request, key) for key in ("dataset_id", "mapping_id", "harness_id")):
                    raise VersionConflict("Idempotency key already belongs to different inputs")
                result = as_view(existing)
            else:
                dataset = session.get(Dataset, request.dataset_id)
                mapping = session.get(MappingRecord, request.mapping_id)
                harness = session.get(HarnessRecord, request.harness_id)
                if dataset is None or mapping is None or harness is None or mapping.dataset_id != dataset.id:
                    raise ValueError("Missing or incompatible dataset, mapping or harness")
                job = Job(id=str(uuid4()), **request.model_dump(), status="queued",
                          created_at=datetime.now(timezone.utc).isoformat(),
                          mapping_snapshot=copy.deepcopy(mapping.payload),
                          harness_snapshot=copy.deepcopy(harness.payload))
                session.add(job)
                session.flush()
                result = as_view(job)
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise


def get_job(engine: Engine, job_id: str) -> JobView | None:
    with Session(engine) as session:
        job = session.get(Job, job_id)
        return None if job is None else as_view(job)
