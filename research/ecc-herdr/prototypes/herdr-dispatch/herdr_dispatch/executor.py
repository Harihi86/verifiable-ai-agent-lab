"""Execute a dispatch plan against a Herdr server with an absolute binary and explicit session."""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .plan import DispatchPlan, Step


@dataclass
class StepResult:
    id: str
    argv: list[list[str]]
    exit_codes: list[int]
    captured: dict[str, str] = field(default_factory=dict)
    stdout_tail: str = ""
    stderr_tail: str = ""
    elapsed_ms: float = 0.0
    simulated: bool = False

    def to_dict(self) -> dict:
        return self.__dict__


def _json_path(payload, dotted: str):
    current = payload
    for part in dotted.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


class HerdrRunner:
    """Runs Herdr CLI commands with a fixed absolute binary, session, environment, and cwd."""

    def __init__(self, binary: str, session: str | None, env: dict, cwd: str, log_path: Path | None = None):
        self.binary = str(Path(binary))
        if not Path(self.binary).is_absolute():
            raise ValueError("Herdr binary must be an absolute path")
        self.session = session
        self.env = env
        self.cwd = cwd
        self.log_path = log_path

    def argv(self, args: list[str]) -> list[str]:
        prefix = [self.binary] + (["--session", self.session] if self.session else [])
        return prefix + list(args)

    def run(self, args: list[str], timeout: float = 120.0):
        argv = self.argv(args)
        completed = subprocess.run(argv, env=self.env, cwd=self.cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"$ {' '.join(argv)}\nexit={completed.returncode}\n{completed.stdout[-2000:]}\n{completed.stderr[-1000:]}\n\n")
        return completed


TOKEN = re.compile(r"\{(pane_id|workspace_id|agent_status|seq)\}")


def _render(args: list[str], variables: dict[str, str]) -> list[str]:
    """Substitute only known plan tokens; leave every other brace (e.g. JSON in a role prompt) untouched."""
    return [TOKEN.sub(lambda m: variables.get(m.group(1), m.group(0)), a) for a in args]


def execute_plan(plan: DispatchPlan, runner: HerdrRunner, *, simulate: bool = False, dry_run: bool = False,
                 variables: dict[str, str] | None = None, only_steps: list[str] | None = None) -> dict:
    """Run the plan (or a subset of step ids, for supervised real-agent runs). Returns a JSON-serialisable record."""
    variables = dict(variables or {})
    variables.setdefault("seq", str(int(time.time())))
    results: list[StepResult] = []
    ok = True
    for step in plan.steps:
        if only_steps is not None and step.id not in only_steps:
            continue
        started = time.perf_counter()
        commands: list[list[str]]
        simulated = False
        if simulate and step.simulation_argv:
            commands = [list(c) for c in step.simulation_argv]
            simulated = True
        else:
            commands = [list(step.argv)]
        result = StepResult(id=step.id, argv=[], exit_codes=[], simulated=simulated)
        for command in commands:
            variables["seq"] = str(int(variables["seq"]) + 1)
            rendered = _render(command, variables)
            external = rendered and rendered[0] == "__external__"
            if dry_run:
                result.argv.append(rendered if external else runner.argv(rendered))
                result.exit_codes.append(0)
                continue
            if external:
                completed = subprocess.run(rendered[1:], env=runner.env, cwd=runner.cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                                           input=result.stdout_tail or variables.get("last_read", ""))
                result.argv.append(rendered[1:])
            else:
                # A Herdr command that carries its own --timeout (ms) may legitimately run that long; give it a margin.
                cli_timeout = 120.0
                if "--timeout" in rendered:
                    try:
                        cli_timeout = int(rendered[rendered.index("--timeout") + 1]) / 1000.0 + 30.0
                    except (ValueError, IndexError):
                        pass
                completed = runner.run(rendered, timeout=cli_timeout)
                result.argv.append(runner.argv(rendered))
            result.exit_codes.append(completed.returncode)
            result.stdout_tail = completed.stdout[-4000:]
            result.stderr_tail = completed.stderr[-1500:]
            if completed.returncode != 0:
                ok = False
                break
            text = completed.stdout.strip()
            if text.startswith("{"):
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = None
                if payload:
                    for name, dotted in step.capture.items():
                        value = _json_path(payload, dotted)
                        if value is not None:
                            variables[name] = str(value)
                            result.captured[name] = str(value)
            if step.id == "4":
                variables["last_read"] = completed.stdout
        result.elapsed_ms = (time.perf_counter() - started) * 1000.0
        results.append(result)
        if not ok:
            break
    return {"ok": ok, "simulate": simulate, "dry_run": dry_run, "variables": {k: v for k, v in variables.items() if k != "last_read"},
            "steps": [r.to_dict() for r in results]}
