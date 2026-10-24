"""Live API probe against a disposable isolated Herdr backend.

Verifies, without any real coding agent:
  1. raw named-pipe request/response (ping)
  2. events.subscribe delivers workspace/pane lifecycle and agent-status events
  3. an external process can report custom agent state (pane.report_agent) and metadata tokens
     (pane.report_metadata) and the state shows up in agent list / events

Usage: python C:\\Herdr-dev\\prototypes\\common\\live_api_probe.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import herdr_isolated as hi  # noqa: E402
import herdr_socket as hs  # noqa: E402


def main() -> int:
    rt = hi.IsolatedRuntime(session_name=hi.unique_session_name("probe"))
    rt.prepare()
    rt.write_resolution_record()
    report: dict = {"session": rt.session_name, "root": str(rt.root), "checks": {}}
    process = rt.start_server()
    try:
        ready = rt.wait_for_ping(timeout=40)
        report["checks"]["server_ready"] = ready
        if not ready:
            return finish(rt, report, 1)

        _, sessions = rt.run_json("session", "list", "--json")
        socket_path = next(s["socket_path"] for s in sessions["sessions"] if s["name"] == rt.session_name)
        report["socket_path"] = socket_path
        report["pipe_name"] = hs.pipe_name_for(socket_path)

        pong = hs.request(socket_path, "ping")
        report["checks"]["ping"] = pong
        report["server_version"] = pong.get("result", {}).get("version")
        report["server_protocol"] = pong.get("result", {}).get("protocol")

        seen: list[dict] = []
        # Phase 1: workspace lifecycle (no pane_id needed).
        ws_sub = hs.EventSubscription(socket_path, [{"type": "workspace.created"}], seen.append)
        report["checks"]["workspace_subscription_ack"] = ws_sub.ack

        workdir = rt.tmp_dir / "probe-project"
        workdir.mkdir(exist_ok=True)
        created, payload = rt.run_json("workspace", "create", "--cwd", str(workdir), "--label", "probe", "--no-focus")
        report["checks"]["workspace_create_exit"] = created.returncode
        pane_id = payload["result"]["root_pane"]["pane_id"]
        workspace_id = payload["result"]["workspace"]["workspace_id"]
        report["pane_id"], report["workspace_id"] = pane_id, workspace_id

        ev_ws = ws_sub.wait_for(lambda e: "workspace.created" in json.dumps(e), 10)
        report["checks"]["event_workspace_created"] = ev_ws is not None
        report["sample_event_workspace_created"] = ev_ws

        # Phase 2: pane-scoped subscriptions require the pane_id (server rejects them otherwise).
        sub = hs.EventSubscription(
            socket_path,
            [
                {"type": "pane.agent_status_changed", "pane_id": pane_id},
                {"type": "pane.agent_detected", "pane_id": pane_id},
                {"type": "pane.updated", "pane_id": pane_id},
            ],
            seen.append,
        )
        report["checks"]["pane_subscription_ack"] = sub.ack

        # Simulated custom agent: Herdr's documented third-party reporting API.
        seq = int(time.time())
        r1 = rt.run("pane", "report-agent", pane_id, "--source", "custom:research", "--agent", "research-bot",
                    "--state", "working", "--seq", str(seq))
        r2 = rt.run("pane", "report-agent", pane_id, "--source", "custom:research", "--agent", "research-bot",
                    "--state", "idle", "--seq", str(seq + 1))
        report["checks"]["report_agent_working_exit"] = r1.returncode
        report["checks"]["report_agent_idle_exit"] = r2.returncode
        report["report_agent_stderr"] = (r1.stderr + r2.stderr)[:500]

        ev_status = sub.wait_for(lambda e: "pane.agent_status_changed" in json.dumps(e), 10)
        report["checks"]["event_agent_status_changed"] = ev_status is not None
        report["sample_event_agent_status_changed"] = ev_status

        _, agents = rt.run_json("agent", "list")
        report["agent_list"] = agents
        agent_entries = (agents or {}).get("result", {}).get("agents", [])
        report["checks"]["agent_list_has_research_bot"] = any(
            a.get("agent") == "research-bot" or a.get("name") == "research-bot" or "research-bot" in json.dumps(a)
            for a in agent_entries
        )

        meta = hs.request(socket_path, "pane.report_metadata", {
            "pane_id": pane_id,
            "source": "custom:research",
            "tokens": {"memory": "3 notes", "ecc": "probe"},
            "ttl_ms": 60000,
        })
        report["checks"]["report_metadata"] = meta
        got = hs.request(socket_path, "pane.get", {"pane_id": pane_id})
        report["pane_get_after_metadata"] = got
        report["checks"]["tokens_visible"] = "3 notes" in json.dumps(got)

        rel = rt.run("pane", "release-agent", pane_id, "--source", "custom:research", "--agent", "research-bot",
                     "--seq", str(seq + 2))
        report["checks"]["release_agent_exit"] = rel.returncode
        time.sleep(0.5)
        report["events_seen_types"] = sorted({str(e.get("event") or e.get("type") or "?") for e in seen})
        report["events_seen_count"] = len(seen)
        report["events_raw_first3"] = seen[:3]
        sub.close()
        ws_sub.close()
        return finish(rt, report, 0)
    finally:
        code = rt.stop_server(process)
        report["server_exit"] = code
        (rt.log_dir / "live-api-probe.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def finish(rt: hi.IsolatedRuntime, report: dict, code: int) -> int:
    print(json.dumps({"session": report["session"], "checks": report["checks"], "events_seen": report.get("events_seen_count"),
                      "event_types": report.get("events_seen_types")}, indent=2, default=str))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
