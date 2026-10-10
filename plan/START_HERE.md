# HisabhParakh — small-context entry point

Do not read the entire `implementation.md` on every task. It is the detailed design archive. Use this sequence:

1. Read [plan/STATUS.md](plan/STATUS.md) to find the next unfinished work and actual blockers.
2. Read [plan/CORE.md](plan/CORE.md) for shared constraints.
3. Read only the current file in [plan/phases](plan/phases), plus its required scoped references.
4. Inspect applicable repository instructions and relevant actual code; implement and verify the phase.
5. Update status with evidence, changed paths, decisions and the exact next step. Keep the handoff short.

Start with [P00](plan/phases/P00.md). P00–P10 are delivery phases; P11 is optional. If a phase is partially blocked, finish independent tasks and record the precise remaining dependency.

Suggested prompt:

> Read START_HERE.md. Implement the next ready unfinished phase using STATUS.md, CORE.md and that phase's required references. Do not load the full master plan unless needed to resolve a specific ambiguity. Verify the work, prepare its PR/draft, update status, and give a Hinglish summary.

## Keeping the plan consistent

The split files initially reproduce the master plan's sections. For subsequent planning edits, update the affected split file and corresponding master section together. Record material decisions in STATUS.md; resolve discrepancies explicitly instead of silently choosing a version. The user's latest instruction takes precedence.

Copy this file, the `plan/` directory and `implementation.md` into the actual project when handing it to a coding agent. These files currently live in the planning workspace; they are not application code.
