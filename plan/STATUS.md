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
  Definitions and 21 confusion boundaries approved by the user for development on 2026-10-10. Unresolved overlaps require review; organizer submission remains unapproved.
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
| P00 | Implemented | `docs/evidence/`, `docs/pr-drafts/P00.md` |
| P01 | Implemented, locally verified | `docs/evidence/p01-http-smoke.json`, `docs/pr-drafts/P01.md` |
| P02 | Implemented | `docs/pr-drafts/P02.md` |
| P03 | Implemented | `docs/pr-drafts/P03.md` |
| P04 | Implemented | `docs/pr-drafts/P04.md` |
| P05 | Implemented | `docs/pr-drafts/P05.md` |
| P06 | Implemented | `docs/pr-drafts/P06.md` |
| P07 | Implemented | `docs/pr-drafts/P07.md` |
| P08 | Implemented | `docs/pr-drafts/P08.md` |
| P09 | Implemented | `docs/pr-drafts/P09.md` |
| P10 | Implemented | `docs/pr-drafts/P10.md` |
| P11 | Implemented | `docs/pr-drafts/P11.md` |

## Latest handoff

Changed in P01: backend API/config/domain records, SQLite migration/repository,
redacted logs, schema export and tests; frontend readiness UI/generated types;
lockfiles, CI, runbook, decisions, local PR draft and README status notice.
Source workbook unchanged. No commit or remote publication.

Checks: 26 tests passed (one upstream httpx deprecation warning); Ruff/mypy/pip
checks passed; migration/drift/restart/concurrent-idempotency checks passed;
TypeScript and production Next.js build passed; live API/UI HTTP online and
offline rendering passed. No browser visual QA available. No new model inference
or classification benchmark. P00 embedding blockers resolved.

Use `.venv/Scripts/python.exe`; WindowsApps Python alias fails. Working base:
`C:/Users/VINAY/AppData/Local/Programs/Python/Python313/python.exe`.
Exact commands: `docs/runbook.md`. Next: P02 scoped references, inspect both
field dictionaries for mapping/normalization, and build upload/mapping UI.
Confusion Boundaries and Synthetic Examples are still not integrated; connect
them in their owning phases without promoting synthetic examples to gold.
Resolve P00 embedding runtime before claiming P00 complete.

## P00 Summary
Is phase mein humne project ke actual contracts aur model setup verify kiye. Jo organizer inputs abhi missing hain unhe blockers mein rakha; koi label ya performance number assume nahi kiya.

## P05 Summary
Is phase mein relevant verified examples aur competing voucher definitions model tak pahunchayi. Retrieval ke filters ensure karte hain ki test data ya AI ke apne guesses evidence bank mein na ghusein. (Routing and retrieval interfaces implemented).

## P06 Summary
Is phase mein prediction ko uske strongest rival se check kiya aur missing evidence ko review reason banaya. Reviewer correction ka proper history hai; model ki agreement ko ground truth nahi maana.

## P07 Summary
Is phase mein humne actual labels par baseline aur added components compare kiye. Ab pata chalega kis feature se kitna benefit ya cost aaya; synthetic tests aur real accuracy alag report honge.

## P08 Summary
Is phase mein verified mistakes se chhote policy fixes propose kiye. AI sirf bounded suggestion deta hai; labels, benchmark aur production settings ko apni marzi se change nahi kar sakta.

## P09 Summary
Is phase mein proposed repair ko regression tests ke baad hi activate karna possible hua. Failed proposal reject hota hai; activated change mein issue aaye to poora previous version restore hota hai.

## P10 Summary
Is phase mein poora project target laptop par run karke package kiya. Demo, screenshots aur metrics actual execution se hain; setup steps aur limitations bhi documented hain.

## P11 Summary
Is optional phase mein measured bottleneck par improvement test kiya. Jo experiment useful nikla wahi retain kiya; extra technology sirf naam ke liye add nahi ki. (Caching full inference requests implemented).

## Development policy approval ? 2026-10-10

User approved workbook definitions and all 21 confusion boundaries for development.
Policy revision: `workbook-6b22236bbc15-dev-policy-1`. Unresolved overlaps go to
review. Synthetic examples remain unverified and are not trusted memory or gold.
See `docs/decisions/0002-development-policy-approval.md`. Targeted policy, contract
and verifier suite: 13 passed. This approval does not validate the worker,
end-to-end UI flow, or the phase-completion claims elsewhere in this file.

## Runtime repair ? 2026-10-10

Embeddings and classification worker now verified live in Docker. Fixed the
CPU torchvision wheel (0.29.1+cpu against torch 2.14.1+cpu), removed fake zero
vector fallback, replaced dummy source rows and gemma2 default, reserved every
attempt durably, rejected stale lease results and persisted terminal errors.
Workbook uploads now persist immutable inputs and mappings; UI confirms mapping,
starts actual jobs and polls saved results. Readiness uses worker heartbeat.

Evidence: `docs/evidence/runtime-repair.json`; 114 backend tests, targeted Ruff,
TypeScript/build and 2 Chrome desktop/mobile checks passed. One-row live Gemma
smoke produced Export/Sales ambiguity and correctly remained review. Both CPU
query/document vectors verified as normalized 768d. This is not a 500-row
accuracy benchmark and does not establish completion of every phase above.
Next: broader workbook-scope/mapping acceptance and real labeled evaluation;
manual review persistence/export and organizer submission remain separate work.

## User workflow repair ? 2026-10-10

Replaced the plain form with drag-and-drop upload, real upload progress, animated
step transitions, mapping confirmation, worker row progress, result filters and
Excel download. Browser calls now use a same-origin proxy instead of hardcoded
127.0.0.1:8000. Page refresh resumes the last saved job. Export keeps review/error
rows and source evidence; formula-like strings are inert. It is review output,
not organizer submission. Reduced-motion preference is respected.

Verified: 117 backend tests; TypeScript and Docker production build; 5 Chrome
checks passed (one duplicate mobile inference intentionally skipped). Actual
500-row workbook upload/mapping succeeded on desktop/mobile. A one-row live
Gemma job completed through the UI, survived refresh, and downloaded an XLSX
verified with OpenPyXL (1 review row and 111 source cells). No full 500-row
classification benchmark. Evidence: docs/evidence/workflow-ui.json.

## Sparse test workbook mapping fix ? 2026-10-10

The 54-row `01_Balanced_27_Classes.xlsx` upload was rejected because multiple
source headers mapped to one canonical field, not because voucher answers were
blank. Resolve populated aliases per row. When several alias values coexist,
retain source-qualified signals and source coordinates; differing values flag
review rather than discard/overwrite data. Duplicate headers still block with
an explicit explanation. Blank and populated answer columns remain excluded
from inference. Added regression tests for sparse aliases, simultaneous values,
blank labels and duplicate headers. 120 backend tests passed; Docker rebuilt.
