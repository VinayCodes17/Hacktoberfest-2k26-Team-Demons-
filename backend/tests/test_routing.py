from app.routing.ontology import OntologyProvider
from app.routing.router import FinancialRouter
from app.schemas import CanonicalTransaction, SourceRow


def test_ontology_provider(tmp_path):
    ontology_path = tmp_path / "ontology.json"
    ontology_path.write_text('{"entries": [{"name": "Payment", "family": "Banking", "definition": "test", "source_url": "url", "source_row": 1, "boundary": "bound", "provenance": "prov"}]}')
    
    provider = OntologyProvider(ontology_path)
    assert len(provider.get_all()) == 1
    payment = provider.get_by_name("Payment")
    assert payment is not None
    assert payment.family == "Banking"
    assert provider.get_by_family("Banking")[0].name == "Payment"

def test_router(tmp_path):
    ontology_path = tmp_path / "ontology.json"
    ontology_path.write_text('{"entries": [{"name": "Payment", "family": "Banking", "definition": "test", "source_url": "url", "source_row": 1, "boundary": "bound", "provenance": "prov"}]}')
    provider = OntologyProvider(ontology_path)
    router = FinancialRouter(provider)
    
    transaction = CanonicalTransaction(
        id="t1",
        sources=[SourceRow(dataset_id="mock", sheet="mock", physical_row=1, source_sha256="a" * 64, cells=[])],
        document={},
        parties={},
        accounts={},
        amounts={},
        signals=[]
    )
    
    candidates = router.route(transaction)
    assert candidates == ["Payment"]
