"""CLI: python -m asset_gate scan <path> [--json out.json] [--md out.md] [--include GLOB ...] [--exclude GLOB ...]
     python -m asset_gate coexist <claude-settings.json> [--json out.json]
Exit codes: 0 allow, 1 review, 2 deny, 3 usage/error."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import rules, scanner, structural

EXIT = {"allow": 0, "review": 1, "deny": 2}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="asset_gate")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="scan a directory or file of agent assets")
    scan.add_argument("path")
    scan.add_argument("--json", dest="json_out")
    scan.add_argument("--md", dest="md_out")
    scan.add_argument("--include", action="append", default=None)
    scan.add_argument("--exclude", action="append", default=None)
    scan.add_argument("--max-findings", type=int, default=None)
    scan.add_argument("--strict", action="store_true", help="do not cap findings inside test/fixture paths")
    scan.add_argument("--quiet", action="store_true")
    co = sub.add_parser("coexist", help="check a Claude settings.json for Herdr hook presence and strictness")
    co.add_argument("settings")
    co.add_argument("--json", dest="json_out")
    args = parser.parse_args(argv)

    if args.command == "scan":
        target = Path(args.path)
        if not target.exists():
            print(json.dumps({"error": f"path not found: {target}"}))
            return 3
        result = scanner.scan_path(target, include=args.include, exclude=args.exclude, strict=args.strict)
        scanner.write_reports(result, Path(args.json_out) if args.json_out else None, Path(args.md_out) if args.md_out else None, args.max_findings)
        if not args.quiet:
            summary = result.to_dict(0)
            summary.pop("findings", None)
            print(json.dumps(summary, indent=2))
        return EXIT[result.decision]

    if args.command == "coexist":
        path = Path(args.settings)
        if not path.exists():
            print(json.dumps({"error": f"path not found: {path}"}))
            return 3
        text = path.read_text(encoding="utf-8", errors="replace")
        findings = structural.herdr_coexistence(path.name, text) + structural.check_claude_hooks(path.name, text)
        decision, reason = rules.decide(findings)
        payload = {"settings": str(path), "decision": decision, "reason": reason, "findings": [f.to_dict() for f in findings]}
        if args.json_out:
            Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return EXIT[decision]
    return 3


if __name__ == "__main__":
    sys.exit(main())
