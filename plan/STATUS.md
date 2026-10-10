# Implementation handoff

## Current position

- Implementation started on 10 October 2026 in the actual project repository.
- [P00](phases/P00.md): partial; contracts/workbook profile/Gemma smoke verified.
- Next ready independent phase: [P01](phases/P01.md), typed API and storage.
- Evidence: [implementation status](../docs/implementation-status.md),
  [decisions](../docs/decisions/0001-p00-contracts.md),
  [local PR draft](../docs/pr-drafts/P00.md) (not published).

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
| P01 | Ready for independent foundation work | P00 contracts available |
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

Changed: `backend/` contracts/importer/smoke tools/tests/dependency freeze;
`docs/` schemas, evidence, decisions, runbook and draft; root ignore/environment
template. Source workbook and README unchanged. No commit or remote publication.

Checks: workbook CLI exit 0 (27 categories/500 rows/111 fields); seven tests
pass; Gemma live smoke exit 0 (22.629 s incl. load, one request); embedding probe
exit 1 with explicit missing-package/snapshot blockers. Ontology footer import
bug fixed and tested. No classification accuracy claimed.

Use `.venv/Scripts/python.exe`; WindowsApps Python alias fails. Working base:
`C:/Users/VINAY/AppData/Local/Programs/Python/Python313/python.exe`.
Exact commands: `docs/runbook.md`. Next: P01 scoped references and foundation;
resolve P00 embedding runtime before claiming that phase complete.
