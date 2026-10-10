# P00 decisions — 10 October 2026

## Scope and sources

The initial implementation follows `plan/START_HERE.md`: P00 precedes P01.
Workbook prose, formulas and URLs are reference data, not instructions,
permissions or verified ground truth.

- README preserved. Current SHA-256:
  `5a585818ba122c7bbd7ccd3d69a61fea3aa1555a85d22d5c59038ce959736638`.
  This differs from the historical planning hash; use today's actual bytes.
- Workbook SHA-256:
  `6b22236bbc1508fa85052949592deb5b22818b53d35b9e0db448229e321538fa`.
- Original stays unchanged in Downloads. No transaction contents are committed.
  Extracted definitions retain workbook provenance and URLs; those accounting
  pages were not independently audited in this run.

## Input gates

| Gate | Evidence and decision | Remaining dependency |
|---|---|---|
| G1 | User confirmed on 2026-10-10 that the organizer confirmed the 27 category names. Names extracted exactly from ontology rows 2–28; no IDs invented. | Interpreted definitions and precedence remain unapproved. Production classification fails closed. |
| G2 | 500 unique, nonblank transaction IDs. Select `Organizer_Ready_Input`, 111 columns, rows 2–501. Identity is hash + sheet + physical row. | Official multi-line/export rules; current policy is for development. |
| G3 | Typed pending submission contract exists. | Exact envelope, label representation, identity and abstention rules. |
| G4 | Workbook explicitly marks transactions synthetic/unverified. Zero trusted labels imported. | Reviewer authority, permitted gold sources and grouped splits. |
| G5 | Gemma live JSON passed, digest pinned, GPU/RAM samples recorded. | Embedding dependencies and pinned snapshot absent; full-stack fit unmeasured. |
| G6 | No authoritative deadline/rubric supplied. | Deadline and judging rubric. |

`Transactions_Input` (115 columns), `Agent_Ready_View` (32 columns), and
`Agent_Context_Complete` are parallel views, not additional transactions. Use
the complete 111-column organizer view. Synthetic document stage/type shortcuts
and generated context are not needed for import. The blank separator ends the
ontology table; the footer is excluded. Missing XLSX dimensions are computed
before profiling. No source cells are rewritten or formulas evaluated.

## Runtime and stack

Retain planned FastAPI/Pydantic, SQLAlchemy/Alembic/SQLite, Next.js, Qdrant and
CPU EmbeddingGemma 2. P00 implements contracts/tooling; services belong to P01.
Python 3.13.0 exists but the normal launcher fails. A project `.venv` uses the
working installation. Tested P00 dependencies are frozen in
`backend/requirements.lock`; future dependencies are not yet validated.
The first pip attempt hit sandbox socket restrictions; approved retry succeeded.

Gemma: Ollama 0.35.1, `gemma4:e4b-it-q4_K_M`, full digest in the smoke report.
Artifact metadata reports Q4_K_M, 7.5B and a validation-named parent; preserve
those values without inventing a checkpoint identity. Local model license text
reports Apache 2.0 and its hash is recorded. Embedding license/revision remains
unverified locally; the complete runtime/package license audit is pending.

Test settings: one request, context 4096, output cap 128, temperature 0,
thinking disabled. These are smoke settings, not optimized classification limits.
Whole-host RAM approached 16.4 GB physical capacity. Sampled GPU use reached
5170 MiB of 8188 MiB. One short successful request does not prove full-stack
capacity, 500-row throughput or accuracy. Ollama `size_vram` differs from
nvidia-smi usage; both are retained without equating them.

## Documentation and research

- [Ollama generate API](https://docs.ollama.com/api/generate): checked for schema
  output, nonstreaming calls, thinking and timings.
- [Google embedding guide](https://ai.google.dev/gemma/docs/embeddinggemma/inference-embeddinggemma-with-sentence-transformers):
  checked for text-only configuration, CPU/float32 and 768d setup. Optional smoke
  tooling exists; its live embedding path remains untested.
- Research citations retain planning status. R2 publisher verification remains
  pending. This transport test validates no research or accuracy claims.

No model substitutions, category renaming, trusted-label promotion or remote
publication occurred.
