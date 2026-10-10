import sys, json, os
import pandas as pd
sys.path.append("backend")
from app.worker.prompt import build_prompt
from app.worker.llm import generate_classification
from app.settings import Settings
from app.schemas import CanonicalTransaction, ModelProposal
from app.verification.verifier import Verifier
from app.routing.ontology import OntologyProvider
from app.contracts import load_taxonomy

settings = Settings()
taxonomy = load_taxonomy(settings.taxonomy_path)
verifier = Verifier(OntologyProvider(taxonomy))

df = pd.read_excel("excel files/Voucher_Classification_Test_Cases_v2.xlsx")
# Drop empty rows
df = df.dropna(how="all")
if "Voucher Category" not in df.columns:
    print("No Voucher Category column!")
    sys.exit(1)

results = []
correct = 0
needs_review = 0
errors = 0
total = 0
confusion = {}
for idx, row in df.iterrows():
    ground_truth = row["Voucher Category"]
    if pd.isna(ground_truth):
        continue
    total += 1
    # Build transaction dict
    tx_dict = {}
    for col in df.columns:
        if col != "Voucher Category" and pd.notna(row[col]):
            tx_dict[col] = str(row[col])
    
    prompt = build_prompt(tx_dict, {}, taxonomy)
    try:
        pred_dict = generate_classification(prompt, settings)
        proposal = ModelProposal.model_validate(pred_dict)
        # Mock CanonicalTransaction for verifier
        signals = []
        for k, v in tx_dict.items():
            from app.schemas import FinancialSignal
            signals.append(FinancialSignal(name=k, value=v, status="observed", source_paths=[]))
        tx = CanonicalTransaction(id=str(idx), sources=[], signals=signals)
        status, reasons = verifier.verify(proposal, tx)
        
        pred_label = proposal.proposed_label
        if status == "accepted":
            if pred_label == ground_truth:
                correct += 1
            else:
                confusion[(ground_truth, pred_label)] = confusion.get((ground_truth, pred_label), 0) + 1
        elif status == "review":
            needs_review += 1
            pred_label = "Needs Review"
        else:
            errors += 1
            pred_label = "Error"
            
        print(f"Row {idx}: GT={ground_truth} | Pred={pred_label} | Status={status}")
        results.append((idx, ground_truth, pred_label, status, reasons))
    except Exception as e:
        print(f"Error on row {idx}: {e}")
        errors += 1
        
print(f"\\nTotal: {total}")
print(f"Correct: {correct}")
print(f"Needs Review: {needs_review}")
print(f"Errors: {errors}")
print(f"Accuracy (accepted match): {correct/total:.2%}")
print("Confusion Matrix (GT, Pred) for accepted but wrong:")
for k, v in sorted(confusion.items(), key=lambda x: -x[1]):
    print(f"  {k[0]} -> {k[1]}: {v}")
