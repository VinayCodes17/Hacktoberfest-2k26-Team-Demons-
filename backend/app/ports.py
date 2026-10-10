"""Interfaces only; test doubles live in tests, never in application readiness."""

from typing import Protocol

from app.schemas import CanonicalTransaction, ModelProposal


class GenerationPort(Protocol):
    def propose(self, transaction: CanonicalTransaction) -> ModelProposal: ...


class EmbeddingPort(Protocol):
    def encode_query(self, text: str) -> list[float]: ...
    def encode_document(self, text: str) -> list[float]: ...
