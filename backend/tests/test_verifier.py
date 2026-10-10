from app.verification.verifier import verify_proposal

def test_verifier_accepts_valid_proposal(monkeypatch):
    monkeypatch.setattr("app.verification.verifier.load_ontology", lambda: [{"name": "Contra"}, {"name": "Payment"}])
    
    proposal = {
        "proposed_label": "Contra",
        "top_alternative": "Payment",
        "evidence_paths": ["ownership_relation"],
        "missing_evidence": []
    }
    transaction = {"ownership_relation": "same_organization"}
    
    decision = verify_proposal(proposal, transaction)
    
    assert decision["status"] == "accepted"
    assert decision["reason_codes"] == []
    assert decision["candidates"] == ["Contra", "Payment"]
    assert decision["checked_evidence_paths"] == ["ownership_relation"]

def test_verifier_flags_invalid_label(monkeypatch):
    monkeypatch.setattr("app.verification.verifier.load_ontology", lambda: [{"name": "Payment"}])
    
    proposal = {
        "proposed_label": "InvalidCategory",
        "evidence_paths": ["amount"]
    }
    
    decision = verify_proposal(proposal, {"amount": "100"})
    
    assert decision["status"] == "error"
    assert "INVALID_PROPOSED_LABEL" in decision["reason_codes"]
    assert decision["proposed_label"] is None

def test_verifier_flags_missing_evidence(monkeypatch):
    monkeypatch.setattr("app.verification.verifier.load_ontology", lambda: [{"name": "Contra"}])
    
    proposal = {
        "proposed_label": "Contra",
        "evidence_paths": ["fake_path"]
    }
    
    decision = verify_proposal(proposal, {"amount": "100"})
    
    assert decision["status"] == "review"
    assert "INVALID_EVIDENCE_PATH" in decision["reason_codes"]
    assert "MISSING_DECISIVE_EVIDENCE" in decision["reason_codes"]

def test_verifier_handles_malformed_json():
    # If the LLM output is not even a dict
    decision = verify_proposal("just some text", {})
    assert decision["status"] == "error"
    assert "INVALID_JSON_PROPOSAL" in decision["reason_codes"]
