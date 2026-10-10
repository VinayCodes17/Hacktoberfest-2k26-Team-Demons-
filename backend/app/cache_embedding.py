"""Explicit online setup; runtime model loading remains offline and pinned."""
import json
import os
from pathlib import Path

from app.settings import ROOT


def main():
    os.environ.setdefault("HF_XET_CACHE", str(ROOT / "storage/huggingface/xet"))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    from huggingface_hub import snapshot_download

    manifest = json.loads((ROOT / "backend/embedding-model.json").read_text())
    snapshot = snapshot_download(
        repo_id=manifest["model_id"], revision=manifest["revision"],
        cache_dir=ROOT / "storage/huggingface", token=False,
        allow_patterns=["*.json", "*.safetensors", "*.model", "*.jinja", "README.md"],
        max_workers=2,
    )
    if Path(snapshot).name != manifest["revision"]:
        raise ValueError("Snapshot revision mismatch")
    print("Pinned EmbeddingGemma 2 snapshot cached in project storage.")


if __name__ == "__main__":
    main()
