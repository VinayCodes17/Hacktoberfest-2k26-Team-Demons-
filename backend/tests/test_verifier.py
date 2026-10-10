from pathlib import Path

from app.routing.ontology import OntologyProvider
from app.schemas import CanonicalTransaction, FinancialSignal, ModelProposal, SourceRow
from app.verification.verifier import Verifier


def test_verifier_accepts_valid_proposal(monkeypatch):
    monkeypatch.setattr("app.routing.ontology.OntologyProvider.get_by_name", lambda self, name: {"name": name})
    
    verifier = Verifier(OntologyProvider(Path("dummy.json")))
    proposal = ModelProposal(
        proposed_label="Contra",
        top_alternative="Payment",
        evidence_paths=["ownership_relation"],
        missing_evidence=[],
        rationale_summary="some reason"
    )
    transaction = CanonicalTransaction(
        id="123",
        sources=[SourceRow(
            dataset_id="mock", sheet="mock", physical_row=1,
            source_sha256="a" * 64, cells=[]
        )],
        signals=[FinancialSignal(name="ownership_relation", value="same", status="observed", source_paths=["col1"])],
        missing_paths=[]
    )
    
    status, reasons = verifier.verify(proposal, transaction)
    assert status == "accepted"
    assert reasons == []

def test_verifier_flags_invalid_label(monkeypatch):
    monkeypatch.setattr("app.routing.ontology.OntologyProvider.get_by_name", lambda self, name: None)
    
    verifier = Verifier(OntologyProvider(Path("dummy.json")))
    proposal = ModelProposal(
        proposed_label="InvalidCategory",
        top_alternative="Payment",
        evidence_paths=["amount"],
        missing_evidence=[],
        rationale_summary="some reason"
    )
    transaction = CanonicalTransaction(
        id="1",
        sources=[SourceRow(
            dataset_id="mock", sheet="mock", physical_row=1,
            source_sha256="a" * 64, cells=[]
        )]
    )
    
    status, reasons = verifier.verify(proposal, transaction)
    assert status == "error"
    assert "INVALID_LABEL" in reasons

def test_verifier_flags_missing_evidence(monkeypatch):
    monkeypatch.setattr("app.routing.ontology.OntologyProvider.get_by_name", lambda self, name: {"name": name})
    
    verifier = Verifier(OntologyProvider(Path("dummy.json")))
    proposal = ModelProposal(
        proposed_label="Contra",
        top_alternative="Payment",
        evidence_paths=["fake_path"],
        missing_evidence=[],
        rationale_summary="some reason"
    )
    transaction = CanonicalTransaction(
        id="1",
        sources=[SourceRow(
            dataset_id="mock", sheet="mock", physical_row=1,
            source_sha256="a" * 64, cells=[]
        )]
    )
    
    status, reasons = verifier.verify(proposal, transaction)
    assert status == "error"
    assert "UNSUPPORTED_EVIDENCE" in reasons
