from app.schemas import ErrorCluster
from typing import Any


class FailureMiner:
    def mine_errors(self, development_decisions: list[dict], true_labels: dict[str, str]) -> list[ErrorCluster]:
        """
        Mines only trusted labeled development errors, grouped by confusion pair and missing/contradictory signal.
        Excludes infrastructure failures (like errors without a valid prediction attempt).
        """
        clusters: dict[tuple[str, str], dict[str, Any]] = {}
        
        for decision in development_decisions:
            txn_id = decision.get("transaction_id")
            if txn_id not in true_labels:
                continue
            
            true_label = true_labels[txn_id]
            pred_label = decision.get("proposed_label")
            status = decision.get("status")
            
            # Exclude infrastructure failures or accepted correct
            if status == "error" or (status == "accepted" and pred_label == true_label):
                continue
                
            # If review or accepted but wrong, it's a semantic error
            if pred_label is None:
                pair = (true_label, "UNKNOWN")
            else:
                pair = (true_label, pred_label)
                
            if pair not in clusters:
                clusters[pair] = {
                    "case_ids": [],
                    "missing_signals": [],
                    "contradictory_signals": []
                }
            
            clusters[pair]["case_ids"].append(txn_id)
            # Extracted from decision trace if available (mocked for now)
            
        result = []
        for pair, data in clusters.items():
            result.append(ErrorCluster(
                id=f"cluster-{pair[0]}-{pair[1]}",
                confusion_pair=pair,
                missing_signals=data["missing_signals"],
                contradictory_signals=data["contradictory_signals"],
                case_ids=data["case_ids"],
                support_count=len(data["case_ids"])
            ))
            
        return result
