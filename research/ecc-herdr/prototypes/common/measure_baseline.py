"""Baseline resource/latency measurements for the isolated Herdr backend (no plugins).

Usage: python C:\\Herdr-dev\\prototypes\\common\\measure_baseline.py [--runs N] [--label text]

Measures, on this machine only:
  - server start -> first successful `workspace list` (ms)
  - CLI round-trip latency of `workspace list` over N runs (ms: min / median / p95)
  - server process working set (bytes) via PowerShell Get-Process after warm-up
Writes JSON to <session root>\\logs\\measure-<label>.json and prints a summary.
These numbers describe the research machine and binary only; they are not benchmarks of Herdr itself.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import herdr_isolated as hi  # noqa: E402


def working_set_bytes(pid: int) -> int | None:
    try:
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"(Get-Process -Id {pid}).WorkingSet64",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return int(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else None
    except (subprocess.SubprocessError, ValueError):
        return None


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(pct / 100.0 * (len(ordered) - 1)))))
    return ordered[index]


def measure(runtime: hi.IsolatedRuntime, runs: int, label: str) -> dict:
    runtime.prepare()
    runtime.write_resolution_record()
    t0 = time.perf_counter()
    process = runtime.start_server()
    ready = runtime.wait_for_ping(timeout=60, interval=0.1)
    start_ms = (time.perf_counter() - t0) * 1000.0
    result: dict = {"label": label, "session": runtime.session_name, "ready": ready, "start_to_ready_ms": start_ms}
    if ready:
        for _ in range(3):  # warm-up
            runtime.run("workspace", "list")
        samples = []
        for _ in range(runs):
            t1 = time.perf_counter()
            completed = runtime.run("workspace", "list")
            samples.append((time.perf_counter() - t1) * 1000.0)
            if completed.returncode != 0:
                result.setdefault("errors", []).append(completed.stderr[:300])
        result["cli_roundtrip_ms"] = {
            "runs": runs,
            "min": min(samples),
            "median": statistics.median(samples),
            "p95": percentile(samples, 95),
            "max": max(samples),
        }
        result["server_working_set_bytes"] = working_set_bytes(process.pid)
    exit_code = runtime.stop_server(process)
    result["server_exit"] = exit_code
    (runtime.log_dir / f"measure-{label}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--label", default="baseline")
    args = parser.parse_args()
    runtime = hi.IsolatedRuntime(session_name=hi.unique_session_name(f"measure-{args.label}"))
    result = measure(runtime, args.runs, args.label)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
