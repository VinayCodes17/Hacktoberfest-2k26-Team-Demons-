# P01 foundation — 10 October 2026

## Scope

P01 proceeds independently of P00's missing embedding runtime. It introduces
FastAPI, SQLite/SQLAlchemy/Alembic, a Next.js readiness UI, shared domain records,
evaluation-run schema, generated OpenAPI types and CI. Classification, upload,
mapping UI and evaluation execution are not claimed implemented.

The database migration creates datasets, source rows, mappings, harness versions,
jobs, row states, model attempts, predictions and evaluations. Review, trusted
labels, policy activation and export tables will be added by their owning phases
when those workflows exist. Alembic migrations are explicit and checked for drift.

Jobs pin mapping and harness snapshots at creation. A short `BEGIN IMMEDIATE`
transaction serializes idempotency checks and insertion. No inference occurs in
these transactions. SQLite enables WAL, foreign keys and a five-second busy
timeout on each connection. Unique and foreign-key constraints prevent orphan
records and duplicate row results. Attempt numbers are restricted to 1 and 2;
durable pre-request reservations and crash/lease recovery remain P03 work.

## Process and worker boundary

Run one Uvicorn process and, when implemented in P03, one external bounded
classification worker. No FastAPI background task or in-request inference is
used. The future worker claims row leases in short transactions, commits an
attempt reservation before sending, heartbeats/reclaims leases and never retries
silently. P01's job creation HTTP endpoint stays blocked until that worker and
confirmed mappings exist. Test doubles live only in `backend/tests/fakes.py`.

## Readiness and local UI

Health is liveness. Readiness checks the DB migration, taxonomy approval and live
Ollama model metadata/digest, without loading a model. API readiness depends on
the DB; classification readiness remains false until the actual worker/gates
exist. Embeddings are explicitly pending. Empty reference memory is optional.

The UI reads this endpoint server-side with a timeout and no caching. It displays
an offline state when the API cannot be reached. It has no placeholder scores,
predictions, upload controls or invented metrics. Local-only Sites guidance was
used; the existing Next.js stack was retained and nothing was published.
No browser-control tool was available; production HTML and live/offline API
integration were checked, but visual/browser interaction QA remains unperformed.

## Configuration and logs

Settings enforce the chosen models, one generation session, two total attempts,
CPU 768d embeddings and a 4096 context ceiling until a larger context is measured.
Numeric environment literals are explicitly parsed; `.env.example` is tested.
Paths resolve from the repository root. Default bindings are loopback-only.

Application logs allow only an event name, generated request ID, status and
duration. Request bodies, query strings, headers and exception text are excluded.
Validation errors return a fixed typed message rather than echoing financial
values. Run Uvicorn with `--no-access-log` as documented. Authentication and
reviewer authorization are not implemented; do not expose this local prototype.

## Compatibility and evidence

Pinned packages passed local tests on Python 3.13.0 / Node 24.12.0 / Windows.
Next.js 16.4.0 / React 19.3.0 production build passed. OpenAPI generator requires
TypeScript 5.x; the initial 7.x resolution was replaced with 5.9.3. Native Node
types match major 24. Lockfiles record full installed dependency versions.

The pinned Starlette test client warns that httpx will be superseded by httpx2;
this is a warning, not a failed test. Backend code still uses tested httpx.
CI mirrors lint, type, tests, schema drift and frontend build checks; remote
workflow execution has not been claimed.

Primary documentation consulted: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html),
[Next.js setup](https://nextjs.org/docs/app/getting-started/installation).

The other workbook reference sheets are still not integrated. P02 should inspect
field dictionaries for normalization; P03/P06 should connect confusion boundaries,
and synthetic examples should enter behavior tests without promotion to gold.
