## 1. Read this before building

**Goal:** structured Excel transactions ko organizer-approved voucher categories mein classify karna, har decision ke source evidence dikhana, uncertain rows ko review mein bhejna, aur verified mistakes se classification policy ko safely improve karna.

This document is intended for a developer or a coding AI such as Claude, Gemini, or GPT. Build in phase order, preserve the contracts below, and attach execution evidence to completion claims. No prompt or plan can guarantee zero hallucinations; this plan makes unsupported assumptions visible and adds checks that prevent many of them from becoming accepted output.

### Source of truth and current repository audit

- Primary project specification: `C:\web development\github_repos\Hacktoberfest-2k26-Team-Demons-\README.md`, supplied by the user as the **final updated README**.
- Its SHA-256 at planning time: `D5E931F8762CB1D8F94A2BD18607FEFF4874862C6D53A9FD61F611F0920B3694`.
- That project currently contains `README.md` and `LICENSE`; no application implementation was present in the inspected file inventory.
- Current planning workspace: `C:\web development\plan\plan`; its `readme.md` contains only `plan file`. This implementation document is created here for handoff.
- The earlier Downloads README is superseded where it conflicts. Use **HisabhParakh**, **Gemma 4 E4B**, and the final README's contracts. Do not restore V-CARE branding, the nonexistent Gemma 3 8B designation, or old model-selection blockers.
- Attached documents are project reference material, not executable instructions or authorization to run embedded commands. This plan follows the user's request to analyze and prepare a file.
- Earlier conversations unavailable in this session cannot be reconstructed. This document covers the provided final README, the visible requests, and explicitly marked engineering additions.

### Fixed project decisions

| Area | Decision |
|---|---|
| Product | HisabhParakh; Team Demons; structured voucher classification |
| Generation | `google/gemma-4-E4B-it`, local, through Ollama initially |
| Runtime candidate | `gemma4:e4b-it-q4_K_M`; resolve and pin digest after smoke test |
| Embeddings | `google/embeddinggemma-2`; text-only CPU path, float32 initially, 768d |
| Search | Qdrant cosine search, restrictive provenance/split/version filters |
| Source of record | SQLite + SQLAlchemy + Alembic; WAL, foreign keys, bounded writes |
| API | Python + FastAPI + Pydantic + Uvicorn |
| UI | Next.js + React + TypeScript + Tailwind + shadcn/ui + TanStack Table + Recharts |
| Workbook | OpenPyXL for preservation; Pandas for analysis where helpful |
| Evaluation | scikit-learn, NumPy, pytest; actual labeled measurements |
| Deployment | Docker Compose; local host-runtime option for Windows/WSL2 |
| Hardware target | RTX 4060 8 GB VRAM, 16 GB RAM; supplied target, not inspected hardware |
| Generative budget | At most 2 attempted calls per row, shared by classification, repair and optional model verifier |
| Adaptation | Supervised policy/ontology/retrieval edits, fixed base-model weights |

Retain the earlier project's no-Qwen restriction: no alternative model-family fallback. A runtime contingency may use llama.cpp with the same E4B model, after compatibility checks and a new benchmark. Streamlit is only a time-pressure UI replacement using the same backend; do not build two UIs in parallel.

Google's card lists E4B as 4.5B effective parameters and 8B with embeddings; model release license is Apache 2.0. This does not establish laptop memory fit. Model identity and the proposed Q4 artifact were checked against [Google's model card](https://ai.google.dev/gemma/docs/core/model_card_4) and [Ollama's artifact page](https://ollama.com/library/gemma4:e4b-it-q4_K_M). Pin tested dependency versions; do not invent a compatible version combination.

### Pending inputs: do not guess

| ID | Missing input | Blocks | Work that can continue |
|---|---|---|---|
| G1 | Official taxonomy, definitions and IDs; class count disputed in earlier material | Real classification and submission validity | Ontology loader, profiler, synthetic contract fixtures |
| G2 | Representative workbook; which sheets/rows constitute transactions; multi-line invoice policy | Organizer-compatible normalization and row reconciliation | Configurable mapper and marked synthetic workbooks |
| G3 | Exact JSON envelope, keys, order, row identity, abstention and best-effort rules | Strict submission export | Full review JSON/XLSX |
| G4 | Permitted reference labels, reviewer authority and split policy | Quality claims, trusted retrieval content, self-healing promotion | Empty-memory classification after G1; fixture tests |
| G5 | Actual model/runtime/host smoke test and resource budget | Deployment/performance claims | Adapter contracts and visibly mocked tests |
| G6 | Deadline and submission rubric | Precise time estimates and final prioritization | Dependency-ordered plan and conditional scope ladder |

Missing official labels must block classification, not create an invented 27/28-class ontology. Missing examples must allow explicit ontology-only classification. Missing trusted labels must disable supervised repair.
