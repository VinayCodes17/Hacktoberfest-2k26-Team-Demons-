import json
from pathlib import Path

ONTOLOGY_PATH = Path(__file__).parent.parent.parent / "ontology" / "workbook-seed.json"


def load_ontology() -> list[dict]:
    if not ONTOLOGY_PATH.exists():
        raise FileNotFoundError(f"Ontology file not found at {ONTOLOGY_PATH}")
    with open(ONTOLOGY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # The ontology contains list of categories in 'entries'
    return data.get("entries", [])


def build_prompt(transaction: dict, mapping_snapshot: dict) -> str:
    ontology = load_ontology()
    categories = [
        cat.get("Voucher Category") or cat.get("name")
        for cat in ontology
        if (cat.get("Voucher Category") or cat.get("name"))
    ]

    # Clean up empty dicts and lists from the raw transaction dictionary
    cleaned_txn = {}
    for k, v in transaction.items():
        if isinstance(v, (dict, list)) and not v:
            continue
        if v is None or v == "":
            continue
        cleaned_txn[k] = v

    prompt = f"""You are a strict, highly accurate Indian financial accounting assistant. Your task is to classify the following financial transaction into exactly one of the permitted Voucher Categories.

PERMITTED CATEGORIES:
{json.dumps(categories, indent=2)}

TRANSACTION DATA:
{json.dumps(cleaned_txn, indent=2, default=str)}

MAPPING SNAPSHOT:
{json.dumps(mapping_snapshot, indent=2)}

INSTRUCTIONS:
1. Analyze the transaction data and mapping snapshot.
2. Determine the most appropriate Voucher Category from the PERMITTED CATEGORIES list.
3. If no category fits, you may return null for the proposed_label.
4. Identify a top alternative if applicable.
5. Provide a rationale summary (max 1000 chars) explaining the choice based on accounting principles.
6. Provide evidence paths (keys from the transaction data that led to the conclusion).
7. List any missing evidence that would have made the classification more confident.
"""
    return prompt
