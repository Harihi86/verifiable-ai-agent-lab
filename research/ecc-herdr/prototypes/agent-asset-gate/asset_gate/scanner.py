"""Directory walker and report builder."""
from __future__ import annotations

import fnmatch
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import rules, structural

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target", ".next", "coverage"}
MAX_FILE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_FILES = 20000


@dataclass
class ScanResult:
    root: str
    files_scanned: int = 0
    files_skipped: int = 0
    bytes_scanned: int = 0
    executable_files: int = 0
    instruction_files: int = 0
    elapsed_ms: float = 0.0
    findings: list[rules.Finding] = field(default_factory=list)
    decision: str = "allow"
    reason: str = ""

    def counts(self) -> dict:
        by_sev: dict[str, int] = {}
        by_rule: dict[str, int] = {}
        for finding in self.findings:
            by_sev[finding.severity] = by_sev.get(finding.severity, 0) + 1
            by_rule[finding.rule] = by_rule.get(finding.rule, 0) + 1
        return {"by_severity": by_sev, "by_rule": dict(sorted(by_rule.items()))}

    def to_dict(self, max_findings: int | None = None) -> dict:
        ordered = sorted(self.findings, key=lambda f: (-rules.SEVERITY_ORDER[f.severity], f.rule, f.file, f.line or 0))
        if max_findings is not None:
            ordered = ordered[:max_findings]
        return {
            "root": self.root,
            "decision": self.decision,
            "reason": self.reason,
            "files_scanned": self.files_scanned,
            "files_skipped": self.files_skipped,
            "bytes_scanned": self.bytes_scanned,
            "executable_files": self.executable_files,
            "instruction_files": self.instruction_files,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "counts": self.counts(),
            "findings": [f.to_dict() for f in ordered],
        }


def classify(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if name == "herdr-plugin.toml":
        return "herdr-plugin"
    if name in ("hooks.json", "settings.json", "settings.local.json") or name.endswith("-hooks.json"):
        return "claude-hooks"
    if name in (".mcp.json", "mcp.json") or name.endswith("mcp.json") or "mcp" in name and suffix == ".json":
        return "mcp"
    if suffix in rules.INSTRUCTION_EXTENSIONS:
        return "instruction"
    if suffix in rules.EXECUTABLE_EXTENSIONS:
        return "script"
    if suffix in rules.TEXT_EXTENSIONS:
        return "text"
    return "binary"


def _read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def scan_path(root: Path, *, include: list[str] | None = None, exclude: list[str] | None = None, max_files: int = DEFAULT_MAX_FILES, strict: bool = False) -> ScanResult:
    start = time.perf_counter()
    root = Path(root)
    result = ScanResult(root=str(root))
    candidates: list[Path] = [root] if root.is_file() else []
    if root.is_dir():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for filename in filenames:
                candidates.append(Path(dirpath) / filename)
                if len(candidates) >= max_files:
                    break
            if len(candidates) >= max_files:
                break
    for path in candidates:
        rel = str(path.relative_to(root)) if root.is_dir() else path.name
        rel = rel.replace("\\", "/")
        if include and not any(fnmatch.fnmatch(rel, pattern) for pattern in include):
            continue
        if exclude and any(fnmatch.fnmatch(rel, pattern) for pattern in exclude):
            result.files_skipped += 1
            continue
        kind = classify(path)
        if kind == "binary":
            result.files_skipped += 1
            continue
        try:
            size = path.stat().st_size
        except OSError:
            result.files_skipped += 1
            continue
        if size > MAX_FILE_BYTES:
            result.findings.append(rules.Finding("FILE-TOO-LARGE", "low", rel, f"skipped: {size} bytes exceeds scan limit"))
            result.files_skipped += 1
            continue
        text = _read_text(path)
        if text is None:
            result.files_skipped += 1
            continue
        result.files_scanned += 1
        result.bytes_scanned += size
        if kind == "script":
            result.executable_files += 1
        if kind == "instruction":
            result.instruction_files += 1
        result.findings.extend(rules.iter_text_findings(rel, text, instruction_file=(kind == "instruction")))
        if kind == "claude-hooks":
            result.findings.extend(structural.check_claude_hooks(rel, text))
        elif kind == "mcp":
            result.findings.extend(structural.check_mcp_config(rel, text))
        elif kind == "herdr-plugin":
            result.findings.extend(structural.check_herdr_plugin_manifest(rel, text))
        elif kind == "instruction":
            result.findings.extend(structural.check_instruction_asset(rel, text))
    result.findings = rules.cap_for_test_paths(result.findings, strict=strict)
    result.decision, result.reason = rules.decide(result.findings)
    result.elapsed_ms = (time.perf_counter() - start) * 1000.0
    return result


def render_markdown(result: ScanResult, max_findings: int = 60) -> str:
    data = result.to_dict(max_findings)
    lines = [
        f"# agent-asset-gate report: `{data['root']}`",
        "",
        f"**Decision: {data['decision'].upper()}** — {data['reason']}",
        "",
        f"Files scanned {data['files_scanned']} (executable {data['executable_files']}, instruction {data['instruction_files']}), skipped {data['files_skipped']}, "
        f"{data['bytes_scanned']:,} bytes, {data['elapsed_ms']} ms.",
        "",
        "| severity | count |", "|---|---|",
    ]
    for sev in ("critical", "high", "medium", "low", "info"):
        lines.append(f"| {sev} | {data['counts']['by_severity'].get(sev, 0)} |")
    lines += ["", "| rule | count |", "|---|---|"]
    for rule, count in data["counts"]["by_rule"].items():
        lines.append(f"| {rule} | {count} |")
    lines += ["", f"## Top findings (first {max_findings} by severity)", "", "| sev | rule | file:line | message | evidence |", "|---|---|---|---|---|"]
    for f in data["findings"]:
        loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
        evidence = (f["evidence"] or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {f['severity']} | {f['rule']} | `{loc}` | {f['message'].replace('|', '/')} | `{evidence[:80]}` |")
    return "\n".join(lines) + "\n"


def write_reports(result: ScanResult, json_path: Path | None, md_path: Path | None, max_findings: int | None = None) -> None:
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(result.to_dict(max_findings), indent=2), encoding="utf-8")
    if md_path:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(render_markdown(result, max_findings or 60), encoding="utf-8")
