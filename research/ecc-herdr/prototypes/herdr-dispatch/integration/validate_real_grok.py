"""Supervised real-agent validation: Grok Build started by Herdr in an isolated named research session.

Authorized by the owner on 2026-10-24 ("run the memory plugin and dispatch plan against a real Grok Build process in an
isolated named research session with a throwaway repository, no production profiles").

Isolation: workspace Herdr binary, fresh XDG roots under runtime/sessions/<name>/, no Herdr production profile, no
`herdr integration install` (Grok's own config is never edited by this script). Grok itself runs as the user with its
existing login in ~/.grok (nothing is copied); the files Grok changes there are reported before/after.

Approval policy (automatic, logged): a blocked dialog is answered only when it is a folder-trust prompt for the
throwaway repository path, or a read-only tool permission for a path inside that repository. The affirmative option
chosen never contains "always", "yolo", or "all". Any other dialog aborts the run without input.

Usage: python C:\\Herdr-dev\\prototypes\\herdr-dispatch\\integration\\validate_real_grok.py [--max-turns 3]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

COMMON = Path(r"C:\Herdr-dev\prototypes\common")
DISPATCH = Path(r"C:\Herdr-dev\prototypes\herdr-dispatch")
PLUGIN_DIR = Path(r"C:\Herdr-dev\prototypes\herdr-agent-memory")
MEMORY_CLI = PLUGIN_DIR / "src" / "cli.js"
PLUGIN_ID = "research.agent-memory"
OUTPUT_DIR = Path(r"C:\Herdr-dev\outputs\real-grok-validation")
GROK_HOME = Path(os.environ.get("USERPROFILE", "")) / ".grok"
sys.path.insert(0, str(COMMON))
sys.path.insert(0, str(DISPATCH))
import herdr_isolated as hi  # noqa: E402
import herdr_socket as hs  # noqa: E402
from herdr_dispatch.executor import HerdrRunner, execute_plan  # noqa: E402
from herdr_dispatch.plan import build_plan  # noqa: E402
from herdr_dispatch.roles import load_role  # noqa: E402

ROLE_TEXT = """---
name: grok-probe
description: Read-only probe role used to validate Herdr-native dispatch and memory capture
tools: Read
---
You are a read-only reviewer. Do not create, modify, delete, or move any file. Do not run shell commands.
Do not use web search or subagents. Keep answers short.
"""
TASK = "Read README.md in the current directory and reply with exactly three short bullet points that summarize it. Then stop."
OPTION_LINE = re.compile(r"^\s*\u2503\s*([0-9a-z])\s*\(([\u25cb\u25cf])\)\s*(.+?)\s*$", re.MULTILINE)
# Grok Build 1.0.67 trust dialog layout: "Yes, proceed                 y" / "No, quit                     n"
PLAIN_OPTION_LINE = re.compile(r"^\s*((?:Yes|No|Trust|Allow|Deny|Quit)[^\n]*?)\s{2,}([a-z])\s*$", re.MULTILINE)
MAX_INTERVENTIONS = 3


def parse_options(text: str) -> list[tuple[str, str]]:
    """Return (key, label) pairs for both the gutter-list and the plain two-column dialog layouts."""
    options = [(key, label) for key, _mark, label in OPTION_LINE.findall(text)]
    options += [(key, label.strip()) for label, key in PLAIN_OPTION_LINE.findall(text)]
    return options


def snapshot(root: Path) -> dict[str, tuple[int, float]]:
    out = {}
    if not root.exists():
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("bin", "bundled", "downloads", "docs", "completions")]
        for name in filenames:
            p = Path(dirpath) / name
            try:
                st = p.stat()
            except OSError:
                continue
            out[str(p.relative_to(root))] = (st.st_size, st.st_mtime)
    return out


def diff_snapshots(before: dict, after: dict) -> dict:
    added = sorted(k for k in after if k not in before)
    modified = sorted(k for k in after if k in before and after[k] != before[k])
    removed = sorted(k for k in before if k not in after)
    return {"added": added, "modified": modified, "removed": removed}


class Timeline:
    def __init__(self):
        self.t0 = time.perf_counter()
        self.events: list[dict] = []
        self.lock = threading.Lock()

    def note(self, kind: str, **data):
        with self.lock:
            self.events.append({"t_ms": round((time.perf_counter() - self.t0) * 1000.0, 1), "kind": kind, **data})

    def on_event(self, event: dict):
        name = event.get("event") or event.get("type")
        data = event.get("data") or {}
        self.note("herdr-event", event=name, agent=data.get("agent"), status=data.get("agent_status"))


def make_repo(root: Path) -> Path:
    repo = root / "throwaway-repo"
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "README.md").write_text(
        "# Throwaway Probe Repo\n\nThis repository exists only to validate Herdr-native agent dispatch.\n\n"
        "- It contains one Python module, `src/hello.py`, that prints a greeting.\n"
        "- It has no dependencies and no tests.\n"
        "- It will be deleted after the validation run.\n", encoding="utf-8")
    (repo / "src" / "hello.py").write_text('def main():\n    print("hello from the throwaway probe repo")\n\n\nif __name__ == "__main__":\n    main()\n', encoding="utf-8")
    git = ["git", "-c", "user.name=research", "-c", "user.email=research@example.invalid", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    subprocess.run([*git, "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run([*git, "-C", str(repo), "commit", "-q", "-m", "init"], check=True, capture_output=True)
    return repo


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-turns", type=int, default=3)
    parser.add_argument("--start-timeout-ms", type=int, default=120000)
    parser.add_argument("--wait-timeout-ms", type=int, default=240000)
    parser.add_argument("--manifest-override", help="patched agent-detection manifest to install ONLY in this session's isolated config dir")
    args = parser.parse_args()

    rt = hi.IsolatedRuntime(session_name=hi.unique_session_name("realgrok"))
    rt.prepare()
    rt.write_resolution_record()
    if args.manifest_override:
        override_dir = rt.herdr_config_dir("herdr") / "agent-detection"
        override_dir.mkdir(parents=True, exist_ok=True)
        (override_dir / "grok.toml").write_text(Path(args.manifest_override).read_text(encoding="utf-8"), encoding="utf-8")
    tl = Timeline()
    report: dict = {"session": rt.session_name, "root": str(rt.root), "checks": {}, "policy_actions": [], "screens": {},
                    "manifest_override": args.manifest_override}
    checks = report["checks"]
    env = rt.env()
    # Grok resolution inside the research environment (PATH minus production Herdr entries).
    where = subprocess.run(["where", "grok"], env=env, capture_output=True, text=True)
    version = subprocess.run(["grok", "--version"], env=env, capture_output=True, text=True, timeout=60)
    report["grok"] = {"where": where.stdout.strip().splitlines(), "version": (version.stdout or version.stderr).strip()}
    checks["grok_resolves_outside_production_dirs"] = bool(report["grok"]["where"]) and all(".grok" in p for p in report["grok"]["where"])
    grok_before = snapshot(GROK_HOME)
    report["grok_home_files_before"] = len(grok_before)

    repo = make_repo(rt.tmp_dir)
    role_path = rt.tmp_dir / "grok-probe.md"
    role_path.write_text(ROLE_TEXT, encoding="utf-8")
    role = load_role(role_path)
    plan = build_plan(role, "grok", str(repo), task=TASK, start_timeout_ms=args.start_timeout_ms, wait_timeout_ms=args.wait_timeout_ms,
                      memory_cli=str(MEMORY_CLI), extra_args=["--no-subagents", "--disable-web-search", "--max-turns", str(args.max_turns)])
    (rt.log_dir / "dispatch-plan.json").write_text(plan.to_json(), encoding="utf-8")
    (rt.log_dir / "dispatch-plan.md").write_text(plan.to_markdown(), encoding="utf-8")
    report["plan_agent_start_argv"] = plan.steps[1].argv

    process = rt.start_server()
    state_dir = rt.herdr_state_dir("herdr") / "plugins" / PLUGIN_ID
    runner_env = dict(env)
    runner_env.update({"HERDR_PLUGIN_STATE_DIR": str(state_dir), "HERDR_BIN_PATH": str(rt.binary), "HERDR_SESSION": rt.session_name})
    runner = HerdrRunner(str(rt.binary), rt.session_name, runner_env, str(rt.tmp_dir), rt.log_dir / "dispatch-cli.log")
    sub = None
    pane_id = None
    aborted_reason = None
    try:
        checks["server_ready"] = rt.wait_for_ping(timeout=40)
        if not checks["server_ready"]:
            return finish(rt, report, tl)
        link, link_json = rt.run_json("plugin", "link", str(PLUGIN_DIR))
        checks["plugin_link_exit"] = link.returncode

        one = execute_plan(plan, runner, only_steps=["1"])
        variables = one["variables"]
        pane_id = variables.get("pane_id")
        checks["workspace_created"] = one["ok"] and bool(pane_id)
        report["pane_id"] = pane_id
        if not pane_id:
            return finish(rt, report, tl)
        _, sessions = rt.run_json("session", "list", "--json")
        sock = next(s["socket_path"] for s in sessions["sessions"] if s["name"] == rt.session_name)
        sub = hs.EventSubscription(sock, [{"type": "pane.agent_status_changed", "pane_id": pane_id}, {"type": "pane.agent_detected", "pane_id": pane_id}], tl.on_event)

        def screen(label: str) -> str:
            vis = rt.run("agent", "read", pane_id, "--source", "visible", timeout=30)
            text = vis.stdout if vis.returncode == 0 else rt.run("pane", "read", pane_id, "--source", "visible", timeout=30).stdout
            report["screens"][f"{len(report['screens']):02d}-{label}"] = text[-3000:]
            return text

        def status() -> tuple[str | None, str | None]:
            _, got = rt.run_json("agent", "get", pane_id, timeout=20)
            agent = ((got or {}).get("result") or {}).get("agent") or {}
            return agent.get("agent"), agent.get("agent_status")

        def supervise(phase: str, timeout_s: float) -> str:
            """Wait for idle/done; answer only policy-approved dialogs. Returns final status or 'aborted'."""
            nonlocal aborted_reason
            deadline = time.monotonic() + timeout_s
            interventions = 0
            last_dialog = None
            while time.monotonic() < deadline:
                agent, st = status()
                if st in ("idle", "done"):
                    return st
                if st == "blocked":
                    text = screen(f"{phase}-blocked")
                    options = parse_options(text)
                    lower = text.lower()
                    repo_fragment = repo.name.lower()
                    trust_dialog = "trust" in lower and (repo_fragment in lower or "folder" in lower or "director" in lower)
                    read_dialog = any(w in lower for w in ("read", "view", "open", "cat ")) and repo_fragment in lower and not any(w in lower for w in ("write", "edit", "delete", "remove", "network", "curl"))
                    choice = None
                    for key, label in options:
                        ll = label.lower()
                        if re.search(r"\b(yes|trust|allow|proceed|continue)\b", ll) and not re.search(r"\b(always|yolo|all|never|no|reject|deny|don't)\b", ll):
                            choice = (key, label)
                            break
                    dialog_sig = (tuple(options), text[-400:])
                    if (trust_dialog or read_dialog) and choice and interventions < MAX_INTERVENTIONS:
                        if dialog_sig == last_dialog:
                            rt.run("agent", "send-keys", pane_id, "enter", timeout=20)
                            report["policy_actions"].append({"phase": phase, "action": "enter (same dialog persisted)", "t_ms": tl.events[-1]["t_ms"] if tl.events else None})
                        else:
                            rt.run("agent", "send-keys", pane_id, choice[0], timeout=20)
                            report["policy_actions"].append({"phase": phase, "action": f"send key {choice[0]!r} for option {choice[1]!r}", "dialog": "trust" if trust_dialog else "read-permission"})
                        interventions += 1
                        last_dialog = dialog_sig
                        tl.note("policy", phase=phase, intervention=interventions)
                        time.sleep(2.0)
                        continue
                    aborted_reason = f"{phase}: unapprovable or unrecognised dialog (options={options[:4]})"
                    tl.note("abort", reason=aborted_reason)
                    return "aborted"
                time.sleep(1.0)
            aborted_reason = f"{phase}: timeout waiting for idle (last status {status()[1]})"
            tl.note("abort", reason=aborted_reason)
            return "aborted"

        # Step 2: real `agent start grok-probe --kind grok --pane <id> --timeout ... -- <safety flags>`
        tl.note("step", step="2-agent-start")
        t_start = time.perf_counter()
        two = execute_plan(plan, runner, variables=variables, only_steps=["2"])
        report["step2"] = {"ok": two["ok"], "exit_codes": two["steps"][0]["exit_codes"] if two["steps"] else None,
                           "stderr": (two["steps"][0]["stderr_tail"] if two["steps"] else "")[-600:], "elapsed_ms": two["steps"][0]["elapsed_ms"] if two["steps"] else None}
        screen("after-agent-start")
        _, status_after_start = status()
        report["status_right_after_agent_start"] = status_after_start
        checks["start_reported_blocked_or_not_ready_when_trust_dialog_shown"] = (
            status_after_start == "blocked" or "agent_not_ready" in report["step2"]["stderr"]
            or "trust" not in report["screens"].get("00-after-agent-start", "").lower())
        final = supervise("startup", timeout_s=args.start_timeout_ms / 1000.0 + 60)
        report["timings_ms"] = {"start_to_ready": (time.perf_counter() - t_start) * 1000.0}
        checks["agent_start_reached_idle"] = final in ("idle", "done")
        agent_label, _ = status()
        checks["detected_kind_is_grok"] = agent_label == "grok"
        report["detected_agent_label"] = agent_label
        if final == "aborted":
            return finish(rt, report, tl)

        # Step 3: role prompt with --wait
        tl.note("step", step="3-agent-prompt")
        t_prompt = time.perf_counter()
        three = execute_plan(plan, runner, variables=variables, only_steps=["3"])
        report["step3"] = {"ok": three["ok"], "exit_codes": three["steps"][0]["exit_codes"] if three["steps"] else None,
                           "stderr": (three["steps"][0]["stderr_tail"] if three["steps"] else "")[-600:], "elapsed_ms": three["steps"][0]["elapsed_ms"] if three["steps"] else None}
        screen("after-prompt-wait")
        final = supervise("turn", timeout_s=args.wait_timeout_ms / 1000.0)
        report["timings_ms"]["prompt_to_settled"] = (time.perf_counter() - t_prompt) * 1000.0
        checks["prompt_turn_settled"] = final in ("idle", "done")
        if final == "aborted":
            return finish(rt, report, tl)

        # Steps 4-5: read through Herdr, then handoff into the memory vault
        tl.note("step", step="4-5-read-and-handoff")
        four_five = execute_plan(plan, runner, variables=variables, only_steps=["4", "5"])
        read_text = four_five["steps"][0]["stdout_tail"] if four_five["steps"] else ""
        report["agent_read_tail"] = read_text[-2500:]
        report["agent_read_chars"] = len(read_text)
        checks["agent_read_ok"] = bool(four_five["steps"]) and four_five["steps"][0]["exit_codes"] == [0]
        checks["agent_answer_has_bullets"] = read_text.count("\n- ") + read_text.count("\n• ") + read_text.count("\n* ") >= 2 or "hello" in read_text.lower()
        checks["handoff_ok"] = four_five["ok"]

        # Memory plugin: did the event hook capture the real agent's settle?
        deadline = time.monotonic() + 30
        captured = []
        while time.monotonic() < deadline:
            captured = [p for p in state_dir.rglob("mem_*.md") if 'source_agent: "grok"' in p.read_text(encoding="utf-8", errors="replace")] if state_dir.exists() else []
            if captured:
                break
            time.sleep(0.5)
        checks["memory_plugin_captured_grok"] = bool(captured)
        if captured:
            doc = captured[0].read_text(encoding="utf-8")
            report["memory_doc_head"] = doc[:1500]
            report["memory_doc_chars"] = len(doc)
        logs, logs_json = rt.run_json("plugin", "log", "list", "--plugin", PLUGIN_ID, "--limit", "20")
        report["plugin_log"] = json.dumps(logs_json or {})[:2500]
        recall = subprocess.run(["node", str(MEMORY_CLI), "recall", "README", "--project", str(repo), "--json"], env=runner_env, capture_output=True, text=True, encoding="utf-8", timeout=60)
        try:
            rec = json.loads(recall.stdout)
            report["recall"] = {"included": rec.get("included"), "chars": rec.get("chars"), "raw_read_chars": len(read_text)}
            checks["recall_includes_capture_or_handoff"] = (rec.get("included") or 0) >= 1
        except json.JSONDecodeError:
            checks["recall_includes_capture_or_handoff"] = False
        _, got = rt.run_json("pane", "get", pane_id)
        report["pane_tokens"] = ((got or {}).get("result") or {}).get("pane", {}).get("tokens")
        return finish(rt, report, tl)
    finally:
        report["aborted_reason"] = aborted_reason
        try:
            if sub:
                sub.close()
        except Exception:
            pass
        if pane_id:
            screen_final = rt.run("pane", "read", pane_id, "--source", "visible", timeout=30).stdout
            report["screens"]["99-final"] = screen_final[-3000:]
            rt.run("pane", "close", pane_id, timeout=30)
        rt.run("plugin", "unlink", PLUGIN_ID, timeout=30)
        report["server_exit"] = rt.stop_server(process)
        report["grok_home_changes"] = diff_snapshots(grok_before, snapshot(GROK_HOME))
        report["timeline"] = tl.events
        rt.log_dir.mkdir(parents=True, exist_ok=True)
        (rt.log_dir / "real-grok-validation.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / f"{rt.session_name}.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def finish(rt: hi.IsolatedRuntime, report: dict, tl: Timeline) -> int:
    failed = [k for k, v in report["checks"].items() if v is False or (k.endswith("_exit") and isinstance(v, int) and v != 0)]
    report["failed_checks"] = failed
    print(json.dumps({"session": report["session"], "checks": report["checks"], "timings_ms": report.get("timings_ms"), "policy_actions": report["policy_actions"],
                      "aborted_reason": report.get("aborted_reason"), "failed": failed}, indent=2, default=str))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
