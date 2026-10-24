"""Simulated dispatch against a disposable isolated Herdr backend.

The plan is built for kind `grok` from an ECC agent definition (data only). In `--simulate` mode the
`agent start` and `agent prompt` steps are replaced by Herdr's documented custom-agent reporting API
(`pane report-agent --source custom:dispatch-sim`), so no real Grok/Claude/Codex process runs. Everything
else (workspace creation, wait/read, memory handoff through the agent-memory plugin CLI) is real Herdr.

Usage: python C:\\Herdr-dev\\prototypes\\herdr-dispatch\\integration\\test_dispatch_backend.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

COMMON = Path(r"C:\Herdr-dev\prototypes\common")
DISPATCH = Path(r"C:\Herdr-dev\prototypes\herdr-dispatch")
MEMORY_CLI = Path(r"C:\Herdr-dev\prototypes\herdr-agent-memory\src\cli.js")
ECC_AGENT = Path(r"C:\Herdr-dev\ecc\agents\code-reviewer.md")
sys.path.insert(0, str(COMMON))
sys.path.insert(0, str(DISPATCH))
import herdr_isolated as hi  # noqa: E402
from herdr_dispatch.executor import HerdrRunner, execute_plan  # noqa: E402
from herdr_dispatch.plan import build_plan  # noqa: E402
from herdr_dispatch.roles import load_role  # noqa: E402


def main() -> int:
    rt = hi.IsolatedRuntime(session_name=hi.unique_session_name("dispatch"))
    rt.prepare()
    rt.write_resolution_record()
    report: dict = {"session": rt.session_name, "root": str(rt.root), "checks": {}}
    checks = report["checks"]
    process = rt.start_server()
    try:
        checks["server_ready"] = rt.wait_for_ping(timeout=40)
        if not checks["server_ready"]:
            return finish(report)
        project = rt.tmp_dir / "dispatch-project"
        (project / ".git").mkdir(parents=True, exist_ok=True)
        role = load_role(ECC_AGENT)
        plan = build_plan(role, "grok", str(project), task="Review the last change and list defects.", memory_cli=str(MEMORY_CLI))
        (rt.log_dir / "dispatch-plan.json").write_text(plan.to_json(), encoding="utf-8")
        (rt.log_dir / "dispatch-plan.md").write_text(plan.to_markdown(), encoding="utf-8")
        checks["plan_has_grok_agent_start"] = plan.steps[1].argv[:5] == ["agent", "start", role.name, "--kind", "grok"]
        checks["plan_no_codex"] = not any("codex" in " ".join(s.argv) for s in plan.steps)

        env = rt.env()
        state_dir = rt.herdr_state_dir("herdr") / "plugins" / "research.agent-memory"
        env.update({"HERDR_PLUGIN_STATE_DIR": str(state_dir), "HERDR_BIN_PATH": str(rt.binary), "HERDR_SESSION": rt.session_name})
        runner = HerdrRunner(str(rt.binary), rt.session_name, env, str(rt.tmp_dir), rt.log_dir / "dispatch-cli.log")
        outcome = execute_plan(plan, runner, simulate=True)
        report["outcome"] = outcome
        checks["all_steps_ok"] = outcome["ok"]
        checks["five_steps_ran"] = len(outcome["steps"]) == 5
        checks["pane_captured"] = "pane_id" in outcome["variables"]
        # Visibility is asserted from the step-2 rename response: Herdr's safety net clears a custom-reported agent
        # a second or two after its pane is back at a shell prompt (docs/add-herdr-support), so a post-run
        # `agent list` is not meaningful for a simulated occupant.
        step2 = outcome["steps"][1] if len(outcome["steps"]) > 1 else {"stdout_tail": ""}
        checks["simulated_agent_visible"] = f'"name":"{role.name}"' in step2["stdout_tail"] and '"agent_status":"idle"' in step2["stdout_tail"]
        report["agent_record"] = step2["stdout_tail"][-600:]
        checks["read_step_has_prompt_echo"] = "role prompt received" in (outcome["steps"][3]["stdout_tail"] if len(outcome["steps"]) > 3 else "")
        memories = list(state_dir.rglob("mem_*.md")) if state_dir.exists() else []
        checks["handoff_written_to_vault"] = any("handoff" in p.read_text(encoding="utf-8") for p in memories)
        report["vault_files"] = [str(p) for p in memories]
        report["step_timings_ms"] = {s["id"]: round(s["elapsed_ms"], 1) for s in outcome["steps"]}
        return finish(report)
    finally:
        report["server_exit"] = rt.stop_server(process)
        (rt.log_dir / "dispatch-integration.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def finish(report: dict) -> int:
    failed = [k for k, v in report["checks"].items() if v is False]
    report["failed_checks"] = failed
    print(json.dumps({"session": report["session"], "checks": report["checks"], "step_timings_ms": report.get("step_timings_ms"), "failed": failed}, indent=2, default=str))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
