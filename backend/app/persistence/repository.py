"""Short transactions only. This module never calls an inference service."""

import copy
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.persistence.models import (
    Dataset,
    HarnessRecord,
    Job,
    JobRow,
    MappingRecord,
    ModelAttempt,
    Prediction,
    SourceRecord,
)
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
                if any(
                    getattr(existing, key) != getattr(request, key)
                    for key in ("dataset_id", "mapping_id", "harness_id")
                ):
                    raise VersionConflict("Idempotency key already belongs to different inputs")
                result = as_view(existing)
            else:
                dataset = session.get(Dataset, request.dataset_id)
                mapping = session.get(MappingRecord, request.mapping_id)
                harness = session.get(HarnessRecord, request.harness_id)
                if dataset is None or mapping is None or harness is None or mapping.dataset_id != dataset.id:
                    raise ValueError("Missing or incompatible dataset, mapping or harness")
                job = Job(
                    id=str(uuid4()),
                    **request.model_dump(),
                    status="queued",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    mapping_snapshot=copy.deepcopy(mapping.payload),
                    harness_snapshot=copy.deepcopy(harness.payload),
                )
                session.add(job)
                session.flush()

                # Create a JobRow for each SourceRecord in the dataset
                from app.persistence.models import JobRow, SourceRecord

                source_records = session.scalars(
                    select(SourceRecord).where(SourceRecord.dataset_id == dataset.id)
                ).all()
                for sr in source_records:
                    session.add(JobRow(job_id=job.id, transaction_id=sr.id, status="queued"))

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


def claim_job_row_lease(
    engine: Engine, worker_id: str, lease_duration_seconds: int = 300
) -> tuple[JobRow, SourceRecord, Job, int] | None:
    from datetime import timedelta

    from sqlalchemy import and_, or_, select

    from app.persistence.models import JobRow, SourceRecord

    with Session(engine) as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        try:
            now = datetime.now(timezone.utc).isoformat()

            # Find an available row
            stmt = (
                select(JobRow)
                .where(
                    or_(
                        JobRow.status == "queued",
                        and_(JobRow.status == "running", JobRow.lease_expires_at < now),
                    )
                )
                .limit(1)
            )

            row = session.scalar(stmt)
            if not row:
                return None

            # Get job and source record
            job = session.get(Job, row.job_id)
            source = session.get(SourceRecord, row.transaction_id)

            if not job or not source:
                # Broken relationship, should not happen, fail row
                row.status = "failed"
                session.commit()
                return claim_job_row_lease(engine, worker_id, lease_duration_seconds)

            # Track attempt
            stmt_attempt = select(ModelAttempt).where(
                ModelAttempt.job_id == row.job_id, ModelAttempt.transaction_id == row.transaction_id
            )
            attempts = session.scalars(stmt_attempt).all()
            attempt_number = len(attempts) + 1

            if attempt_number > 2:
                # Max retries exceeded
                row.status = "failed"
                session.commit()
                return claim_job_row_lease(engine, worker_id, lease_duration_seconds)

            row.status = "running"
            row.lease_owner = worker_id
            row.lease_expires_at = (
                datetime.now(timezone.utc) + timedelta(seconds=lease_duration_seconds)
            ).isoformat()

            attempt = ModelAttempt(
                job_id=row.job_id, transaction_id=row.transaction_id, number=attempt_number, reserved_at=now
            )
            session.add(attempt)

            session.commit()
            # session.refresh(row) and others before returning if needed, but we don't need them attached.
            session.expunge_all()
            return row, source, job, attempt_number
        except Exception:
            session.rollback()
            raise


def record_prediction(
    engine: Engine,
    job_id: str,
    transaction_id: str,
    attempt_number: int,
    payload: dict | None = None,
    error: str | None = None,
):
    from app.persistence.models import JobRow

    with Session(engine) as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        try:
            row = session.get(JobRow, (job_id, transaction_id))
            if not row:
                return

            attempt = session.get(ModelAttempt, (job_id, transaction_id, attempt_number))
            if attempt:
                attempt.outcome = "success" if error is None else f"error: {error}"

            if error is None and payload is not None:
                row.status = "completed"
                pred = Prediction(
                    id=str(uuid4()), job_id=job_id, transaction_id=transaction_id, payload=payload
                )
                session.add(pred)
            else:
                row.status = "queued"  # Will be marked failed by the lease claiming logic on retry exceed

            row.lease_owner = None
            row.lease_expires_at = None
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_job_progress(engine: Engine, job_id: str) -> dict:
    from sqlalchemy import func

    from app.persistence.models import JobRow

    with Session(engine) as session:
        counts = session.execute(
            select(JobRow.status, func.count()).where(JobRow.job_id == job_id).group_by(JobRow.status)
        ).all()
        result = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
        for status, count in counts:
            result[status] = count
        result["total"] = sum(result.values())
        return result


def get_job_predictions(engine: Engine, job_id: str) -> list[dict]:

    with Session(engine) as session:
        preds = session.scalars(select(Prediction).where(Prediction.job_id == job_id)).all()
        return [{"transaction_id": p.transaction_id, "payload": p.payload} for p in preds]


def get_prediction_trace(engine: Engine, prediction_id: str) -> dict | None:

    with Session(engine) as session:
        pred = session.get(Prediction, prediction_id)
        if not pred:
            return None
        return {
            "id": pred.id,
            "job_id": pred.job_id,
            "transaction_id": pred.transaction_id,
            "decision": pred.payload,
        }
