"""Offline-only embedding check; absent packages/cache are explicit blockers."""

import argparse
import importlib.metadata
import json
import math
import re
import time
from pathlib import Path

from app.workbook_seed import write_json


def validate_vectors(vectors):
    if len(vectors) != 2:
        raise ValueError("Expected query and document vectors")
    for vector in vectors:
        if len(vector) != 768 or not all(math.isfinite(float(x)) for x in vector):
            raise ValueError("Expected finite 768-dimensional vectors")
        norm = math.sqrt(sum(float(x) ** 2 for x in vector))
        if abs(norm - 1) > 1e-4:
            raise ValueError("Expected normalized vectors")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot", type=Path, help="Local HF snapshot directory, named by its 40-character revision"
    )
    parser.add_argument("--output", type=Path, default=Path("../docs/evidence/embedding-smoke.json"))
    args = parser.parse_args()
    started = time.monotonic()
    report = {
        "model_id": "google/embeddinggemma-2",
        "status": "blocked",
        "live_inference": False,
        "device": "cpu",
        "dtype": "float32",
        "dimensions": 768,
        "blockers": [],
    }
    for package in ("torch", "sentence-transformers", "transformers"):
        try:
            report[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report["blockers"].append(f"Package not installed: {package}")
    if args.snapshot is None or not args.snapshot.is_dir():
        report["blockers"].append("Pinned local EmbeddingGemma 2 snapshot not supplied")
    elif not re.fullmatch(r"[a-f0-9]{40}", args.snapshot.name):
        report["blockers"].append("Snapshot directory must identify its immutable 40-character revision")
    if not report["blockers"]:
        try:
            import torch
            from sentence_transformers import SentenceTransformer

            report["revision"] = args.snapshot.name
            torch.set_num_threads(2)
            model = SentenceTransformer(
                str(args.snapshot),
                device="cpu",
                local_files_only=True,
                trust_remote_code=True,
                config_kwargs={"vision_config": None, "audio_config": None},
                model_kwargs={"torch_dtype": torch.float32},
            )
            config = model[0].auto_model.config
            if (
                getattr(config, "vision_config", None) is not None
                or getattr(config, "audio_config", None) is not None
            ):
                raise ValueError("Unused modality configurations remain enabled")
            parameter_names = [name for name, _ in model.named_parameters()]
            if any("vision_tower" in name or "audio_tower" in name for name in parameter_names):
                raise ValueError("Unused modality parameters were loaded")
            if any(p.device.type != "cpu" or p.dtype != torch.float32 for p in model.parameters()):
                raise ValueError("Parameters are not CPU float32")
            if not model.prompts.get("SearchQuery") or not model.prompts.get("Document"):
                raise ValueError("Checkpoint query/document prefixes missing")
            report["prefixes"] = {name: model.prompts[name] for name in ("SearchQuery", "Document")}
            query = model.encode(
                ["Synthetic zero amount, currency missing"],
                prompt_name="SearchQuery",
                normalize_embeddings=True,
            )
            document = model.encode(
                ["Synthetic test document"], prompt_name="Document", normalize_embeddings=True
            )
            validate_vectors([query[0], document[0]])
            report["parameter_count"] = sum(p.numel() for p in model.parameters())
            report["norms"] = [float((vector**2).sum() ** 0.5) for vector in (query[0], document[0])]
            report.update(status="passed", live_inference=True, unused_modalities_loaded=False)
        except Exception as error:
            report.update(status="failed", error=f"{type(error).__name__}: {error}")
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    write_json(args.output, report)
    print(json.dumps(report))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
