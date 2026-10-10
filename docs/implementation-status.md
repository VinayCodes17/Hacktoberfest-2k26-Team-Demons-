# Implementation status — 10 October 2026

P00 is **partially implemented and verified**. P01 has not started.

Implemented: strict contracts/JSON schemas, read-only workbook importer,
confirmed category names with separate definition approval, 500-row profile,
Gemma live smoke, optional offline embedding probe, isolated Python environment
and frozen installed dependencies.

| Command (backend directory, repository .venv Python) | Result | Evidence |
|---|---|---|
| `python -m app.workbook_seed <supplied-workbook> --names-authority <recorded-confirmation>` | Exit 0; 27 categories, 500 rows, 111 columns, 500 unique IDs, zero input formulas | `evidence/workbook-profile.json`, `contracts/workbook.json`, `../backend/ontology/workbook-seed.json` |
| `python -m app.runtime_smoke` | Exit 0; one live synthetic request, schema-valid JSON, 22.629 s including load | `evidence/gemma-smoke.json` |
| `python -m app.embedding_smoke` | Exit 1; blocked, no live inference | `evidence/embedding-smoke.json` |
| `python -m pytest -q` | Exit 0; 7 passed | `../backend/tests/` |
| `git diff --check` (repository root) | Exit 0 | Local check |
| `python -m pip check` | Exit 0; no broken requirements | Isolated project environment |

Final artifact validation also passed: extracted contracts deserialize, 27
confirmed names retain the unapproved-definition gate, workbook/README hashes
are unchanged, new files have no trailing whitespace, and private storage plus
the virtual environment are ignored by Git.

Exact invocations are in `runbook.md`. Initial import failed on an ontology
footer; blank-separator handling fixes it with a synthetic regression test.
Tests use synthetic fixtures; no classification benchmark was run.

Remaining P00: install/pin/test CPU EmbeddingGemma 2, verify absent modality
encoders, shared resource fit and remaining compatibility/license evidence.
Definitions/precedence, submission, trusted-label/split and deadline inputs
remain separate gates; category names are confirmed by the user.

Next ready work: **P01 typed API and durable storage**, using P00 contracts.
Its independent work needs neither live embeddings nor approved definitions.
Follow `plan/phases/P01.md`. Keep P00 partial until runtime checks pass.

Local review: `pr-drafts/P00.md` (**not published**). No commit or remote PR.
Existing planning files preserved apart from status handoff.
