## 7. Evaluation definitions and anti-leakage rules

| Measurement | Definition / reporting rule |
|---|---|
| Accuracy | Correct labels / all eligible labeled rows; null/error counts as incorrect |
| Macro/weighted F1 | Explicit official-label list and support counts; abstention counted as missed true class; show absent classes and zero-division policy |
| Candidate recall | Rows whose true label is in candidate set / eligible labeled rows; report set size and K |
| Retrieval MRR/Recall@K | Use declared relevance judgments; label agreement is a separate proxy, not automatically semantic relevance |
| Accepted coverage | Accepted rows / all eligible rows |
| Selective risk | Incorrect accepted rows / accepted rows; if none accepted, undefined, not zero |
| Review/error rates | Counts and denominators alongside all-row quality |
| Robustness consistency | Unchanged decisions for meaning-preserving transforms; report sample count and incorrect-but-consistent cases |
| Latency | Cold/warm per-row and end-to-end P50/P95, queue versus compute; real attempt/token counts |
| Resource use | Peak process/system RAM and VRAM for full stack; include offload/runtime config |

Use three main partitions: reference/training, development validation, final test. Within development, reserve a calibration subset if calibration is attempted; use a disjoint labeled assessment for calibrated claims. For error-driven repair, preferably separate development error-mining and promotion-validation groups; if too small, disclose reuse and development overfitting risk. A fixed final test remains untouched in all cases.

Near-duplicate detection rules and group IDs must be recorded before splitting. A second upload of the same record must not evade split exclusions through a new dataset ID. Synthetic stress fixtures never mix into reported organizer-data accuracy. Limit proposal iterations and retain a tuning history. A final test inspected repeatedly ceases to be untouched; label it accordingly and do not continue making unbiased test claims.

Do not show Brier score/ECE for cosine similarity, arbitrary quality scores or unsupported class probabilities. If there is no valid probability estimator and sufficient held-out labels, leave probability calibration out.
