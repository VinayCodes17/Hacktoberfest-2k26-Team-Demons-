import json
from pathlib import Path
from app.schemas import OntologyEntry

class OntologyProvider:
    def __init__(self, ontology_path: Path):
        self.ontology_path = ontology_path
        self._entries: list[OntologyEntry] = []
        self._load()

    def _load(self):
        if not self.ontology_path.exists():
            return
        data = json.loads(self.ontology_path.read_text())
        entries = data.get("entries", [])
        self._entries = [OntologyEntry(**entry) for entry in entries]

    def get_all(self) -> list[OntologyEntry]:
        return self._entries

    def get_by_family(self, family: str) -> list[OntologyEntry]:
        return [e for e in self._entries if e.family == family]

    def get_by_name(self, name: str) -> OntologyEntry | None:
        for e in self._entries:
            if e.name == name:
                return e
        return None
