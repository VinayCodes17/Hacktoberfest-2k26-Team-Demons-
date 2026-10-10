"""SYNTHETIC TEST DOUBLES ONLY: never import into production app code."""
from app.schemas import CanonicalTransaction, ModelProposal


class SyntheticGenerator:
    def propose(self, transaction: CanonicalTransaction) -> ModelProposal:
        return ModelProposal(proposed_label=None, top_alternative=None, evidence_paths=[],
                             missing_evidence=["synthetic fixture"], rationale_summary="Test double; no inference")


class SyntheticEncoder:
    def encode_query(self, text: str) -> list[float]:
        return [1.0] + [0.0] * 767

    def encode_document(self, text: str) -> list[float]:
        return self.encode_query(text)
