import hashlib
import math
from typing import Literal

import httpx


def get_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TextEncoder:
    def __init__(self, endpoint: str = "http://127.0.0.1:11435/embed"):
        self.endpoint = endpoint
        self.client = httpx.Client(timeout=30.0, trust_env=False)

    def encode(self, text: str, kind: Literal["query", "document"]) -> list[float]:
        response = self.client.post(self.endpoint, json={"text": text, "kind": kind})
        response.raise_for_status()
        vector = response.json()["vector"]
        if len(vector) != 768 or not all(math.isfinite(x) for x in vector):
            raise ValueError("INVALID_EMBEDDING")
        if not 0.99 < sum(x * x for x in vector) < 1.01:
            raise ValueError("EMBEDDING_NOT_NORMALIZED")
        return vector
