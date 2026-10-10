import hashlib
import json
import os
from pathlib import Path
from typing import Any

class InferenceCache:
    def __init__(self, cache_dir: str = ".cache/inference"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_request(self, model_name: str, prompt: str, settings_dict: dict) -> str:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "settings": settings_dict
        }
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def get(self, model_name: str, prompt: str, settings_dict: dict) -> dict[str, Any] | None:
        key = self._hash_request(model_name, prompt, settings_dict)
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def set(self, model_name: str, prompt: str, settings_dict: dict, result: dict[str, Any]):
        key = self._hash_request(model_name, prompt, settings_dict)
        cache_file = self.cache_dir / f"{key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f)
