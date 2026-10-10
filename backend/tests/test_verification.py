import pytest

from app.routing.ontology import OntologyProvider
from app.schemas import CanonicalTransaction, Decision, ModelProposal, SourceRow
from app.verification.review_service import ReviewService
from app.verification.verifier import Verifier


def test_verifier_missing_label(tmp_path):
    ontology_path = tmp_path / "ontology.json"
    ontology_path.write_text('{"entries": []}')
    provider = OntologyProvider(ontology_path)
    verifier = Verifier(provider)

    proposal = ModelProposal(
        proposed_label=None,
        top_alternative=None,
        evidence_paths=[],
        missing_evidence=[],
        rationale_summary="test"
    )
    transaction = CanonicalTransaction(id="t1", sources=[SourceRow(dataset_id="mock", sheet="mock", physical_row=1, source_sha256="a" * 64, cells=[])])
    
    status, reasons = verifier.verify(proposal, transaction)
    assert status == "review"
    assert "MISSING_LABEL" in reasons

def test_verifier_invalid_label(tmp_path):
    ontology_path = tmp_path / "ontology.json"
    ontology_path.write_text('{"entries": [{"name": "Payment", "family": "Banking", "definition": "test", "boundary": "bound", "provenance": "prov"}]}')
    provider = OntologyProvider(ontology_path)
    verifier = Verifier(provider)

    proposal = ModelProposal(
        proposed_label="Unknown",
        top_alternative=None,
        evidence_paths=[],
        missing_evidence=[],
        rationale_summary="test"
    )
    transaction = CanonicalTransaction(id="t1", sources=[SourceRow(dataset_id="mock", sheet="mock", physical_row=1, source_sha256="a" * 64, cells=[])])
    
    status, reasons = verifier.verify(proposal, transaction)
    assert status == "error"
    assert "INVALID_LABEL" in reasons

def test_review_service(tmp_path):
    ontology_path = tmp_path / "ontology.json"
    ontology_path.write_text('{"entries": [{"name": "Payment", "family": "Banking", "definition": "test", "boundary": "bound", "provenance": "prov"}]}')
    provider = OntologyProvider(ontology_path)
    service = ReviewService(provider)

    decision = Decision(
        id="d1",
        job_id="j1",
        transaction_id="t1",
        proposed_label="Unknown",
        status="error",
        reason_codes=[],
        candidates=[],
        checked_evidence_paths=[],
        attempts=1,
        trace_id="tr1",
        harness_id="h1"
    )
    
    review = service.submit_review(
        reviewer_id="user1", 
        decision=decision, 
        corrected_label="Payment", 
        reason="Manual fix", 
        authority="trusted", 
        source="dashboard"
    )
    
    assert review is not None
    assert review.reviewer_id == "user1"
    assert review.corrected_label == "Payment"
    
    with pytest.raises(ValueError):
        service.submit_review(
            reviewer_id="user1", 
            decision=decision, 
            corrected_label="Unknown", 
            reason="Manual fix", 
            authority="trusted", 
            source="dashboard"
        )
