from app.schemas import CanonicalTransaction, FinancialSignal
from app.routing.ontology import OntologyProvider

class FinancialRouter:
    def __init__(self, ontology: OntologyProvider):
        self.ontology = ontology

    def route(self, transaction: CanonicalTransaction) -> list[str]:
        """
        Returns candidate voucher names based on financial signals.
        Preserves rivals and uses all labels under weak evidence.
        """
        candidates = set()
        signals = transaction.signals
        
        # If no signals or very weak evidence, return all labels as fallback
        if not signals:
            return [e.name for e in self.ontology.get_all()]
            
        # Here we'd implement ontology-backed financial signals and candidate ranking.
        # For MVP, we return all names to ensure we do not drop true labels.
        return [e.name for e in self.ontology.get_all()]
