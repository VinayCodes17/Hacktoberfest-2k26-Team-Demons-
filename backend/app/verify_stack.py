"""Bounded HTTP smoke against owned processes; no browser or model inference."""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

from app.settings import ROOT


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def get(url: str) -> tuple[int, str]:
    try:
        with build_opener(ProxyHandler({})).open(url, timeout=8) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as error:
        return error.code, error.read().decode("utf-8")


def wait_for(url: str) -> tuple[int, str]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            return get(url)
        except (URLError, TimeoutError, ConnectionError):
            time.sleep(0.3)
    raise RuntimeError("Local service startup timed out")


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main():
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node is required")
    backend_port, frontend_port = free_port(), free_port()
    while frontend_port == backend_port:
        frontend_port = free_port()
    api_url = f"http://127.0.0.1:{backend_port}"
    ui_url = f"http://127.0.0.1:{frontend_port}"
    processes = []
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with tempfile.TemporaryFile() as output:
        try:
            backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "127.0.0.1", "--port", str(backend_port), "--workers", "1", "--no-access-log"], cwd=ROOT / "backend", stdout=output, stderr=output, creationflags=flags)
            processes.append(backend)
            health_status, _ = wait_for(api_url + "/api/v1/health")
            readiness_status, data = get(api_url + "/api/v1/readiness")
            readiness = json.loads(data)
            assert health_status == 200 and readiness_status == 200 and readiness["service_ready"]
            frontend = subprocess.Popen([node, str(ROOT / "frontend/node_modules/next/dist/bin/next"), "start", "--hostname", "127.0.0.1", "--port", str(frontend_port)], cwd=ROOT / "frontend", env={**os.environ, "HISABHPARAKH_API_URL": api_url, "NEXT_TELEMETRY_DISABLED": "1"}, stdout=output, stderr=output, creationflags=flags)
            processes.append(frontend)
            online_status, html = wait_for(ui_url)
            assert online_status == 200 and "Service readiness" in html
            assert "The foundation is taking shape." in html
            for check in readiness["checks"]:
                assert check["name"] in html
            assert "The local API isn’t connected." not in html
            stop(backend)
            offline_status, offline_html = get(ui_url)
            assert offline_status == 200 and "The local API isn’t connected." in offline_html
            report = {"kind": "live_local_HTTP_integration_no_browser_no_inference", "api_health_status": health_status,
                      "api_readiness_status": readiness_status, "readiness": readiness,
                      "ui_online_status": online_status, "ui_live_checks_rendered": True,
                      "ui_offline_status": offline_status, "ui_offline_state_rendered": True,
                      "owned_processes_stopped": True}
            destination = ROOT / "docs/evidence/p01-http-smoke.json"
            destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print("Live API + production UI HTTP smoke passed; online and offline states verified.")
        finally:
            for process in reversed(processes):
                stop(process)


if __name__ == "__main__":
    main()
