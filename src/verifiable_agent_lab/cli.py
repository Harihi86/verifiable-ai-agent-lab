import argparse
import hashlib
import json
from pathlib import Path

from .adapters import DirectoryAdapter, FixtureAdapter
from .models import Check, Task
from .runner import Lab, write_json


def demo(output):
    acceptance = Path(__file__).with_name("acceptance_mean.py").resolve()
    # Pin the externally supplied oracle in the immutable owner task specification.
    oracle_hash = hashlib.sha256(acceptance.read_bytes()).hexdigest()
    task = Task(
        "mean-empty-sequence",
        "Arithmetic mean; reject an empty sequence with ValueError. "
        + "Owner acceptance SHA-256: "
        + oracle_hash,
        (
            Check(
                "owner-acceptance",
                ("{python}", "-I", str(acceptance)),
                input_files=(str(acceptance),),
            ),
        ),
        max_attempts=2,
    )
    lab = Lab(output)
    buggy = "def mean(values):\n    return sum(values) / len(values) if values else 0\n"
    fixed = "def mean(values):\n    if not values:\n        raise ValueError('empty sequence')\n    return sum(values) / len(values)\n"
    reports = [
        lab.run(task, FixtureAdapter({"mini_stats.py": source})) for source in (buggy, fixed)
    ]
    summary = {
        "kind": "deterministic local fixtures; no live AI execution",
        "outcomes": [r["outcome"] for r in reports],
        "attempts": [r["attempt_id"] for r in reports],
        "acceptance_sha256": oracle_hash,
    }
    write_json(Path(output) / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate trusted local submissions with explicit evidence"
    )
    sub = parser.add_subparsers(dest="operation", required=True)
    demonstration = sub.add_parser("demo")
    demonstration.add_argument("--output", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--task", type=Path, required=True)
    run.add_argument("--candidate", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument(
        "--execute-trusted-code",
        action="store_true",
        required=True,
        help="Acknowledge execution on this host; this is not a sandbox",
    )
    recover = sub.add_parser("recover")
    recover.add_argument("task_id")
    recover.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "demo":
        result = demo(args.output)
        code = 0 if result["outcomes"] == ["FAIL", "PASS"] else 1
    elif args.operation == "recover":
        result = {"recovered": Lab(args.output).recover(args.task_id)}
        code = 0
    else:
        task = Task.from_dict(json.loads(args.task.read_text(encoding="utf-8")))
        result = Lab(args.output).run(task, DirectoryAdapter(args.candidate))
        code = 0 if result["outcome"] == "PASS" else 1
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
