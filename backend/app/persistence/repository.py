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

    with Session(engine, expire_on_commit=False) as session:
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
                session.add(
                    Prediction(
                        id=str(uuid4()),
                        job_id=row.job_id,
                        transaction_id=row.transaction_id,
                        payload={
                            "status": "error",
                            "proposed_label": None,
                            "reason_codes": ["ATTEMPT_BUDGET_EXHAUSTED"],
                            "attempts": 2,
                        },
                    )
                )
                _finish_job(session, row.job_id)
                session.commit()
                return None

            row.status = "running"
            job.status = "running"
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


def _finish_job(session, job_id):
    session.flush()
    rows = session.scalars(select(JobRow).where(JobRow.job_id == job_id)).all()
    job = session.get(Job, job_id)
    if rows and all(r.status in {"completed", "failed"} for r in rows):
        job.status = "failed" if any(r.status == "failed" for r in rows) else "completed"


def record_prediction(
    engine: Engine,
    job_id: str,
    transaction_id: str,
    attempt_number: int,
    payload: dict | None = None,
    error: str | None = None,
    worker_id: str | None = None,
):
    with Session(engine) as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        row = session.get(JobRow, (job_id, transaction_id))
        attempt = session.get(ModelAttempt, (job_id, transaction_id, attempt_number))
        if (
            row is None
            or attempt is None
            or attempt.outcome is not None
            or row.status != "running"
            or (worker_id is not None and row.lease_owner != worker_id)
        ):
            return
        latest = session.scalars(
            select(ModelAttempt).where(
                ModelAttempt.job_id == job_id, ModelAttempt.transaction_id == transaction_id
            )
        ).all()
        if attempt_number != max(a.number for a in latest):
            return  # A reclaimed lease owns any newer result.
        attempt.outcome = "success" if error is None else error
        if error is not None and attempt_number < 2:
            row.status = "queued"
        else:
            row.status = "completed" if error is None else "failed"
            final = (
                payload
                if error is None
                else {
                    "status": "error",
                    "proposed_label": None,
                    "reason_codes": [error],
                    "attempts": attempt_number,
                }
            )
            session.add(
                Prediction(id=str(uuid4()), job_id=job_id, transaction_id=transaction_id, payload=final)
            )
        row.lease_owner = None
        row.lease_expires_at = None
        _finish_job(session, job_id)
        session.commit()


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
        active = session.execute(
            select(SourceRecord.physical_row, SourceRecord.sheet)
            .join(JobRow, JobRow.transaction_id == SourceRecord.id)
            .where(JobRow.job_id == job_id, JobRow.status == "running")
            .limit(1)
        ).first()
        result["active_row"] = None if active is None else {"physical_row": active[0], "sheet": active[1]}
        return result


def get_job_predictions(engine: Engine, job_id: str) -> list[dict]:

    with Session(engine) as session:
        preds = session.scalars(select(Prediction).where(Prediction.job_id == job_id)).all()
        return [{"id": p.id, "transaction_id": p.transaction_id, "payload": p.payload} for p in preds]


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


def cancel_job(engine: Engine, job_id: str) -> dict:
    """Cancel a running job by marking remaining queued/running rows as failed."""
    with Session(engine) as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        job = session.get(Job, job_id)
        if job is None:
            raise LookupError("JOB_NOT_FOUND")
        if job.status not in ("queued", "running"):
            return {"status": job.status, "cancelled": 0}
        rows = session.scalars(
            select(JobRow).where(
                JobRow.job_id == job_id,
                JobRow.status.in_(["queued", "running"]),
            )
        ).all()
        for row in rows:
            row.status = "failed"
            row.lease_owner = None
            row.lease_expires_at = None
            # Save a cancelled prediction so the UI shows something
            session.add(
                Prediction(
                    id=str(uuid4()),
                    job_id=job_id,
                    transaction_id=row.transaction_id,
                    payload={
                        "status": "error",
                        "proposed_label": None,
                        "reason_codes": ["CANCELLED_BY_USER"],
                        "attempts": 0,
                    },
                )
            )
        job.status = "failed"
        session.commit()
        return {"status": "cancelled", "cancelled": len(rows)}
