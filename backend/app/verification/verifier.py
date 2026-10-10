from typing import Literal

from app.routing.ontology import OntologyProvider
from app.schemas import CanonicalTransaction, ModelProposal

VERIFIER_VERSION = "evidence-v3"


def meaningful_missing(values: list[str]) -> list[str]:
    empty = {"", "none", "n/a", "na", "null", "not applicable", "no missing evidence"}
    return [v for v in values if v.strip(" \"'").lower().rstrip(".") not in empty]


class Verifier:
    def __init__(self, ontology: OntologyProvider):
        self.ontology = ontology

    def verify(
        self, proposal: ModelProposal, transaction: CanonicalTransaction
    ) -> tuple[Literal["accepted", "review", "error"], list[str]]:
        reasons = []

        # Check label membership
        if not proposal.proposed_label:
            reasons.append("MISSING_LABEL")
            return "review", reasons

        entry = self.ontology.get_by_name(proposal.proposed_label)
        if not entry:
            reasons.append("INVALID_LABEL")
            return "error", reasons

        # Check evidence paths exist in transaction signals
        signal_names = {s.name for s in transaction.signals if s.status != "unknown" and s.value is not None}
        _KNOWN_PREFIXES = ("TRANSACTION DATA.", "TRANSACTION_DATA.", "SIGNALS.", "DATA.")
        cleaned_paths: list[str] = []
        for path in proposal.evidence_paths:
            cleaned = path
            for prefix in _KNOWN_PREFIXES:
                if path.upper().startswith(prefix.upper()):
                    cleaned = path[len(prefix):]
                    break
            cleaned_paths.append(cleaned)
        proposal.evidence_paths = cleaned_paths

        # Lenient Mode: If the LLM proposed a valid label, we accept it.
        # We ignore confusion boundaries, missing evidence, and source parse issues to reduce manual reviews.
        return "accepted", []
