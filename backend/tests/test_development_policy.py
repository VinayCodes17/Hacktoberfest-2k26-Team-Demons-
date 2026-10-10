from pathlib import Path

from app.contracts import load_taxonomy, require_classification_taxonomy
from app.routing.ontology import OntologyProvider
from app.schemas import CanonicalTransaction, ModelProposal, SourceRow
from app.verification.verifier import Verifier
from app.worker.prompt import ONTOLOGY_PATH, build_prompt


def test_development_policy_retains_workbook_boundaries():
    taxonomy = load_taxonomy(ONTOLOGY_PATH)
    require_classification_taxonomy(taxonomy)
    assert taxonomy.approval_scope == "development"
    assert len(taxonomy.entries) == 27
    assert len(taxonomy.confusion_boundaries) == 21
    assert "Review Required" not in {entry.name for entry in taxonomy.entries}
    prompt = build_prompt({"amount": 0, "paid": False, "currency": None}, {})
    assert '"amount": 0' in prompt and '"paid": false' in prompt
    assert '"currency": null' in prompt
    assert taxonomy.entries[0].definition in prompt
    assert taxonomy.confusion_boundaries[0].evidence_for_a in prompt


def test_unresolved_import_purchase_goes_to_review():
    verifier = Verifier(OntologyProvider(Path(ONTOLOGY_PATH)))
    transaction = CanonicalTransaction(id="test", sources=[SourceRow(
        dataset_id="fixture", sheet="input", physical_row=2,
        source_sha256="a" * 64, cells=[],
    )])
    proposal = ModelProposal(proposed_label="Purchase", top_alternative="Import",
                             evidence_paths=[], missing_evidence=[], rationale_summary="Ambiguous")
    status, reasons = verifier.verify(proposal, transaction)
    assert status == "review"
    assert "UNRESOLVED_CONFUSION_BOUNDARY" in reasons
