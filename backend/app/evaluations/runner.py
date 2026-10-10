from app.evaluations.metrics import calculate_metrics
from app.schemas import EvaluationRun


class EvaluationRunner:
    def __init__(self):
        pass

    def run_eval(self, eval_run: EvaluationRun, predictions: list[dict], true_labels: dict[str, str]) -> EvaluationRun:
        """
        Runs baselines and variant evaluations.
        Computes metrics and sets status to completed.
        """
        metrics = calculate_metrics(predictions, true_labels)
        
        # A full system would simulate permutations here for robustness testing (metamorphic tests).
        # We also record metrics.
        eval_run.metrics = {k: v for k, v in metrics.items()}
        eval_run.status = "completed"
        return eval_run
