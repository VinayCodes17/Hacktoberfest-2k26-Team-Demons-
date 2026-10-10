from app.retrieval.encoder import TextEncoder

class ExampleRetriever:
    """
    Retrieves trusted exemplars and development errors based on semantic search.
    """
    def __init__(self, encoder: TextEncoder):
        self.encoder = encoder
    
    def retrieve_examples(self, query: str, candidates: list[str], max_results: int = 5) -> list[dict]:
        """
        In a real implementation, this would search Qdrant using the query vector.
        Balance examples across competing classes, deduplicate and enforce a context budget.
        Never use the unknown query gold label to choose exemplars.
        Fallback to returning no examples if Qdrant isn't ready or memory is empty.
        """
        vector = self.encoder.encode(query, kind="query")
        
        # Empty reference memory is a normal no-retrieval mode.
        return []
