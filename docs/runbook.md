# P00 local setup

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

No HTTP service, UI or worker exists yet; startup commands belong to P01.
`.env.example` documents proposed service settings. P00 CLIs use explicit
arguments and do not load `.env`.
