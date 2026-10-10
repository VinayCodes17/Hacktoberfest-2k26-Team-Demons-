# Deployment Guide

This repository contains a full Docker Compose configuration to run HisabhParakh in an isolated, production-like environment.

## Architecture
- **Web**: Next.js frontend, port 3000
- **API**: FastAPI backend running one worker slot (to prevent resource contention), port 8000
- **Qdrant**: Vector database for trusted context retrieval, port 6333
- **Volumes**: Persistent local storage for SQLite (`app_data`), Qdrant indices (`qdrant_data`), and model caches (`model_cache`).

## Prerequisites
- Docker & Docker Compose
- Minimum 16GB RAM for CPU embedding and Qdrant overhead
- Valid local/remote connection for Ollama (configured via environment).

## Execution
From the root directory:

```bash
docker-compose up --build -d
```

### Limitations
1. **SQLite**: It is deliberately mounted to a local path (`/data/app.db`) inside Docker. Do not bind-mount to an NFS or SMB network share as SQLite will throw lock errors.
2. **Worker Scaling**: We strictly configure `workers=1` to enforce bounds on concurrent GPU/CPU pressure. Scaling horizontally requires an external message queue not provided in this MVP.
3. **Offline**: The system functions entirely offline *after* Docker images and HuggingFace caches are pulled. 

## Reproducibility
Review the `docs/reproducibility-manifest.json` for exact pinning of commit hashes, hardware baselines, and model constraints used during testing.
