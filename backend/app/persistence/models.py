from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)


class SourceRecord(Base):
    __tablename__ = "source_rows"
    __table_args__ = (
        UniqueConstraint("dataset_id", "sheet", "physical_row"),
        CheckConstraint("physical_row >= 1"),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    sheet: Mapped[str] = mapped_column(String)
    physical_row: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class MappingRecord(Base):
    __tablename__ = "mappings"
    __table_args__ = (UniqueConstraint("id", "dataset_id"), UniqueConstraint("dataset_id", "revision"),
                      CheckConstraint("revision >= 1"))
    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    revision: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class HarnessRecord(Base):
    __tablename__ = "harness_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        ForeignKeyConstraint(["mapping_id", "dataset_id"], ["mappings.id", "mappings.dataset_id"]),
        CheckConstraint("status IN ('queued','running','completed','failed')"),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    mapping_id: Mapped[str] = mapped_column(String)
    harness_id: Mapped[str] = mapped_column(ForeignKey("harness_versions.id"))
    idempotency_key: Mapped[str] = mapped_column(String, unique=True)
    mapping_snapshot: Mapped[dict] = mapped_column(JSON)
    harness_snapshot: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="queued")
    created_at: Mapped[str] = mapped_column(String)


class JobRow(Base):
    __tablename__ = "job_rows"
    __table_args__ = (CheckConstraint("status IN ('queued','running','completed','failed')"),)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("source_rows.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String, default="queued")
    lease_owner: Mapped[str | None] = mapped_column(String)
    lease_expires_at: Mapped[str | None] = mapped_column(String)


class ModelAttempt(Base):
    __tablename__ = "model_attempts"
    __table_args__ = (
        ForeignKeyConstraint(["job_id", "transaction_id"], ["job_rows.job_id", "job_rows.transaction_id"]),
        CheckConstraint("number >= 1 AND number <= 2"),
    )
    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, primary_key=True)
    reserved_at: Mapped[str] = mapped_column(String)
    outcome: Mapped[str | None] = mapped_column(String)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("job_id", "transaction_id"),
        ForeignKeyConstraint(["job_id", "transaction_id"], ["job_rows.job_id", "job_rows.transaction_id"]),
    )
    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String)
    transaction_id: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)


class EvaluationRecord(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    harness_id: Mapped[str] = mapped_column(ForeignKey("harness_versions.id"))
    payload: Mapped[dict] = mapped_column(JSON)
