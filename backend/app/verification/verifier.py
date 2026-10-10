from typing import Literal

from app.routing.ontology import OntologyProvider
from app.schemas import CanonicalTransaction, ModelProposal


class Verifier:
    def __init__(self, ontology: OntologyProvider):
        self.ontology = ontology

    def verify(self, proposal: ModelProposal, transaction: CanonicalTransaction) -> tuple[Literal["accepted", "review", "error"], list[str]]:
        reasons = []

        # Check label membership
        if not proposal.proposed_label:
            reasons.append("MISSING_LABEL")
            return "review", reasons
        
        entry = self.ontology.get_by_name(proposal.proposed_label)
        if not entry:
            reasons.append("INVALID_LABEL")
            return "error", reasons

        if proposal.top_alternative:
            rival = self.ontology.get_by_name(proposal.top_alternative)
            if not rival:
                reasons.append("INVALID_RIVAL_LABEL")

        # Check evidence paths exist in transaction signals
        signal_names = {s.name for s in transaction.signals}
        for path in proposal.evidence_paths:
            # We assume evidence path relates to a signal name or missing path
            if path not in signal_names and path not in transaction.missing_paths:
                reasons.append(f"UNSUPPORTED_EVIDENCE_PATH:{path}")

        if any(r.startswith("UNSUPPORTED_EVIDENCE_PATH") for r in reasons):
            reasons.append("UNSUPPORTED_EVIDENCE")
            return "error", reasons

        if proposal.missing_evidence:
            reasons.append("MISSING_DECISIVE_EVIDENCE")
            return "review", reasons

        # If no reasons, accept
        if not reasons:
            return "accepted", []

        return "review", reasons
