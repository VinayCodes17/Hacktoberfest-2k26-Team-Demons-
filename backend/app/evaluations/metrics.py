import hashlib

def calculate_metrics(predictions: list[dict], true_labels: dict[str, str]) -> dict[str, float]:
    """
    Computes standard classification metrics.
    Accuracy = Correct / All eligible labeled rows
    Coverage = Accepted / All eligible labeled rows
    """
    if not true_labels:
        return {"accuracy": 0.0, "coverage": 0.0}

    correct_count = 0
    accepted_count = 0

    for pred in predictions:
        txn_id = pred.get("transaction_id")
        if txn_id not in true_labels:
            continue
            
        true_label = true_labels[txn_id]
        
        status = pred.get("status")
        if status == "accepted":
            accepted_count += 1
            if pred.get("proposed_label") == true_label:
                correct_count += 1

    total = len(true_labels)
    
    return {
        "accuracy": correct_count / total,
        "coverage": accepted_count / total,
        # Other metrics like macro_f1 can be added here
    }
