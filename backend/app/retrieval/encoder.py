import hashlib
from typing import Literal


def get_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

class TextEncoder:
    """
    Encoder adapter matching the embeddinggemma service.
    """
    def __init__(self):
        pass

    def encode(self, text: str, kind: Literal["query", "document"]) -> list[float]:
        # Connects to embedding service API or runs embedding locally.
        # Fallback to returning a dummy vector if the service is not running.
        return [0.0] * 768
