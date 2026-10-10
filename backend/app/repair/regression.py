from app.schemas import GateConfig, RegressionReport

class RegressionGate:
    def evaluate_candidate(
        self, 
        candidate_id: str, 
        parent_id: str, 
        config: GateConfig, 
        parent_metrics: dict[str, float], 
        candidate_metrics: dict[str, float]
    ) -> RegressionReport:
        reasons = []
        passed = True
        
        # Missing required gate data fails closed
        if "macro_f1" not in parent_metrics or "macro_f1" not in candidate_metrics:
            reasons.append("Missing macro_f1 metric")
            passed = False
        else:
            f1_gain = round(candidate_metrics["macro_f1"] - parent_metrics["macro_f1"], 4)
            if f1_gain < config.min_macro_f1_gain:
                reasons.append(f"macro_f1 gain {f1_gain} < required {config.min_macro_f1_gain}")
                passed = False
                
        if "critical_class_recall" in parent_metrics and "critical_class_recall" in candidate_metrics:
            drop = parent_metrics["critical_class_recall"] - candidate_metrics["critical_class_recall"]
            if drop > config.max_critical_class_recall_drop:
                reasons.append(f"critical_class_recall drop {drop} > allowed {config.max_critical_class_recall_drop}")
                passed = False
                
        # Validate Latency
        if "p95_latency_ms" in candidate_metrics:
            if candidate_metrics["p95_latency_ms"] > config.max_p95_latency_ms:
                reasons.append("Latency exceeds P95 budget")
                passed = False

        if "support_count" in parent_metrics and parent_metrics["support_count"] < config.minimum_label_support:
            reasons.append("Insufficient label support")
            passed = False

        return RegressionReport(
            candidate_id=candidate_id,
            parent_id=parent_id,
            passed=passed,
            reasons=reasons,
            parent_metrics=parent_metrics,
            candidate_metrics=candidate_metrics
        )
