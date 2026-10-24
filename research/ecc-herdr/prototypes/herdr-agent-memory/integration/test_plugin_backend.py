"""Integration test: research.agent-memory plugin linked into a disposable, isolated Herdr backend.

No real coding agent is involved. Agent lifecycle is simulated through Herdr's documented third-party
reporting API (`pane report-agent`, source `custom:*`), which drives the same `pane.agent_status_changed`
event path that claude/codex/cursor/grok detection would drive.

Usage: python C:\\Herdr-dev\\prototypes\\herdr-agent-memory\\integration\\test_plugin_backend.py
Exit 0 when every check passes. Writes <session root>\\logs\\plugin-integration.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

COMMON = Path(r"C:\Herdr-dev\prototypes\common")
PLUGIN_DIR = Path(r"C:\Herdr-dev\prototypes\herdr-agent-memory")
PLUGIN_ID = "research.agent-memory"
sys.path.insert(0, str(COMMON))
import herdr_isolated as hi  # noqa: E402


def main() -> int:
    rt = hi.IsolatedRuntime(session_name=hi.unique_session_name("plugin"))
    rt.prepare()
    rt.write_resolution_record()
    report: dict = {"session": rt.session_name, "root": str(rt.root), "checks": {}, "timings_ms": {}}
    checks = report["checks"]
    process = rt.start_server()
    try:
        checks["server_ready"] = rt.wait_for_ping(timeout=40)
        if not checks["server_ready"]:
            return finish(rt, report)

        # 1. Link the plugin (registry lands in the isolated XDG_CONFIG_HOME/herdr/plugins.json).
        link, link_json = rt.run_json("plugin", "link", str(PLUGIN_DIR))
        checks["plugin_link_exit"] = link.returncode
        report["plugin_link"] = link_json or {"stderr": link.stderr[:500]}
        warnings = (link_json or {}).get("result", {}).get("plugin", {}).get("warnings") or []
        checks["plugin_link_no_unknown_event_warning"] = not any("unknown event" in str(w) for w in warnings)
        cfg, cfg_json = rt.run_json("plugin", "config-dir", PLUGIN_ID)
        report["plugin_config_dir"] = (cfg.stdout or cfg.stderr).strip()[:300]
        registry = rt.herdr_config_dir("herdr") / "plugins.json"
        checks["registry_inside_isolated_config"] = registry.exists()

        # 2. A project workspace with a .git marker so the plugin derives a stable project key.
        project = rt.tmp_dir / "demo-project"
        (project / ".git").mkdir(parents=True, exist_ok=True)
        created, payload = rt.run_json("workspace", "create", "--cwd", str(project), "--label", "demo", "--no-focus")
        pane_id = payload["result"]["root_pane"]["pane_id"]
        report["pane_id"] = pane_id

        # Put some recognisable text on the pane so the capture has content.
        rt.run("pane", "run", pane_id, 'echo "edited src/app/actions.rs and tests/cli/agents.rs"')
        rt.run("pane", "wait-output", pane_id, "--match", "tests/cli/agents.rs", "--timeout", "15000")

        # 3. Simulated agent: working -> idle (this is what detection would report for a real agent).
        seq = int(time.time())
        rt.run("pane", "report-agent", pane_id, "--source", "custom:research", "--agent", "codex-sim", "--state", "working", "--seq", str(seq))
        time.sleep(0.3)
        t0 = time.perf_counter()
        idle = rt.run("pane", "report-agent", pane_id, "--source", "custom:research", "--agent", "codex-sim", "--state", "idle", "--seq", str(seq + 1))
        checks["report_idle_exit"] = idle.returncode

        # 4. Wait for the event hook to produce a vault document under the plugin state dir.
        state_dir = rt.herdr_state_dir("herdr") / "plugins" / PLUGIN_ID
        vault_files: list[Path] = []
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            vault_files = list(state_dir.rglob("mem_*.md")) if state_dir.exists() else []
            if vault_files:
                break
            time.sleep(0.2)
        report["timings_ms"]["idle_report_to_vault_file"] = (time.perf_counter() - t0) * 1000.0
        checks["vault_file_created"] = bool(vault_files)
        report["state_dir"] = str(state_dir)
        report["vault_files"] = [str(p) for p in vault_files]
        if vault_files:
            doc = vault_files[0].read_text(encoding="utf-8")
            checks["vault_doc_has_schema"] = 'schema: "herdr.agent-memory.v1"' in doc
            checks["vault_doc_names_agent"] = 'source_agent: "codex-sim"' in doc
            checks["vault_doc_has_pane_text"] = "tests/cli/agents.rs" in doc
            report["vault_doc_head"] = doc[:900]

        # 5. Plugin command log shows the hook ran and what it decided.
        time.sleep(1.0)
        logs, logs_json = rt.run_json("plugin", "log", "list", "--plugin", PLUGIN_ID, "--limit", "20")
        entries = (logs_json or {}).get("result", {}).get("logs") or (logs_json or {}).get("result", {}).get("entries") or []
        report["plugin_log_entries"] = entries[:6]
        log_text = json.dumps(entries)
        checks["log_shows_capture"] = '"captured":true' in log_text or "captured\\\":true" in log_text
        checks["log_shows_skip_for_working"] = "not-a-capture-state" in log_text

        # 6. Metadata token reported back onto the pane (display-only).
        got, got_json = rt.run_json("pane", "get", pane_id)
        tokens = ((got_json or {}).get("result", {}).get("pane", {}) or {}).get("tokens", {})
        report["pane_tokens"] = tokens
        checks["memory_token_on_pane"] = "memory" in tokens

        # 7. Explicit recall through a plugin action with workspace context.
        t1 = time.perf_counter()
        rt.run("workspace", "focus", payload["result"]["workspace"]["workspace_id"])
        inv, inv_json = rt.run_json("plugin", "action", "invoke", f"{PLUGIN_ID}.recall")
        report["timings_ms"]["action_invoke_roundtrip"] = (time.perf_counter() - t1) * 1000.0
        checks["recall_action_exit"] = inv.returncode
        report["recall_invoke"] = inv_json or {"stderr": inv.stderr[:400]}
        time.sleep(1.5)
        logs2, logs2_json = rt.run_json("plugin", "log", "list", "--plugin", PLUGIN_ID, "--limit", "20")
        text2 = json.dumps(logs2_json or {})
        checks["recall_log_has_guard_header"] = "HISTORICAL REFERENCE ONLY" in text2
        checks["recall_log_mentions_agent"] = "codex-sim" in text2

        # 8. Direct CLI recall as an orchestrator would call it (absolute paths, plugin state dir).
        import os
        import subprocess
        env = rt.env()
        env.update({"HERDR_PLUGIN_STATE_DIR": str(state_dir), "HERDR_BIN_PATH": str(rt.binary), "HERDR_SESSION": rt.session_name})
        cli = subprocess.run(["node", str(PLUGIN_DIR / "src" / "cli.js"), "recall", "actions.rs", "--project", str(project), "--json"],
                             capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
        checks["direct_cli_recall_exit"] = cli.returncode
        try:
            recall = json.loads(cli.stdout)
            checks["direct_cli_recall_included"] = recall.get("included", 0) >= 1
            report["direct_recall_chars"] = recall.get("chars")
            raw_read = rt.run("pane", "read", pane_id, "--source", "recent-unwrapped", "--lines", "120")
            report["raw_pane_read_chars"] = len(raw_read.stdout)
        except json.JSONDecodeError:
            checks["direct_cli_recall_included"] = False
            report["direct_cli_stdout"] = cli.stdout[:500]

        # 9. CLI round-trip latency with the plugin linked (compare with baseline measurement).
        samples = []
        for _ in range(10):
            s = time.perf_counter()
            rt.run("workspace", "list")
            samples.append((time.perf_counter() - s) * 1000.0)
        report["timings_ms"]["workspace_list_with_plugin_median"] = sorted(samples)[len(samples) // 2]

        # 10. Unlink leaves files alone and removes the registration.
        unl, _ = rt.run_json("plugin", "unlink", PLUGIN_ID)
        checks["plugin_unlink_exit"] = unl.returncode
        return finish(rt, report)
    finally:
        report["server_exit"] = rt.stop_server(process)
        (rt.log_dir / "plugin-integration.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def finish(rt: hi.IsolatedRuntime, report: dict) -> int:
    failed = [k for k, v in report["checks"].items() if v is False or (isinstance(v, int) and not isinstance(v, bool) and k.endswith("_exit") and v != 0)]
    report["failed_checks"] = failed
    print(json.dumps({"session": report["session"], "checks": report["checks"], "timings_ms": report["timings_ms"], "failed": failed}, indent=2, default=str))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
