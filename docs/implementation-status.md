# Implementation status — 10 October 2026

P01 and P02 foundation is **implemented and locally verified**. P00 remains partial
because embedding/full-stack runtime evidence is still missing. Next: P03 (Worker Leases).

## P01 evidence

- FastAPI health/readiness and blocked job creation; strict shared domain and
  evaluation schemas; structured logs that omit input data and exception text.
- Nine SQLite tables with explicit Alembic migration, WAL/FKs/bounded writes,
  idempotent job persistence and pinned mapping/harness snapshots.
- Next.js/Tailwind local UI renders real readiness/offline state; TypeScript
  contracts generated from OpenAPI. No invented predictions or accuracy.
- Locked dependencies, `.env` validation, synthetic test doubles only in tests,
  CI definition and [runbook](runbook.md).

| P01 check | Actual result |
|---|---|
| `python -m pytest -q` | 26 passed; one upstream Starlette/httpx deprecation warning |
| `python -m ruff check app tests migrations` | Passed |
| `python -m mypy` | Passed for 10 scoped source files |
| `python -m pip check` | No broken dependencies |
| `python -m alembic upgrade head` / `python -m alembic check` | Passed; no schema drift; repeated migration also tested |
| Separate-process DB read + concurrent idempotency | Passed in test suite |
| `npm.cmd run generate:api` / `npm.cmd run typecheck` | Passed |
| `npm.cmd run build` | Production build passed |
| `python -m app.verify_stack` | Live API + production UI HTTP checks passed, including API-offline rendering; owned processes stopped |

HTTP report: [p01-http-smoke.json](evidence/p01-http-smoke.json).
CI is configured, not remotely run. Browser visual/interaction QA was unavailable;
verification used production HTML/HTTP. No new generation or accuracy benchmark.

Decisions: [0002](decisions/0002-p01-foundation.md).
Review: [P01 draft](pr-drafts/P01.md), **not published**. No commit/merge.
Worker leases/reservation/recovery logic belongs to P03; its storage fields and
constraints exist, but HTTP jobs remain blocked until the real worker is ready.

## P02 evidence

- Implemented safe workbook ingestion with zip bomb / macro protection.
- Created robust schema detection supporting both synthetic (111 cols) and organizer (169 cols) test case schemas.
- Implemented column mapping with exclusion of the `Voucher Category` column to prevent label leakage.
- Handled sparse rows distinguishing False, 0, and Missing values properly.
- All unit tests for reading, profiling, and mapping pass.

| P02 check | Actual result |
|---|---|
| `python -m pytest backend/tests/test_ingestion.py backend/tests/test_normalization.py -q` | 59 passed |


## Earlier P00 evidence (historical)

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

Next ready work: **P02 workbook upload, explicit mapping and normalization**.
Inspect the supplied field dictionaries and preserve full cell provenance.
Integrate confusion boundaries in their classification/verification phases;
synthetic examples remain behavior fixtures, not trusted labels. Keep P00
partial until embedding/runtime checks pass.

Local review: `pr-drafts/P00.md` (**not published**). No commit or remote PR.
Existing planning files preserved apart from status handoff.
