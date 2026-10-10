from typing import Literal

from app.routing.ontology import OntologyProvider
from app.schemas import CanonicalTransaction, ModelProposal

VERIFIER_VERSION = "evidence-v4-smart"


def meaningful_missing(values: list[str]) -> list[str]:
    empty = {"", "none", "n/a", "na", "null", "not applicable", "no missing evidence"}
    return [v for v in values if v.strip(" \"'").lower().rstrip(".") not in empty]


class Verifier:
    def __init__(self, ontology: OntologyProvider):
        self.ontology = ontology

    def verify(
        self, proposal: ModelProposal, transaction: CanonicalTransaction
    ) -> tuple[Literal["accepted", "review", "error"], list[str]]:
        reasons: list[str] = []

        # ── Hard gate: label must exist ──
        if not proposal.proposed_label:
            reasons.append("MISSING_LABEL")
            return "error", reasons

        entry = self.ontology.get_by_name(proposal.proposed_label)
        if not entry:
            reasons.append("INVALID_LABEL")
            return "error", reasons

        # ── Ambiguous Category check: route to review ──
        has_review = False
        if proposal.top_alternative and proposal.top_alternative.strip(" \"'").lower().rstrip(".") not in {"", "none", "n/a", "na", "null"}:
            rival = self.ontology.get_by_name(proposal.top_alternative)
            if not rival:
                # Invalid rival is just a note, not a blocker
                reasons.append("INVALID_RIVAL_LABEL_NOTE")
            else:
                # A valid rival means the model found the transaction ambiguous
                reasons.append("AMBIGUOUS_CATEGORY")
                has_review = True

        # ── Evidence path cleaning (prefix stripping + value stripping + fuzzy match) ──
        signal_names = {s.name for s in transaction.signals if s.value is not None}
        signal_names_lower = {s.lower() for s in signal_names}
        # Build a reverse map: base canonical name → set of bracket-indexed signal names
        # e.g. "narration" → {"narration[Description]", "narration[Notes]"}
        # This allows cleaned paths (with brackets stripped) to match their originals.
        base_to_signals: dict[str, set[str]] = {}
        for sn in signal_names:
            if "[" in sn:
                base = sn.split("[", 1)[0]
                base_to_signals.setdefault(base, set()).add(sn)
            base_to_signals.setdefault(sn, set()).add(sn)
        _KNOWN_PREFIXES = ("TRANSACTION DATA.", "TRANSACTION_DATA.", "SIGNALS.", "DATA.")
        cleaned_paths: list[str] = []
        for path in proposal.evidence_paths:
            cleaned = path
            # Strip known section prefixes
            for prefix in _KNOWN_PREFIXES:
                if path.upper().startswith(prefix.upper()):
                    cleaned = path[len(prefix):]
                    break
            # Strip ": value" suffix (LLM writes "key: value" instead of just "key")
            if ": " in cleaned:
                cleaned = cleaned.split(": ", 1)[0]
            # Strip bracket indexes like "narration[Description]" → "narration"
            if "[" in cleaned:
                cleaned = cleaned.split("[", 1)[0]
            cleaned = cleaned.strip()
            # Fuzzy match: if exact match fails, try case-insensitive
            if cleaned not in signal_names and cleaned.lower() in signal_names_lower:
                for real_name in signal_names:
                    if real_name.lower() == cleaned.lower():
                        cleaned = real_name
                        break
            # Resolve bracket-stripped base names back to an actual signal name
            if cleaned not in signal_names and cleaned in base_to_signals:
                # Use the first matching bracket-indexed signal name
                cleaned = next(iter(base_to_signals[cleaned]))
            # Case-insensitive fallback for base names
            if cleaned not in signal_names:
                cleaned_lower = cleaned.lower()
                for base, sigs in base_to_signals.items():
                    if base.lower() == cleaned_lower:
                        cleaned = next(iter(sigs))
                        break
            cleaned_paths.append(cleaned)
        proposal.evidence_paths = cleaned_paths

        # ── Evidence check: only error if ALL paths are invalid ──
        valid_paths = [p for p in proposal.evidence_paths if p in signal_names]
        invalid_paths = [p for p in proposal.evidence_paths if p not in signal_names]

        if proposal.evidence_paths and not valid_paths:
            # Every single evidence path is wrong — this is a real error, retry will help
            for p in invalid_paths:
                reasons.append(f"UNSUPPORTED_EVIDENCE_PATH:{p}")
            reasons.append("UNSUPPORTED_EVIDENCE")
            return "error", reasons

        # If some paths are valid, accept (partial evidence is fine)
        if invalid_paths:
            reasons.append("PARTIAL_EVIDENCE_MISMATCH")
            has_review = True

        # ── No evidence at all: soft review (but only if no evidence_paths provided) ──
        if not proposal.evidence_paths:
            reasons.append("NO_OBSERVED_EVIDENCE")
            has_review = True

        # ── Check missing evidence ──
        if meaningful_missing(proposal.missing_evidence):
            reasons.append("MISSING_EVIDENCE")
            has_review = True

        # ── Check parse issues for contradictory evidence (amounts) ──
        if transaction.parse_issues:
            for issue in transaction.parse_issues:
                if issue.startswith("MULTIPLE_SOURCE_VALUES:"):
                    field = issue.split(":")[1].lower()
                    if field not in ("narration", "description", "notes", "particulars"):
                        reasons.append("CONFLICTING_EVIDENCE")
                        has_review = True
                        break

        # ── Check unapproved precedence ──
        if proposal.top_alternative and proposal.proposed_label:
            lbl = proposal.proposed_label.lower()
            riv = proposal.top_alternative.lower()
            pair = {lbl, riv}
            if ("import" in pair or "export" in pair) and ("purchase" in pair or "sales" in pair):
                reasons.append("UNRESOLVED_CONFUSION_BOUNDARY")
                has_review = True

        if has_review:
            return "review", reasons

        return "accepted", reasons

