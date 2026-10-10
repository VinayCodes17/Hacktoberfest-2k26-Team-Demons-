# Evaluation foundation

`backend/app/schemas.py::EvaluationRun` defines a pinned harness ID, manifest
hash, split, variants, status and actual metric fields. Its schema is exported
in `docs/contracts/domain.schema.json`; the initial DB has an evaluations table.

No evaluation runner or benchmark has executed. `synthetic_fixture` is distinct
from development and final-test splits. The supplied 500-row workbook is
unverified synthetic input and must not be promoted to gold or retrieval memory.
Later manifests must group related rows/duplicates before splitting and retain
label authority/provenance. No report should imply that this skeleton measures
classification quality.
