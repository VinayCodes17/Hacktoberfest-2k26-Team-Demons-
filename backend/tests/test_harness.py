import pytest
from app.schemas import GateConfig, HarnessBundle
from app.repair.regression import RegressionGate
from app.repair.activation import HarnessManager

def test_regression_gate_passes():
    gate = RegressionGate()
    config = GateConfig(
        min_macro_f1_gain=0.01,
        max_critical_class_recall_drop=0.05,
        max_p95_latency_ms=1000,
        minimum_label_support=50
    )
    
    parent_metrics = {"macro_f1": 0.80, "critical_class_recall": 0.90, "support_count": 100}
    candidate_metrics = {"macro_f1": 0.85, "critical_class_recall": 0.88, "p95_latency_ms": 500}
    
    report = gate.evaluate_candidate("c1", "p1", config, parent_metrics, candidate_metrics)
    assert report.passed is True
    assert len(report.reasons) == 0

def test_regression_gate_fails_on_gain():
    gate = RegressionGate()
    config = GateConfig(
        min_macro_f1_gain=0.05,
        max_critical_class_recall_drop=0.05,
        max_p95_latency_ms=1000,
        minimum_label_support=50
    )
    
    parent_metrics = {"macro_f1": 0.80, "support_count": 100}
    candidate_metrics = {"macro_f1": 0.82}
    
    report = gate.evaluate_candidate("c1", "p1", config, parent_metrics, candidate_metrics)
    assert report.passed is False
    assert "macro_f1 gain 0.02" in report.reasons[0]

def test_harness_activation_and_rollback():
    manager = HarnessManager()
    
    b1 = HarnessBundle(
        id="v1",
        model_digest="a"*64,
        runtime_version="1.0",
        generation_settings={},
        code_commit="sha",
        ontology_sha256="b"*64,
        prompt_sha256="c"*64,
        encoder_config={},
        memory_snapshot_id=None,
        quality_policy={},
        evaluator_manifest_sha256=None
    )
    
    b2 = HarnessBundle(
        id="v2",
        model_digest="a"*64,
        runtime_version="1.0",
        generation_settings={},
        code_commit="sha2",
        ontology_sha256="b"*64,
        prompt_sha256="c"*64,
        encoder_config={},
        memory_snapshot_id=None,
        quality_policy={},
        evaluator_manifest_sha256=None
    )
    
    manager.register_bundle(b1)
    manager.register_bundle(b2)
    
    ev1 = manager.activate_bundle("v1", "admin")
    assert manager.active_bundle_id == "v1"
    assert ev1.action == "activate"
    
    ev2 = manager.activate_bundle("v2", "admin")
    assert manager.active_bundle_id == "v2"
    
    ev3 = manager.rollback("v1", "admin")
    assert manager.active_bundle_id == "v1"
    assert ev3.action == "rollback"
