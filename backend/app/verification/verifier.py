from typing import Literal

from app.routing.ontology import OntologyProvider
from app.schemas import CanonicalTransaction, ModelProposal

VERIFIER_VERSION = "evidence-v3"


def meaningful_missing(values: list[str]) -> list[str]:
    empty = {"", "none", "n/a", "na", "null", "not applicable", "no missing evidence"}
    return [v for v in values if v.strip().lower().rstrip(".") not in empty]


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

        if self.ontology.confusion_boundaries and proposal.proposed_label in {
            "Import",
            "Export",
            "Other / Miscellaneous",
        }:
            reasons.append("UNRESOLVED_CATEGORY_PRECEDENCE")

        if proposal.top_alternative:
            rival = self.ontology.get_by_name(proposal.top_alternative)
            if not rival:
                reasons.append("INVALID_RIVAL_LABEL")
            pair = {proposal.proposed_label, proposal.top_alternative}
            if pair in ({"Import", "Purchase"}, {"Export", "Sales"}) and any(
                pair == {boundary["candidate_a"], boundary["candidate_b"]}
                for boundary in self.ontology.confusion_boundaries
            ):
                # These two custom-category precedence policies remain unapproved.
                reasons.append("UNRESOLVED_CONFUSION_BOUNDARY")

        # Check evidence paths exist in transaction signals
        signal_names = {s.name for s in transaction.signals if s.status != "unknown" and s.value is not None}
        for path in proposal.evidence_paths:
            # We assume evidence path relates to a signal name or missing path
            if path not in signal_names:
                reasons.append(f"UNSUPPORTED_EVIDENCE_PATH:{path}")

        if any(r.startswith("UNSUPPORTED_EVIDENCE_PATH") for r in reasons):
            reasons.append("UNSUPPORTED_EVIDENCE")
            return "error", reasons

        if not proposal.evidence_paths:
            reasons.append("NO_OBSERVED_EVIDENCE")

        if meaningful_missing(proposal.missing_evidence):
            reasons.append("MISSING_DECISIVE_EVIDENCE")
            return "review", reasons

        # Supplementary narration is contextual text, not conflicting numeric data.
        issues = [
            issue
            for issue in transaction.parse_issues
            if not issue.startswith("MULTIPLE_SOURCE_VALUES:narration:")
        ]
        if issues:
            reasons.append("SOURCE_PARSE_ISSUES")

        # If no reasons, accept
        if not reasons:
            return "accepted", []

        return "review", reasons
