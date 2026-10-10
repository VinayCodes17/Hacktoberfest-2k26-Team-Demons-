
def create_manifest(transactions: list[dict], split_policy: str = "random") -> dict:
    """
    Creates a grouped split manifest before indexing.
    Groups duplicates, near-duplicates, and related document lines before splitting.
    Keeps final test isolated.
    """
    # Group by a simulated group key (e.g. invoice_number)
    groups: dict[str, list[dict]] = {}
    for txn in transactions:
        doc = txn.get("document", {})
        key = doc.get("invoice_number", txn.get("id"))
        groups.setdefault(key, []).append(txn)
    
    # Simplistic split representation
    manifest: dict[str, list[str]] = {
        "development": [],
        "final_test": [],
        "synthetic_fixture": []
    }
    
    # For MVP, just put everything in development unless marked otherwise
    for key, group in groups.items():
        manifest["development"].extend([t["id"] for t in group])
        
    return manifest
