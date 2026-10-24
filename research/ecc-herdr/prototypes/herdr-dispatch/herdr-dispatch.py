#!/usr/bin/env python
"""CLI for herdr-dispatch (works under `python -I`).

  plan  --role <agent.md> --kind <kind> --cwd <dir> [--task TEXT] [--worktree-branch B] [--native-flags] [--memory-cli PATH] [--json OUT] [--md OUT]
  run   --plan plan.json --binary <abs herdr.exe> [--session NAME] [--cwd DIR] [--simulate] [--dry-run] [--json OUT]

`run` never uses a bare `herdr`; it requires an absolute binary. Use the research isolation harness to build
the environment (see prototypes/common/herdr_isolated.py). `--simulate` replaces the agent start/prompt steps
with Herdr's documented custom-agent reporting API so the plan can be exercised without a real coding agent.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from herdr_dispatch.executor import HerdrRunner, execute_plan  # noqa: E402
from herdr_dispatch.plan import DispatchPlan, Step, build_plan  # noqa: E402
from herdr_dispatch.roles import load_role  # noqa: E402


def plan_from_json(data: dict) -> DispatchPlan:
    steps = [Step(id=s["id"], description=s["description"], argv=s["argv"], capture=s.get("capture", {}), authority=s.get("authority", "herdr"), simulation_argv=s.get("simulation_argv")) for s in data["steps"]]
    return DispatchPlan(role=data["role"], kind=data["kind"], agent_name=data["agent_name"], cwd=data["cwd"], steps=steps, prompt=data["prompt"], warnings=data.get("warnings", []), notes=data.get("notes", []))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="herdr-dispatch")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--role", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--cwd", required=True)
    p.add_argument("--task")
    p.add_argument("--label")
    p.add_argument("--worktree-branch")
    p.add_argument("--native-flags", action="store_true")
    p.add_argument("--memory-cli")
    p.add_argument("--wait-timeout-ms", type=int, default=600000)
    p.add_argument("--json", dest="json_out")
    p.add_argument("--md", dest="md_out")
    r = sub.add_parser("run")
    r.add_argument("--plan", required=True)
    r.add_argument("--binary", required=True)
    r.add_argument("--session")
    r.add_argument("--cwd")
    r.add_argument("--simulate", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--json", dest="json_out")
    r.add_argument("--log")
    args = parser.parse_args(argv)

    if args.command == "plan":
        role = load_role(args.role)
        plan = build_plan(role, args.kind, args.cwd, task=args.task, label=args.label, worktree_branch=args.worktree_branch,
                          wait_timeout_ms=args.wait_timeout_ms, native_flags=args.native_flags, memory_cli=args.memory_cli)
        if args.json_out:
            Path(args.json_out).write_text(plan.to_json(), encoding="utf-8")
        if args.md_out:
            Path(args.md_out).write_text(plan.to_markdown(), encoding="utf-8")
        print(plan.to_markdown() if not args.json_out else json.dumps({"written": args.json_out, "steps": len(plan.steps), "warnings": plan.warnings}))
        return 0

    plan = plan_from_json(json.loads(Path(args.plan).read_text(encoding="utf-8")))
    runner = HerdrRunner(args.binary, args.session, dict(os.environ), args.cwd or plan.cwd, Path(args.log) if args.log else None)
    outcome = execute_plan(plan, runner, simulate=args.simulate, dry_run=args.dry_run)
    text = json.dumps(outcome, indent=2)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")
    print(text)
    return 0 if outcome["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
