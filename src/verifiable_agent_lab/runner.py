"""Durable single-host orchestration; this module is not a security sandbox."""

import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .adapters import StaticReviewer, stage, tree_digest
from .models import Outcome, Task, decide


def write_json(path: Path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _kill(process):
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        process.kill()


def execute(check, workspace: Path, evidence: Path, timeout: float, output_limit: int):
    command = [
        v.replace("{python}", sys.executable).replace("{workspace}", str(workspace))
        for v in check.command
    ]
    result = {
        "name": check.name,
        "mandatory": check.mandatory,
        "command": command,
        "outcome": Outcome.NOT_RUN,
        "returncode": None,
        "log": evidence.name,
    }
    start = time.monotonic()
    # Inherited credentials are excluded. This does not restrict filesystem/network access.
    env = {
        k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP") if k in os.environ
    }
    env.update({"VAAL_WORKSPACE": str(workspace), "PYTHONDONTWRITEBYTECODE": "1"})
    try:
        process = subprocess.Popen(
            command,
            cwd=workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=os.name == "posix",
        )
    except OSError as exc:
        result.update(outcome=Outcome.BLOCKED, message=f"Cannot start check: {type(exc).__name__}")
        evidence.write_text(result["message"] + "\n", encoding="utf-8")
        return result
    overflow = threading.Event()
    collection_errors = []

    def collect():
        total = 0
        try:
            with evidence.open("wb") as log:
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break
                    available = max(0, output_limit - total)
                    log.write(chunk[:available])
                    total += len(chunk)
                    if total > output_limit:
                        overflow.set()
                        _kill(process)
                        break
        except OSError as exc:
            collection_errors.append(type(exc).__name__)
            _kill(process)

    reader = threading.Thread(target=collect, daemon=True)
    reader.start()
    try:
        process.wait(timeout=timeout)
        result["outcome"] = Outcome.PASS if process.returncode == 0 else Outcome.FAIL
    except subprocess.TimeoutExpired:
        _kill(process)
        process.wait()
        result.update(outcome=Outcome.INCONCLUSIVE, message="Execution deadline exceeded")
    reader.join(timeout=1)
    if reader.is_alive():
        _kill(process)
        reader.join(timeout=1)
        result.update(outcome=Outcome.INCONCLUSIVE, message="Output pipe remained open")
    if overflow.is_set():
        result.update(outcome=Outcome.INCONCLUSIVE, message="Output budget exceeded; log truncated")
    if collection_errors:
        result.update(outcome=Outcome.INCONCLUSIVE, message="Cannot preserve raw check output")
    if not reader.is_alive():
        process.stdout.close()
    result.update(returncode=process.returncode, elapsed_seconds=round(time.monotonic() - start, 6))
    return result


class Lab:
    def __init__(self, output: Path):
        self.output = output.resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.db_path = self.output / "state.sqlite"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, spec_hash TEXT)")
            db.execute("""CREATE TABLE IF NOT EXISTS attempts(
                       id TEXT PRIMARY KEY, task TEXT, state TEXT, outcome TEXT, report TEXT)""")

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def recover(self, task_id):
        """Explicitly mark interrupted attempts uncertain. Never re-execute their commands."""
        with self.connect() as db:
            ids = [
                row[0]
                for row in db.execute(
                    "SELECT id FROM attempts WHERE task=? AND state='RUNNING'", (task_id,)
                )
            ]
            for attempt_id in ids:
                path = self.output / attempt_id / "report.json"
                report = {
                    "task_id": task_id,
                    "attempt_id": attempt_id,
                    "outcome": Outcome.INCONCLUSIVE,
                    "reason": "Explicit recovery of interrupted run; completion unknown",
                }
                write_json(path, report)
                db.execute(
                    "UPDATE attempts SET state='INTERRUPTED', outcome=?, report=? WHERE id=?",
                    (Outcome.INCONCLUSIVE, str(path), attempt_id),
                )
        return ids

    def run(self, task: Task, adapter, reviewer=None):
        spec = json.dumps(task.to_dict(), sort_keys=True)
        spec_hash = hashlib.sha256(spec.encode()).hexdigest()
        attempt = uuid.uuid4().hex
        directory = self.output / attempt
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT spec_hash FROM tasks WHERE id=?", (task.id,)).fetchone()
            if existing and existing[0] != spec_hash:
                raise ValueError("Task specification changed; choose a new task id")
            db.execute("INSERT OR IGNORE INTO tasks VALUES(?,?)", (task.id, spec_hash))
            rows = db.execute("SELECT state FROM attempts WHERE task=?", (task.id,)).fetchall()
            if any(row[0] == "RUNNING" for row in rows):
                raise ValueError(
                    "Run already active or interrupted; inspect it before explicit recovery"
                )
            if len(rows) >= task.max_attempts:
                raise ValueError("Attempt budget exhausted")
            directory.mkdir()
            db.execute(
                "INSERT INTO attempts VALUES(?,?,?,?,?)",
                (attempt, task.id, "RUNNING", Outcome.NOT_RUN, None),
            )
        report = {
            "task_id": task.id,
            "attempt_id": attempt,
            "spec_sha256": spec_hash,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "adapter": adapter.identity,
            "checks": [],
            "outcome": Outcome.NOT_RUN,
            "python": sys.version.split()[0],
            "platform": sys.platform,
        }
        write_json(directory / "task.json", task.to_dict())
        workspace = directory / "source"
        workspace.mkdir()
        try:
            with self.connect() as db:
                missing = [
                    d
                    for d in task.dependencies
                    if not db.execute(
                        "SELECT 1 FROM attempts WHERE task=? AND state='FINISHED' AND outcome='PASS'",
                        (d,),
                    ).fetchone()
                ]
            if missing:
                report.update(
                    outcome=Outcome.BLOCKED,
                    reason="Dependencies have no PASS: " + ", ".join(missing),
                )
            else:
                stage(adapter, workspace)
                before = tree_digest(workspace)
                owner_files = {
                    name: Path(name).read_bytes()
                    for check in task.checks
                    for name in check.input_files
                }
                owner_hashes = {
                    name: hashlib.sha256(content).hexdigest()
                    for name, content in owner_files.items()
                }
                trusted_inputs = directory / "owner-inputs"
                trusted_inputs.mkdir()
                for i, content in enumerate(owner_files.values()):
                    (trusted_inputs / f"input-{i}").write_bytes(content)
                review = (reviewer or StaticReviewer()).review(workspace)
                write_json(directory / "review.json", review)
                for i, check in enumerate(task.checks):
                    report["checks"].append(
                        execute(
                            check,
                            workspace,
                            directory / f"check-{i}.log",
                            task.timeout_seconds,
                            task.max_output_bytes,
                        )
                    )
                after = tree_digest(workspace)
                integrity = before == after == review.get("source_sha256") and all(
                    Path(name).read_bytes() == content for name, content in owner_files.items()
                )
                outcome, reason = decide(
                    report["checks"], review, integrity, task.requires_human_acceptance
                )
                report.update(
                    outcome=outcome,
                    reason=reason,
                    source_sha256=before,
                    source_sha256_after=after,
                    source_integrity=integrity,
                    owner_input_sha256=owner_hashes,
                    review="review.json",
                )
        except Exception as exc:
            report.update(
                outcome=Outcome.INCONCLUSIVE,
                reason=f"Orchestration error: {type(exc).__name__}: {exc}",
            )
        write_json(directory / "report.json", report)
        (directory / "report.md").write_text(
            f"# Evaluation: {task.id}\n\nOutcome: **{report['outcome']}**\n\n{report['reason']}\n\n"
            + "\n".join(
                f"- {c['name']}: {c['outcome']} (raw log: `{c['log']}`)" for c in report["checks"]
            )
            + "\n\nA PASS covers configured technical checks only. Product acceptance remains with the owner.\n",
            encoding="utf-8",
        )

        with self.connect() as db:
            db.execute(
                "UPDATE attempts SET state='FINISHED', outcome=?, report=? WHERE id=?",
                (report["outcome"], str(directory / "report.json"), attempt),
            )
        return report
