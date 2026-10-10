from pathlib import Path

from app.routing.ontology import OntologyProvider
from app.schemas import CanonicalTransaction, FinancialSignal, ModelProposal, SourceRow
from app.verification.verifier import Verifier
from app.worker.prompt import ONTOLOGY_PATH


def check(label="Receipt", rival="Advance / Prepayment", missing=None, issues=None):
    transaction = CanonicalTransaction(
        id="test",
        sources=[SourceRow(dataset_id="d", sheet="s", physical_row=2, source_sha256="a" * 64, cells=[])],
        signals=[
            FinancialSignal(
                name="narration",
                value="Collection against existing sales invoice",
                status="observed",
                source_paths=["A2"],
            )
        ],
        parse_issues=issues or [],
    )
    proposal = ModelProposal(
        proposed_label=label,
        top_alternative=rival,
        evidence_paths=["narration"],
        missing_evidence=missing or [],
        rationale_summary="Existing invoice settlement",
    )
    return Verifier(OntologyProvider(Path(ONTOLOGY_PATH))).verify(proposal, transaction)


def test_resolved_alternative_and_none_sentinel_do_not_force_review():
    assert check(missing=["None"])[0] == "accepted"


def test_supplementary_narration_does_not_force_review():
    assert check(issues=["MULTIPLE_SOURCE_VALUES:narration:A2,B2"])[0] == "accepted"


def test_actual_missing_evidence_and_amount_conflicts_remain_review():
    assert check(missing=["Is this before or after the invoice?"])[0] == "review"
    assert check(issues=["MULTIPLE_SOURCE_VALUES:invoice_total:A2,B2"])[0] == "review"


def test_unapproved_import_precedence_remains_review():
    assert check(label="Import", rival="Purchase", missing=["None"])[0] == "review"
