"""Shared domain records. Money is Decimal internally, strings over JSON."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, JsonValue, model_validator

from app.contracts import Contract

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]


class SourceCell(Contract):
    coordinate: str
    cell_type: Literal["s", "n", "b", "d", "f", "e", "inlineStr", "null"]
    value: JsonValue


class SourceRow(Contract):
    dataset_id: Identifier
    sheet: str
    physical_row: int = Field(ge=1)
    source_sha256: Digest
    cells: list[SourceCell]


class SchemaMapping(Contract):
    id: Identifier
    dataset_id: Identifier
    revision: int = Field(ge=1)
    sheet: str
    header_row: int = Field(ge=1)
    first_data_row: int = Field(ge=2)
    last_data_row: int = Field(ge=2)
    row_unit: Literal["physical_row"]
    canonical_to_column: dict[str, str]
    approver: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_scope(self):
        if not self.header_row < self.first_data_row <= self.last_data_row:
            raise ValueError("Invalid mapping row scope")
        if not self.canonical_to_column or any(not k or not v for k, v in self.canonical_to_column.items()):
            raise ValueError("Mapping requires explicit fields and source columns")
        return self


class FinancialSignal(Contract):
    name: str
    value: JsonValue
    status: Literal["observed", "derived", "unknown"]
    source_paths: list[str]
    derivation_version: str | None = None

    @model_validator(mode="after")
    def require_provenance(self):
        if self.status != "unknown" and not self.source_paths:
            raise ValueError("Known signals require source evidence")
        if self.status == "derived" and not self.derivation_version:
            raise ValueError("Derived signals require a rule version")
        return self


class OntologyEntry(Contract):
    name: str
    official_id: str | None = None
    family: str
    definition: str
    source_url: str | None = None
    source_row: int | None = None
    boundary: str
    provenance: str


class CanonicalTransaction(Contract):
    id: Identifier
    sources: list[SourceRow] = Field(min_length=1)
    document: dict[str, JsonValue] = Field(default_factory=dict)
    parties: dict[str, JsonValue] = Field(default_factory=dict)
    accounts: dict[str, JsonValue] = Field(default_factory=dict)
    amounts: dict[str, Decimal | None] = Field(default_factory=dict)
    currency: str | None = None
    inventory: dict[str, JsonValue] = Field(default_factory=dict)
    tax: dict[str, JsonValue] = Field(default_factory=dict)
    references: dict[str, JsonValue] = Field(default_factory=dict)
    missing_paths: list[str] = Field(default_factory=list)
    parse_issues: list[str] = Field(default_factory=list)
    signals: list[FinancialSignal] = Field(default_factory=list)


class ModelProposal(Contract):
    proposed_label: str | None
    top_alternative: str | None
    evidence_paths: list[str]
    missing_evidence: list[str]
    rationale_summary: str = Field(max_length=1000)


class HarnessBundle(Contract):
    id: Identifier
    model_digest: Digest
    runtime_version: str
    generation_settings: dict[str, JsonValue]
    code_commit: str
    ontology_sha256: Digest
    prompt_sha256: Digest
    encoder_config: dict[str, JsonValue]
    memory_snapshot_id: str | None
    quality_policy: dict[str, JsonValue]
    evaluator_manifest_sha256: Digest | None


class Decision(Contract):
    id: Identifier
    job_id: Identifier
    transaction_id: Identifier
    proposed_label: str | None
    status: Literal["accepted", "review", "error"]
    reason_codes: list[str]
    candidates: list[str]
    checked_evidence_paths: list[str]
    attempts: int = Field(ge=0, le=2)
    trace_id: Identifier
    harness_id: Identifier
    confidence_score: None = None


class Review(Contract):
    prediction_id: Identifier
    expected_revision: int = Field(ge=1)
    reviewer_id: Identifier
    corrected_label: str
    reason: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    source: str = Field(min_length=1)
    created_at: datetime


class EvaluationRun(Contract):
    id: Identifier
    manifest_sha256: Digest
    harness_id: Identifier
    split: Literal["development", "final_test", "synthetic_fixture"]
    variants: list[str] = Field(min_length=1)
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    metrics: dict[str, float | None] = Field(default_factory=dict)


class ErrorCluster(Contract):
    id: Identifier
    confusion_pair: tuple[str, str]
    missing_signals: list[str] = Field(default_factory=list)
    contradictory_signals: list[str] = Field(default_factory=list)
    case_ids: list[Identifier]
    support_count: int


class PolicyPatch(Contract):
    patch_type: Literal["boundary_definition", "fixed_prompt_section", "retrieval_setting"]
    target_path: str
    diff_content: str


class RepairCandidate(Contract):
    id: Identifier
    parent_version: str
    hypothesis: str
    supporting_case_ids: list[Identifier]
    patches: list[PolicyPatch] = Field(max_length=1)  # One delta per candidate
    expected_benefit: str
    risk: str
    paper_reference: str


class GateConfig(Contract):
    min_macro_f1_gain: float
    max_critical_class_recall_drop: float
    max_p95_latency_ms: int
    minimum_label_support: int


class RegressionReport(Contract):
    candidate_id: Identifier
    parent_id: Identifier
    passed: bool
    reasons: list[str]
    parent_metrics: dict[str, float]
    candidate_metrics: dict[str, float]


class ActivationEvent(Contract):
    id: Identifier
    harness_id: Identifier
    parent_id: Identifier | None
    action: Literal["activate", "rollback"]
    authorizer: str
    timestamp: datetime


class JobCreate(Contract):
    dataset_id: Identifier
    mapping_id: Identifier
    harness_id: Identifier
    idempotency_key: Identifier


class JobView(Contract):
    id: Identifier
    dataset_id: Identifier
    mapping_id: Identifier
    harness_id: Identifier
    status: Literal["queued", "running", "completed", "failed"]


class Check(Contract):
    name: str
    status: Literal["ready", "blocked", "unavailable", "optional"]
    message: str


class Readiness(Contract):
    service_ready: bool
    classification_ready: bool
    checks: list[Check]


class Health(Contract):
    status: Literal["ok"] = "ok"
    service: Literal["HisabhParakh"] = "HisabhParakh"


class ErrorResponse(Contract):
    code: str
    message: str
