from app.retrieval.encoder import TextEncoder, get_text_hash
from app.retrieval.retriever import ExampleRetriever


def test_encoder_hash():
    assert get_text_hash("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

def test_encoder_mock():
    encoder = TextEncoder()
    vec = encoder.encode("test", kind="query")
    assert len(vec) == 768

def test_retriever_empty():
    encoder = TextEncoder()
    retriever = ExampleRetriever(encoder)
    results = retriever.retrieve_examples("query", candidates=["Payment"])
    assert results == []
