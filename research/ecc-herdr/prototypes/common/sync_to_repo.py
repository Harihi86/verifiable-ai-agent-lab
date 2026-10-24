"""Copy the reviewable research artifacts into the independent Herdr clone under research/ecc-integration/.

The working copies stay in C:\\Herdr-dev\\{prototypes,research,outputs}; the clone copy is what the
research branch records. Disposable runtime data, the ECC clone, caches and node_modules are never copied.

Usage: python C:\\Herdr-dev\\prototypes\\common\\sync_to_repo.py [--dry-run]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

WORKSPACE = Path(r"C:\Herdr-dev")
CLONE = WORKSPACE / "herdr"
TARGET = CLONE / "research" / "ecc-integration"
SOURCES = ["prototypes", "research", "outputs"]
SKIP_DIR_NAMES = {"__pycache__", "node_modules", ".pytest_cache", "sessions"}
SKIP_SUFFIXES = {".pyc"}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts) or path.suffix in SKIP_SUFFIXES


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not (CLONE / ".git").exists():
        print("clone not found", file=sys.stderr)
        return 2
    copied = 0
    for name in SOURCES:
        source_root = WORKSPACE / name
        for path in sorted(source_root.rglob("*")):
            if path.is_dir() or should_skip(path.relative_to(WORKSPACE)):
                continue
            destination = TARGET / path.relative_to(WORKSPACE)
            if args.dry_run:
                print(destination)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
            copied += 1
    print(f"{'would copy' if args.dry_run else 'copied'} {copied} files into {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
