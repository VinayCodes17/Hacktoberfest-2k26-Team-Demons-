"""Fail-closed P00 contracts; workbook text never confers approval."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TaxonomyEntry(Contract):
    name: str = Field(min_length=1)
    official_id: str | None = None
    family: str
    definition: str
    source_url: str
    source_row: int = Field(ge=2)
    boundary: str
    provenance: str


class Taxonomy(Contract):
    revision: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_sheet: str = "Voucher Ontology"
    names_confirmed: bool = False
    names_authority: str | None = None
    definitions_approved: bool = False
    definitions_authority: str | None = None
    entries: list[TaxonomyEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_names_and_authority(self):
        names = [entry.name.strip().casefold() for entry in self.entries]
        if any(not name for name in names) or len(names) != len(set(names)):
            raise ValueError("Taxonomy names must be nonblank and unique")
        if self.names_confirmed and not self.names_authority:
            raise ValueError("Confirmed names require authority")
        if self.definitions_approved and not self.definitions_authority:
            raise ValueError("Approved definitions require authority")
        return self


def load_taxonomy(path: Path) -> Taxonomy:
    if not path.is_file():
        raise ValueError("TAXONOMY_MISSING")
    return Taxonomy.model_validate_json(path.read_text(encoding="utf-8"))


def require_classification_taxonomy(taxonomy: Taxonomy | None) -> None:
    if taxonomy is None:
        raise ValueError("TAXONOMY_MISSING")
    if not taxonomy.names_confirmed:
        raise ValueError("TAXONOMY_NAMES_UNCONFIRMED")
    if not taxonomy.definitions_approved:
        raise ValueError("TAXONOMY_DEFINITIONS_UNAPPROVED")


class WorkbookContract(Contract):
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    sheet: str
    header_row: int = Field(ge=1)
    first_data_row: int = Field(ge=2)
    last_data_row: int = Field(ge=2)
    row_unit: Literal["physical_row"] = "physical_row"
    identity: Literal["sha256:sheet:physical_row"] = "sha256:sheet:physical_row"
    columns: list[str]
    data_role: Literal["synthetic_unverified"] = "synthetic_unverified"
    official_row_policy_confirmed: bool = False
    excluded_parallel_views: list[str]


class SubmissionContract(Contract):
    status: Literal["pending"] = "pending"
    envelope: None = None
    abstention_policy: None = None
    row_identity_policy: None = None
    reason: str = "Exact organizer submission schema has not been supplied"


class SmokeResponse(Contract):
    record_id: Literal["SYNTHETIC-SMOKE-001"]
    amount: Literal["0.00"]
    missing_currency: Literal[True]
