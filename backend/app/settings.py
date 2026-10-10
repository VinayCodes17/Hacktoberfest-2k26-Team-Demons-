"""Validated local-only service configuration. No model loads at import."""
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="forbid")

    database_path: Path = ROOT / "storage" / "hisabhparakh.db"
    taxonomy_path: Path = ROOT / "backend" / "ontology" / "workbook-seed.json"
    gemma_model_id: Literal["google/gemma-4-E4B-it"] = "google/gemma-4-E4B-it"
    gemma_runtime_model: Literal["gemma4:e4b-it-q4_K_M"] = "gemma4:e4b-it-q4_K_M"
    gemma_model_digest: str = Field(
        default="dc35e8d9c6061baa6f0fa870975ab6932e2542b579b13ea0f199fa4bb7300c9c",
        pattern=r"^[a-f0-9]{64}$",
    )
    ollama_base_url: Literal["http://127.0.0.1:11434", "http://localhost:11434", "http://host.docker.internal:11434"] = "http://127.0.0.1:11434"
    qdrant_url: Literal["http://127.0.0.1:6333", "http://qdrant:6333"] = "http://127.0.0.1:6333"
    embedding_url: Literal["http://127.0.0.1:11435", "http://embeddings:11435"] = "http://127.0.0.1:11435"
    gemma_num_ctx: int = Field(default=4096, ge=512, le=4096)
    generation_concurrency: Literal[1] = 1
    max_model_calls_per_row: Literal[2] = 2
    embedding_model_id: Literal["google/embeddinggemma-2"] = "google/embeddinggemma-2"
    embedding_device: Literal["cpu"] = "cpu"
    embedding_dim: Literal[768] = 768
    embedding_revision: str = "914f7f89142e33e77833254d9c9b90c3cef7303b"

    @field_validator("generation_concurrency", "max_model_calls_per_row", "embedding_dim", mode="before")
    @classmethod
    def parse_fixed_integers(cls, value: object) -> int:
        if isinstance(value, str) and value.isdecimal():
            return int(value)
        if type(value) is int:
            return value
        raise ValueError("Expected an integer setting")

    @field_validator("database_path", "taxonomy_path")
    @classmethod
    def resolve_paths(cls, path: Path) -> Path:
        return (ROOT / path).resolve() if not path.is_absolute() else path.resolve()

    @field_validator("embedding_revision")
    @classmethod
    def revision_is_pinned(cls, value: str) -> str:
        if value and (len(value) != 40 or any(c not in "0123456789abcdef" for c in value)):
            raise ValueError("Embedding revision must be empty or a 40-character commit")
        return value
