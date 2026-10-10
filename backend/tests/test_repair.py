import pytest
from app.repair.miner import FailureMiner
from app.repair.proposer import PolicyProposer

def test_miner_semantic_errors():
    miner = FailureMiner()
    development_decisions = [
        {"transaction_id": "1", "proposed_label": "Receipt", "status": "accepted"}, # Error, should be Payment
        {"transaction_id": "2", "proposed_label": None, "status": "review"}, # Semantic error (miss)
        {"transaction_id": "3", "proposed_label": "Contra", "status": "error"} # Infra error, skip
    ]
    true_labels = {"1": "Payment", "2": "Payment", "3": "Contra"}
    
    clusters = miner.mine_errors(development_decisions, true_labels)
    assert len(clusters) == 2
    pairs = [c.confusion_pair for c in clusters]
    assert ("Payment", "Receipt") in pairs
    assert ("Payment", "UNKNOWN") in pairs

def test_proposer_banned_paths():
    proposer = PolicyProposer(locked_paths=["schemas.py", "evaluations/"])
    cluster = type("MockCluster", (), {"id": "1", "case_ids": ["t1"]})()
    
    patch_data = {
        "patch_type": "boundary_definition",
        "target_path": "backend/app/schemas.py",
        "diff_content": "+ label"
    }
    
    with pytest.raises(ValueError, match="Banned patch path"):
        proposer.propose_repair(cluster, "v1", patch_data)

def test_proposer_valid():
    proposer = PolicyProposer(locked_paths=["schemas.py"])
    cluster = type("MockCluster", (), {"id": "1", "case_ids": ["t1"]})()
    
    patch_data = {
        "patch_type": "boundary_definition",
        "target_path": "backend/ontology/workbook-seed.json",
        "diff_content": "updated definition"
    }
    
    candidate = proposer.propose_repair(cluster, "v1", patch_data)
    assert len(candidate.patches) == 1
    assert candidate.patches[0].target_path == "backend/ontology/workbook-seed.json"
