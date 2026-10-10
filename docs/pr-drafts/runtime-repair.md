# Fix embedding startup and connect durable classification jobs

The embedding container crashed because the torchvision wheel did not match CPU
Torch. Install and check the matching CPU wheel. Readiness now reflects the
running encoder and worker polling state.

Replace dummy transactions and the gemma2 default with immutable uploaded source
rows, approved taxonomy snapshots and pinned E4B inference. Persist attempts before
each request, reject stale leases, and save terminal failures. Replace simulated
frontend completion with mapping confirmation, real jobs and persisted results.

Validation: 114 backend tests, targeted Ruff, TypeScript/production build, two
Chrome desktop/mobile checks, live normalized query/document embeddings and one
synthetic workbook row classified by E4B. Export/Sales overlap remained review.
Evidence: ../evidence/runtime-repair.json. No accuracy benchmark or submission
approval is implied. Trusted reference memory remains empty.
