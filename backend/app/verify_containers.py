"""Create isolated synthetic probes, recreate containers, verify volumes, clean up."""
import json
import subprocess
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from app.settings import ROOT


def docker(*arguments):
    return subprocess.check_output(["docker", "compose", *arguments], cwd=ROOT, text=True)


def main():
    marker = "smoke_" + uuid4().hex
    report = {"kind": "synthetic_container_persistence_probe", "started_at": datetime.now(timezone.utc).isoformat()}
    with httpx.Client(base_url="http://127.0.0.1:6333", timeout=15, trust_env=False) as client:
        try:
            response = client.put(f"/collections/{marker}", json={"vectors": {"size": 768, "distance": "Cosine"}})
            response.raise_for_status()
            response = client.put(f"/collections/{marker}/points?wait=true", json={"points": [{"id": 1, "vector": [1.0] + [0.0] * 767, "payload": {"role": "synthetic_infrastructure_probe"}}]})
            response.raise_for_status()
            script = "import sqlite3,sys; c=sqlite3.connect('/app/storage/hisabhparakh.db'); c.execute('INSERT INTO datasets VALUES (?,?,?,?)',(sys.argv[1],'0'*64,'synthetic_probe','synthetic')); c.commit()"
            docker("exec", "-T", "backend", "python", "-c", script, marker)
            docker("up", "-d", "--force-recreate", "--no-deps", "--wait", "--wait-timeout", "90", "qdrant", "backend")
            script = "import sqlite3,sys; c=sqlite3.connect('/app/storage/hisabhparakh.db'); assert c.execute('SELECT source_sha256 FROM datasets WHERE id=?',(sys.argv[1],)).fetchone()==('0'*64,); print('persisted')"
            assert "persisted" in docker("exec", "-T", "backend", "python", "-c", script, marker)
            response = client.get(f"/collections/{marker}/points/1")
            response.raise_for_status()
            assert response.json()["result"]["payload"]["role"] == "synthetic_infrastructure_probe"
            report.update(sqlite_survives_recreation=True, qdrant_survives_recreation=True)
        finally:
            response = client.delete(f"/collections/{marker}")
            response.raise_for_status()
            script = "import sqlite3,sys; c=sqlite3.connect('/app/storage/hisabhparakh.db'); c.execute('DELETE FROM datasets WHERE id=?',(sys.argv[1],)); c.commit()"
            docker("exec", "-T", "backend", "python", "-c", script, marker)
    report["synthetic_probes_removed"] = True
    (ROOT / "docs/evidence/container-persistence.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("SQLite and Qdrant survived container recreation; synthetic probes removed.")


if __name__ == "__main__":
    main()
