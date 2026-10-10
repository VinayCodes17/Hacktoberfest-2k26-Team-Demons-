"""One live synthetic request, no retries and no workbook data."""
import argparse
import ctypes
import hashlib
import json
import platform
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

from app.contracts import SmokeResponse
from app.workbook_seed import write_json

MODEL = "gemma4:e4b-it-q4_K_M"
BASE = "http://127.0.0.1:11434"


def api(route, body=None, timeout=10):
    payload = None if body is None else json.dumps(body).encode()
    request = Request(BASE + route, data=payload, headers={"Content-Type": "application/json"})
    with build_opener(ProxyHandler({})).open(request, timeout=timeout) as response:
        return json.load(response)


def resources():
    result = {}
    try:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5,
                             check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        name, total, used = gpu.stdout.strip().splitlines()[0].rsplit(",", 2)
        result["gpu"] = {"name": name.strip(), "total_mib": int(total), "used_mib": int(used)}
    except (OSError, ValueError, subprocess.SubprocessError):
        result["gpu"] = None
    if platform.system() == "Windows":
        class Memory(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (key, ctypes.c_ulonglong) for key in
                ("total", "available", "page_total", "page_available", "virtual_total", "virtual_available", "extended")]
        memory = Memory()
        memory.length = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            result["host_ram"] = {"total_bytes": memory.total, "used_bytes": memory.total - memory.available}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("../docs/evidence/gemma-smoke.json"))
    args = parser.parse_args()
    report = {"kind": "live_synthetic_runtime_smoke_not_classification_benchmark",
              "started_at": datetime.now(timezone.utc).isoformat(), "model": MODEL,
              "python": platform.python_version(), "os": platform.platform(),
              "attempts": 0, "status": "failed", "resources_before": resources()}
    stop = threading.Event()
    samples = []

    def monitor():
        while not stop.is_set():
            samples.append(resources())
            stop.wait(1)

    thread = threading.Thread(target=monitor, daemon=True)
    started = time.monotonic()
    try:
        report["runtime"] = api("/api/version")
        installed = next(m for m in api("/api/tags")["models"] if m["name"] == MODEL)
        report["artifact"] = installed
        metadata = api("/api/show", {"model": MODEL})
        license_text = metadata.get("license", "")
        report["license"] = {"apache_2_0_present": "Apache License" in license_text and "Version 2.0" in license_text,
                             "sha256": hashlib.sha256(license_text.encode()).hexdigest()}
        report["capabilities"] = metadata.get("capabilities")
        report["settings"] = {"num_ctx": 4096, "num_predict": 128, "temperature": 0, "seed": 42}
        body = {"model": MODEL, "stream": False, "think": False, "keep_alive": "2m",
                "format": SmokeResponse.model_json_schema(), "options": report["settings"],
                "prompt": 'Synthetic transport test, not voucher classification. Return JSON only: '
                          '{"record_id":"SYNTHETIC-SMOKE-001","amount":"0.00","missing_currency":true}'}
        report["attempts"] = 1
        report["status"] = "attempt_reserved"
        write_json(args.output, report)
        thread.start()
        response = api("/api/generate", body, timeout=180)
        report["response"] = SmokeResponse.model_validate_json(response["response"]).model_dump()
        if response.get("done") is not True or response.get("done_reason") != "stop":
            raise ValueError("Generation did not complete normally")
        report["timings"] = {key: response.get(key) for key in
                             ("total_duration", "load_duration", "prompt_eval_count", "eval_count", "eval_duration")}
        report["loaded_runtime"] = api("/api/ps")
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        stop.set()
        if thread.is_alive():
            thread.join(timeout=6)
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["resources_after"] = resources()
        report["resource_samples"] = len(samples)
        report["sampled_peak_gpu_used_mib"] = max((s["gpu"]["used_mib"] for s in samples if s.get("gpu")), default=None)
        report["sampled_peak_host_ram_used_bytes"] = max((s["host_ram"]["used_bytes"] for s in samples if s.get("host_ram")), default=None)
        report["resource_note"] = "Whole-host sampled usage, not process allocation or guaranteed peak; full stack not measured"
        write_json(args.output, report)
    print(json.dumps({key: report[key] for key in ("status", "attempts", "elapsed_seconds")}))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
