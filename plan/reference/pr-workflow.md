## 9. Phase PR workflow and Hinglish reporting

The request is a phase-wise implementation plan; this planning task does not create application PRs. During building, use a branch such as `phase/03-gemma-jobs` and one phase-focused PR against the real repository. If a remote is unavailable, save the exact PR draft locally and say `not published`. Publishing/merging follows the user's repository authorization; never report a merge that did not occur.

Each PR must contain the following, proportional to its change:

```markdown
## Problem and behavior
What user-visible capability now works? State the concrete before/after.

## Scope
Phase ID, implemented modules and dependency decisions.

## Validation
Exact commands run, exit status, meaningful results and artifact paths.
Separate mocked tests, live inference and labeled benchmark results.

## Research connection
Paper/concept ID, code path, experiment ID, actual result or not measured.

## Hinglish summary
Is phase mein humne ... implement kiya. Isse user ... kar sakta hai.
Humne ... checks run kiye. Abhi ... pending/blocked hai.

## Remaining limitations
Unresolved inputs and next phase; no fabricated completion claims.
```

Suggested status ledger columns: phase, state, branch/real PR or draft path, commit, checks run, evidence artifact, external blocker and next step. Do not automatically tick all checklist boxes. Preserve failed experiments as useful evidence.
