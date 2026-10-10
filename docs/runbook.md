# Local setup and phase checks

PowerShell, repository root. Python 3.13 is required. This machine's working
executable is below; the WindowsApps `python` alias fails.

```powershell
& 'C:/Users/VINAY/AppData/Local/Programs/Python/Python313/python.exe' -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
Set-Location backend
../.venv/Scripts/python.exe -m pytest -q
```

Read-only workbook inspection writes to ignored `storage/p00`. Without an
authority argument names stay unconfirmed. This confirmation applies only to
the supplied workbook.

```powershell
../.venv/Scripts/python.exe -m app.workbook_seed 'C:/Users/VINAY/Downloads/HisabhParakh_Organizer_Aligned_500_Transactions.xlsx' --names-authority 'User confirmation on 2026-10-10: organizer confirmed the 27 category names'
```

One synthetic live request to an already running local Ollama; no workbook
data or retries. Use a fresh output filename to preserve earlier evidence.

```powershell
../.venv/Scripts/python.exe -m app.runtime_smoke --output ../storage/p00/gemma-smoke-rerun.json
```

The embedding check currently exits 1 with missing-package/snapshot blockers.
It never downloads models. After installing/pinning compatible CPU embedding
dependencies, supply a local `google/embeddinggemma-2` HF snapshot directory
named by its 40-character commit revision.

```powershell
../.venv/Scripts/python.exe -m app.embedding_smoke --output ../storage/p00/embedding-smoke-rerun.json
# With a pinned snapshot and compatible dependencies:
# ../.venv/Scripts/python.exe -m app.embedding_smoke --snapshot 'PATH/TO/snapshots/40_CHARACTER_COMMIT'
```

## P01: run the API and local UI

The API reads root `.env` if present; defaults work without it. Optional:
copy `.env.example` to `.env` without overwriting your existing settings.
P00 CLIs still use explicit arguments and do not load `.env`.

From `backend/`, migrate the local SQLite database and start one API process:

```powershell
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

In a second terminal from the repository root:

```powershell
Set-Location frontend
npm.cmd ci
$env:NEXT_TELEMETRY_DISABLED='1'
npm.cmd run dev
```

Open <http://127.0.0.1:3000>. The UI reads the API server-side and renders live
readiness. Refresh checks reloads the page. No Ollama generation runs during
readiness checks. An unavailable backend produces a clear offline state.
`frontend/.env.example` documents the optional server-side API address.

The API exposes `/api/v1/health`, `/api/v1/readiness`, and read-only job lookup.
Job creation deliberately returns 409 until P02 mapping/P03 worker exist.
API readiness is independent of classification readiness: a migrated database
can be ready while definitions, embeddings and worker still need work.
Application startup does not automatically migrate an existing database.

## Validation

From `backend/`:

```powershell
../.venv/Scripts/python.exe -m pip check
../.venv/Scripts/python.exe -m ruff check app tests migrations
../.venv/Scripts/python.exe -m mypy
../.venv/Scripts/python.exe -m pytest -q
../.venv/Scripts/python.exe -m alembic check
../.venv/Scripts/python.exe -m app.export_schemas
```

From `frontend/`:

```powershell
npm.cmd run generate:api
npm.cmd run typecheck
$env:NEXT_TELEMETRY_DISABLED='1'
npm.cmd run build
```

After migration and frontend build, `python -m app.verify_stack` from
`backend/` starts its own API/UI on free loopback ports, checks online and
offline HTML, writes `docs/evidence/p01-http-smoke.json`, and stops only those
owned processes. This is an HTTP integration smoke, not browser visual QA.

Python integration tests use temporary databases and explicitly synthetic
fixtures. The Starlette test client emits an upstream httpx deprecation warning;
tests pass with the pinned dependencies. CI is configured but not run remotely.
