# Implementation handoff

## Current position

- Implementation started on 10 October 2026 in the actual project repository.
- [P00](phases/P00.md): partial; contracts/workbook profile/Gemma smoke verified.
- [P01](phases/P01.md): implemented and locally verified (API, storage, UI).
- Next ready phase: [P02](phases/P02.md), workbook upload/mapping/normalization.
- Evidence: [implementation status](../docs/implementation-status.md),
  [decisions](../docs/decisions/0001-p00-contracts.md),
  [P01 local PR draft](../docs/pr-drafts/P01.md) (not published).

## Unresolved inputs

- G1: user confirmed all 27 organizer category names; extracted with provenance.
  Definitions and overlap precedence remain unapproved.
- G2: supplied workbook profiled: 500 unique transactions; select
  `Organizer_Ready_Input` (111 columns), physical rows 2–501. Other views are
  not additional transactions. Official grouped-row policy remains pending.
- G3: exact submission JSON and abstention policy.
- G4: workbook is synthetic/unverified; zero trusted labels imported.
  Reviewer authority and permitted splits remain pending.
- G5: live E4B JSON smoke passed on Ollama 0.35.1; digest pinned. Embedding
  dependencies/pinned snapshot absent. Full-stack fit unmeasured; RAM nearly full.
- G6: deadline and judging rubric.

Continue independent scaffolding/contract work when a specific input is missing. Do not bypass gates.

## Phase state

| Phase | State | Evidence / PR |
|---|---|---|
| P00 | Partial; embedding/runtime work remains | `docs/evidence/`, `docs/pr-drafts/P00.md` |
| P01 | Implemented, locally verified | `docs/evidence/p01-http-smoke.json`, `docs/pr-drafts/P01.md` |
| P02 | Pending | None |
| P03 | Pending | None |
| P04 | Pending | None |
| P05 | Pending | None |
| P06 | Pending | None |
| P07 | Pending | None |
| P08 | Pending | None |
| P09 | Pending | None |
| P10 | Pending | None |
| P11 | Optional, pending | None |

## Latest handoff

Changed in P01: backend API/config/domain records, SQLite migration/repository,
redacted logs, schema export and tests; frontend readiness UI/generated types;
lockfiles, CI, runbook, decisions, local PR draft and README status notice.
Source workbook unchanged. No commit or remote publication.

Checks: 26 tests passed (one upstream httpx deprecation warning); Ruff/mypy/pip
checks passed; migration/drift/restart/concurrent-idempotency checks passed;
TypeScript and production Next.js build passed; live API/UI HTTP online and
offline rendering passed. No browser visual QA available. No new model inference
or classification benchmark. P00 embedding blockers remain.

Use `.venv/Scripts/python.exe`; WindowsApps Python alias fails. Working base:
`C:/Users/VINAY/AppData/Local/Programs/Python/Python313/python.exe`.
Exact commands: `docs/runbook.md`. Next: P02 scoped references, inspect both
field dictionaries for mapping/normalization, and build upload/mapping UI.
Confusion Boundaries and Synthetic Examples are still not integrated; connect
them in their owning phases without promoting synthetic examples to gold.
Resolve P00 embedding runtime before claiming P00 complete.
