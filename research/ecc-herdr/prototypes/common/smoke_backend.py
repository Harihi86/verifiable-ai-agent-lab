"""Smoke test: start a disposable, fully isolated Herdr backend and exercise read-only CLI/API calls.

Usage:  python C:\\Herdr-dev\\prototypes\\common\\smoke_backend.py

Writes everything under C:\\Herdr-dev\\runtime\\sessions\\<session>\\ and prints a JSON summary.
It also records whether well-known production/user Herdr roots changed during the run.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import herdr_isolated as hi  # noqa: E402

OUTSIDE_ROOTS = [
    Path(os.environ.get("APPDATA", r"C:\__missing__")) / "herdr",
    Path(os.environ.get("APPDATA", r"C:\__missing__")) / "herdr-dev",
    Path(os.environ.get("LOCALAPPDATA", r"C:\__missing__")) / "herdr",
    Path(os.environ.get("LOCALAPPDATA", r"C:\__missing__")) / "herdr-dev",
    Path(r"C:\herdr\.local\<private>"),
    Path(r"C:\herdr\.local\<private>"),
    Path(r"C:\herdr\.local\<private>"),
]


def snapshot_outside() -> dict:
    out = {}
    for root in OUTSIDE_ROOTS:
        if not root.exists():
            out[str(root)] = {"exists": False}
            continue
        latest = 0.0
        count = 0
        for item in root.rglob("*"):
            try:
                st = item.stat()
            except OSError:
                continue
            count += 1
            latest = max(latest, st.st_mtime)
        out[str(root)] = {"exists": True, "entries": count, "latest_mtime": latest}
    return out


def main() -> int:
    rt = hi.IsolatedRuntime(session_name=hi.unique_session_name("smoke"))
    rt.prepare()
    record_path = rt.write_resolution_record()
    before = snapshot_outside()
    steps: list[dict] = []

    def step(name: str, *args: str, timeout: float = 60.0):
        completed = rt.run(*args, timeout=timeout)
        steps.append(
            {
                "step": name,
                "argv": rt.command(*args),
                "exit": completed.returncode,
                "stdout_head": completed.stdout[:3000],
                "stderr_head": completed.stderr[:1500],
            }
        )
        return completed

    step("version", "--version")
    step("server-help", "server", "--help")
    step("workspace-list-before-server", "workspace", "list")

    process = rt.start_server()
    ready = rt.wait_for_ping(timeout=40)
    steps.append({"step": "server-ready", "ready": ready, "pid": process.pid})
    schema_path = rt.log_dir / "herdr-api.schema.json"
    if ready:
        step("session-list", "session", "list", "--json")
        step("api-schema", "api", "schema", "--output", str(schema_path))
        step("api-snapshot", "api", "snapshot")
        step("workspace-list", "workspace", "list")
        step("pane-list", "pane", "list")
        step("agent-list", "agent", "list")
        step("plugin-list", "plugin", "list")
        step("server-agent-manifests", "server", "agent-manifests", "--json")
    stop_code = rt.stop_server(process)
    steps.append({"step": "server-stop", "process_exit": stop_code})

    after = snapshot_outside()
    created = sorted(str(p.relative_to(rt.root)) for p in rt.root.rglob("*") if p.is_file())
    report = {
        "resolution": json.loads(record_path.read_text(encoding="utf-8")),
        "outside_before": before,
        "outside_after": after,
        "outside_unchanged": before == after,
        "steps": steps,
        "files_created_under_root": created,
        "schema_bytes": schema_path.stat().st_size if schema_path.exists() else 0,
    }
    (rt.log_dir / "smoke-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = {
        "session": rt.session_name,
        "root": str(rt.root),
        "ready": ready,
        "outside_unchanged": before == after,
        "server_process_exit": stop_code,
        "schema_bytes": report["schema_bytes"],
        "steps": [(s.get("step"), s.get("exit", s.get("ready", s.get("process_exit")))) for s in steps],
    }
    print(json.dumps(summary, indent=2))
    return 0 if ready and before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
