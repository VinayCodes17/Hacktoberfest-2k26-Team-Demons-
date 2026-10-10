import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts import load_taxonomy
from app.persistence.database import make_engine, migrate
from app.persistence.models import (
    Dataset,
    HarnessRecord,
    MappingRecord,
    ModelAttempt,
    Prediction,
    SourceRecord,
)
from app.persistence.repository import claim_job_row_lease, create_job, get_job, record_prediction
from app.schemas import CanonicalTransaction, FinancialSignal, JobCreate, SourceCell, SourceRow
from app.settings import Settings
from app.worker.worker import process_job_row


@pytest.fixture
def queued(tmp_path):
    settings = Settings(_env_file=None, database_path=tmp_path / "worker.db")
    engine = make_engine(settings.database_path)
    migrate(engine)
    transaction = CanonicalTransaction(
        id="row",
        sources=[
            SourceRow(
                dataset_id="ds",
                sheet="Actual",
                physical_row=7,
                source_sha256="a" * 64,
                cells=[SourceCell(coordinate="A7", cell_type="s", value="External supplier paid")],
            )
        ],
        signals=[
            FinancialSignal(
                name="description", value="External supplier paid", status="observed", source_paths=["A7"]
            )
        ],
    )
    with Session(engine) as session:
        session.add(Dataset(id="ds", source_sha256="a" * 64, storage_key="fixture", created_at="now"))
        session.flush()
        session.add(MappingRecord(id="m", dataset_id="ds", revision=1, payload={"sheet": "Actual"}))
        session.add(
            HarnessRecord(
                id="h",
                payload={
                    "taxonomy": load_taxonomy(settings.taxonomy_path).model_dump(),
                    "model_digest": settings.gemma_model_digest,
                },
            )
        )
        session.add(
            SourceRecord(
                id="row",
                dataset_id="ds",
                sheet="Actual",
                physical_row=7,
                payload=transaction.model_dump(mode="json"),
            )
        )
        session.commit()
    job = create_job(
        engine, JobCreate(dataset_id="ds", mapping_id="m", harness_id="h", idempotency_key="one")
    )
    yield engine, settings, job
    engine.dispose()


def test_worker_reads_real_source_and_saves_result(queued, monkeypatch):
    engine, settings, job = queued

    def generate(prompt, config):
        assert "External supplier paid" in prompt
        return dict(
            proposed_label="Payment",
            top_alternative=None,
            evidence_paths=["description"],
            missing_evidence=[],
            rationale_summary="Settlement",
        )

    monkeypatch.setattr("app.worker.worker.generate_classification", generate)
    assert process_job_row(engine, settings, "worker")
    assert get_job(engine, job.id).status == "completed"
    with Session(engine) as session:
        pred = session.scalar(select(Prediction))
        assert pred.payload["proposed_label"] == "Payment"
        assert pred.payload["evidence_paths"] == ["description"]
        assert len(session.scalars(select(ModelAttempt)).all()) == 1
    assert not process_job_row(engine, settings, "worker")


def test_failure_consumes_two_persisted_attempts_and_finishes(queued, monkeypatch):
    engine, settings, job = queued
    calls = []

    def fail(*args):
        calls.append(1)
        raise TimeoutError()

    monkeypatch.setattr("app.worker.worker.generate_classification", fail)
    process_job_row(engine, settings, "before-restart")
    process_job_row(engine, settings, "after-restart")
    assert not process_job_row(engine, settings, "after-restart")
    assert len(calls) == 2
    assert get_job(engine, job.id).status == "failed"
    with Session(engine) as session:
        assert len(session.scalars(select(ModelAttempt)).all()) == 2
        assert session.scalar(select(Prediction)).payload["status"] == "error"


def test_expired_lease_rejects_stale_result(queued):
    engine, settings, job = queued
    lease = claim_job_row_lease(engine, "old", lease_duration_seconds=-1)
    assert lease[1].sheet == "Actual"  # Detached ORM object remains readable.
    new = claim_job_row_lease(engine, "new")
    assert new[3] == 2
    record_prediction(engine, job.id, "row", 1, payload={"status": "accepted"}, worker_id="old")
    with Session(engine) as session:
        assert session.scalar(select(Prediction)) is None
    record_prediction(engine, job.id, "row", 2, error="TIMEOUT", worker_id="new")
    assert get_job(engine, job.id).status == "failed"


def test_crash_after_second_reservation_has_terminal_error(queued):
    engine, settings, job = queued
    claim_job_row_lease(engine, "first", lease_duration_seconds=-1)
    claim_job_row_lease(engine, "second", lease_duration_seconds=-1)
    assert claim_job_row_lease(engine, "third") is None
    with Session(engine) as session:
        assert session.scalar(select(Prediction)).payload["reason_codes"] == ["ATTEMPT_BUDGET_EXHAUSTED"]
    assert get_job(engine, job.id).status == "failed"
