import pytest
from app.evaluations.metrics import calculate_metrics
from app.evaluations.manifest import create_manifest
from app.evaluations.runner import EvaluationRunner
from app.schemas import EvaluationRun

def test_calculate_metrics():
    predictions = [
        {"transaction_id": "1", "status": "accepted", "proposed_label": "Payment"},
        {"transaction_id": "2", "status": "accepted", "proposed_label": "Receipt"},
        {"transaction_id": "3", "status": "review", "proposed_label": "Contra"},
    ]
    true_labels = {
        "1": "Payment",
        "2": "Contra", # wrong
        "3": "Contra"  # review status
    }
    
    metrics = calculate_metrics(predictions, true_labels)
    assert metrics["accuracy"] == 1/3
    assert metrics["coverage"] == 2/3

def test_create_manifest():
    transactions = [
        {"id": "t1", "document": {"invoice_number": "inv1"}},
        {"id": "t2", "document": {"invoice_number": "inv1"}},
        {"id": "t3", "document": {"invoice_number": "inv2"}}
    ]
    manifest = create_manifest(transactions)
    assert len(manifest["development"]) == 3

def test_evaluation_runner():
    run = EvaluationRun(
        id="eval1",
        manifest_sha256="abcd" * 16,
        harness_id="harness1",
        split="development",
        variants=["A1", "A2"]
    )
    runner = EvaluationRunner()
    result = runner.run_eval(
        run, 
        predictions=[{"transaction_id": "1", "status": "accepted", "proposed_label": "Payment"}],
        true_labels={"1": "Payment"}
    )
    assert result.status == "completed"
    assert result.metrics["accuracy"] == 1.0
