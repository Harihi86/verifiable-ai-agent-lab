"""Isolation audit: prove the protected source and operational Herdr environments were not modified.

Usage: python C:\\Herdr-dev\\prototypes\\common\\isolation_audit.py [--since 2026-10-24T15:48:00] [--json out.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path

PROTECTED = Path(r"C:\herdr")
WORKSPACE = Path(r"C:\Herdr-dev")
DEFAULT_SINCE = "2026-10-24T15:48:00"  # C:\Herdr-dev creation time (empty directory at project start)


def latest_mtime(root: Path, skip: set[str] = frozenset()) -> tuple[float, int, str]:
    latest, count, latest_path = 0.0, 0, ""
    if not root.exists():
        return latest, count, latest_path
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            path = Path(dirpath) / name
            try:
                st = path.stat()
            except OSError:
                continue
            count += 1
            if st.st_mtime > latest:
                latest, latest_path = st.st_mtime, str(path)
    return latest, count, latest_path


def iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).isoformat(timespec="seconds") if ts else ""


def git(args: list[str], cwd: Path) -> tuple[int, str]:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    out = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)
    return out.returncode, (out.stdout + out.stderr).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default=DEFAULT_SINCE)
    parser.add_argument("--json", dest="json_out")
    args = parser.parse_args()
    since = dt.datetime.fromisoformat(args.since).timestamp()
    report: dict = {"since": args.since, "protected": {}, "user_roots": {}, "workspace": {}, "processes": {}}

    # 1. Protected Git repository: HEAD, tree, worktree state, untracked files, index/.git mtimes.
    code, head = git(["rev-parse", "HEAD"], PROTECTED)
    _, tree = git(["rev-parse", "HEAD^{tree}"], PROTECTED)
    _, branch = git(["rev-parse", "--abbrev-ref", "HEAD"], PROTECTED)
    diff_code, diff = git(["diff-index", "--quiet", "HEAD", "--"], PROTECTED)
    _, untracked = git(["ls-files", "--others", "--exclude-standard"], PROTECTED)
    _, worktrees = git(["worktree", "list"], PROTECTED)
    git_dir_latest = latest_mtime(PROTECTED / ".git")
    tracked_latest = latest_mtime(PROTECTED, skip={".git", ".local"})
    local_latest = latest_mtime(PROTECTED / ".local")
    report["protected"] = {
        "head": head, "tree": tree, "branch": branch,
        "expected_head": "2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01", "expected_tree": "8aa25836bb7c8d14ffa866a852dbc724098ca088",
        "head_matches": head == "2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01", "tree_matches": tree == "8aa25836bb7c8d14ffa866a852dbc724098ca088",
        "diff_index_clean": diff_code == 0, "untracked": untracked.splitlines(), "worktrees": worktrees.splitlines(),
        "git_metadata_latest_mtime": iso(git_dir_latest[0]), "git_metadata_latest_path": git_dir_latest[2],
        "git_metadata_modified_since_start": git_dir_latest[0] > since,
        "tracked_files_latest_mtime": iso(tracked_latest[0]), "tracked_files_modified_since_start": tracked_latest[0] > since,
        "dot_local_latest_mtime": iso(local_latest[0]), "dot_local_latest_path": local_latest[2], "dot_local_modified_since_start": local_latest[0] > since,
    }

    # 2. User-level Herdr/agent roots that a careless run could have touched.
    home = Path(os.environ.get("USERPROFILE", ""))
    roots = {
        "APPDATA/herdr": Path(os.environ.get("APPDATA", "")) / "herdr",
        "APPDATA/herdr-dev": Path(os.environ.get("APPDATA", "")) / "herdr-dev",
        "LOCALAPPDATA/herdr": Path(os.environ.get("LOCALAPPDATA", "")) / "herdr",
        "LOCALAPPDATA/herdr-dev": Path(os.environ.get("LOCALAPPDATA", "")) / "herdr-dev",
        "~/.claude/settings.json": home / ".claude" / "settings.json",
        "~/.claude/hooks": home / ".claude" / "hooks",
        "~/.claude/skills": home / ".claude" / "skills",
        "~/.codex": home / ".codex",
        "~/.cursor": home / ".cursor",
        "~/.grok": home / ".grok",
        "~/.gemini": home / ".gemini",
        "~/.ssh": home / ".ssh",
        "~/.herdr": home / ".herdr",
    }
    for label, path in roots.items():
        if path.is_file():
            st = path.stat()
            report["user_roots"][label] = {"exists": True, "latest_mtime": iso(st.st_mtime), "modified_since_start": st.st_mtime > since}
        else:
            latest, count, lpath = latest_mtime(path)
            report["user_roots"][label] = {"exists": path.exists(), "entries": count, "latest_mtime": iso(latest), "latest_path": lpath, "modified_since_start": latest > since}

    # 3. Workspace inventory.
    inventory = {}
    for child in sorted(WORKSPACE.iterdir()):
        if child.name in ("herdr", "ecc"):
            latest, count, _ = latest_mtime(child, skip={".git"})
        else:
            latest, count, _ = latest_mtime(child)
        size = sum(p.stat().st_size for p in child.rglob("*") if p.is_file() and ".git" not in p.parts) if child.is_dir() else child.stat().st_size
        inventory[child.name] = {"files": count, "bytes": size, "latest_mtime": iso(latest)}
    sessions = sorted(p.name for p in (WORKSPACE / "runtime" / "sessions").iterdir()) if (WORKSPACE / "runtime" / "sessions").exists() else []
    code, herdr_status = git(["status", "--short"], WORKSPACE / "herdr")
    _, herdr_branch = git(["rev-parse", "--abbrev-ref", "HEAD"], WORKSPACE / "herdr")
    _, herdr_log = git(["log", "--oneline", "-5"], WORKSPACE / "herdr")
    report["workspace"] = {"inventory": inventory, "runtime_sessions": sessions, "clone_branch": herdr_branch, "clone_status_short": herdr_status.splitlines(), "clone_log": herdr_log.splitlines()}

    # 4. Processes: any herdr.exe started from the workspace binary should be gone after each run.
    ps = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                         "Get-CimInstance Win32_Process -Filter \"Name='herdr.exe'\" | Select-Object ProcessId,CreationDate,ExecutablePath,CommandLine | ConvertTo-Json -Compress"],
                        capture_output=True, text=True)
    try:
        procs = json.loads(ps.stdout) if ps.stdout.strip() else []
        if isinstance(procs, dict):
            procs = [procs]
    except json.JSONDecodeError:
        procs = [{"raw": ps.stdout[:500]}]
    research = [p for p in procs if str(p.get("ExecutablePath") or "").lower().startswith(str(WORKSPACE).lower())]
    others = [{"ProcessId": p.get("ProcessId"), "CreationDate": p.get("CreationDate"), "inspectable": bool(p.get("ExecutablePath"))} for p in procs if p not in research]
    report["processes"] = {"research_binary_running": research, "other_herdr_processes_left_untouched": others}

    verdict = {
        "protected_source_unmodified": report["protected"]["head_matches"] and report["protected"]["tree_matches"] and report["protected"]["diff_index_clean"] and not report["protected"]["untracked"] and not report["protected"]["tracked_files_modified_since_start"],
        "protected_git_metadata_untouched": not report["protected"]["git_metadata_modified_since_start"],
        "protected_dot_local_untouched": not report["protected"]["dot_local_modified_since_start"],
        "user_roots_untouched": not any(v.get("modified_since_start") for v in report["user_roots"].values()),
        "no_research_server_running": not research,
    }
    report["verdict"] = verdict
    text = json.dumps(report, indent=2, default=str)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")
    print(json.dumps({"verdict": verdict, "protected": {k: report["protected"][k] for k in ("head", "branch", "git_metadata_latest_mtime", "dot_local_latest_mtime", "dot_local_latest_path")},
                      "user_roots_modified": [k for k, v in report["user_roots"].items() if v.get("modified_since_start")],
                      "runtime_sessions": len(sessions), "other_herdr_processes": len(others)}, indent=2))
    return 0 if all(verdict.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
