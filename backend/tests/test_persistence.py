import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.persistence.database import make_engine, migrate, schema_ready
from app.persistence.models import (
    Dataset,
    HarnessRecord,
    Job,
    MappingRecord,
    ModelAttempt,
    Prediction,
    SourceRecord,
)
from app.persistence.repository import VersionConflict, create_job, get_job
from app.schemas import JobCreate


@pytest.fixture
def database(tmp_path):
    engine = make_engine(tmp_path / "test.db")
    migrate(engine)
    with engine.begin() as connection:
        connection.execute(insert(Dataset).values(id="dataset", source_sha256="0" * 64, storage_key="synthetic", created_at=datetime.now(timezone.utc).isoformat()))
        connection.execute(insert(MappingRecord).values(id="mapping", dataset_id="dataset", revision=1, payload={"fixture": "mapping-v1"}))
        connection.execute(insert(HarnessRecord).values(id="harness", payload={"fixture": "bundle-v1"}))
        connection.execute(insert(SourceRecord).values(id="row", dataset_id="dataset", sheet="Synthetic", physical_row=2, payload={"synthetic": True}))
    yield engine
    engine.dispose()


def request(key="request"):
    return JobCreate(dataset_id="dataset", mapping_id="mapping", harness_id="harness", idempotency_key=key)


def test_empty_migration_is_repeatable_and_enables_constraints(database):
    migrate(database)
    assert schema_ready(database)
    with database.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
        assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 5000
    with pytest.raises(IntegrityError), database.begin() as connection:
        connection.execute(insert(MappingRecord).values(id="orphan", dataset_id="missing", revision=1, payload={}))


def test_job_survives_new_process_and_keeps_snapshots(database):
    job = create_job(database, request())
    with Session(database) as session:
        mapping = session.get(MappingRecord, "mapping")
        mapping.payload = {"fixture": "changed"}
        session.commit()
        assert session.get(Job, job.id).mapping_snapshot == {"fixture": "mapping-v1"}
    code = "import sys, os; sys.path.insert(0, os.getcwd()); from pathlib import Path; from app.persistence.database import make_engine; from app.persistence.repository import get_job; e=make_engine(Path(sys.argv[1])); print(get_job(e,sys.argv[2]).model_dump_json()); e.dispose()"
    result = subprocess.run([sys.executable, "-c", code, database.url.database, job.id], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == job.model_dump()
    assert get_job(database, "missing") is None


def test_idempotency_and_input_conflict(database):
    first = create_job(database, request())
    assert create_job(database, request()).id == first.id
    conflicting = request().model_copy(update={"mapping_id": "other"})
    with pytest.raises(VersionConflict):
        create_job(database, conflicting)
    with pytest.raises(ValueError):
        create_job(database, request("other").model_copy(update={"dataset_id": "missing"}))
    with Session(database) as session:
        assert len(session.scalars(select(Job)).all()) == 1


def test_concurrent_idempotency_produces_one_job(database):
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = list(pool.map(lambda _: create_job(database, request()), range(2)))
    assert jobs[0].id == jobs[1].id


def test_result_uniqueness_and_attempt_limit(database):
    job = create_job(database, request())
    with database.begin() as connection:
        connection.execute(insert(Prediction).values(id="p1", job_id=job.id, transaction_id="row", payload={}))
        for number in (1, 2):
            connection.execute(insert(ModelAttempt).values(job_id=job.id, transaction_id="row", number=number, reserved_at="synthetic"))
    with pytest.raises(IntegrityError), database.begin() as connection:
        connection.execute(insert(Prediction).values(id="p2", job_id=job.id, transaction_id="row", payload={}))
    with pytest.raises(IntegrityError), database.begin() as connection:
        connection.execute(insert(ModelAttempt).values(job_id=job.id, transaction_id="row", number=3, reserved_at="synthetic"))
