"""Structural checks for well-known asset formats. Read-only parsing; nothing is executed."""
from __future__ import annotations

import json
import re
import tomllib
from typing import Iterable

from .rules import Finding

CLAUDE_HOOK_EVENTS = {
    "PreToolUse", "PostToolUse", "PostToolUseFailure", "UserPromptSubmit", "Notification", "Stop", "SubagentStop",
    "SessionStart", "SessionEnd", "PreCompact", "PermissionRequest",
}
BLOCKING_EVENTS = {"PreToolUse", "UserPromptSubmit", "Stop", "SubagentStop", "PermissionRequest"}
HERDR_SESSIONSTART_MATCHER = "^(startup|resume|clear|compact|fork)$"
HERDR_HOOK_MARKER = "herdr-agent-state"
# Herdr plugin event kinds that fire at pane/agent cardinality (performance-sensitive).
HIGH_CARDINALITY_EVENTS = {"pane.agent_status_changed", "pane.output_matched", "pane.updated", "pane.scroll_changed", "layout.updated"}
SHELL_WRAPPERS = {"sh", "bash", "zsh", "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh"}


class DuplicateKeyError(ValueError):
    pass


def _no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise DuplicateKeyError(f"duplicate key: {key}")
        seen[key] = value
    return seen


def parse_strict_json(text: str):
    """Parse the way Herdr's Claude settings editor does: no comments, trailing commas, or duplicate keys."""
    return json.loads(text, object_pairs_hook=_no_duplicates)


def _hook_entries(doc) -> Iterable[tuple[str, dict, dict]]:
    hooks = doc.get("hooks") if isinstance(doc, dict) else None
    if not isinstance(hooks, dict):
        return
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for hook in group.get("hooks", []) or []:
                if isinstance(hook, dict):
                    yield event, group, hook


def check_claude_hooks(relpath: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        doc = parse_strict_json(text)
    except DuplicateKeyError as err:
        return [Finding("JSON-STRICT", "high", relpath, f"{err}; Herdr's settings editor aborts on duplicate keys", tags=["coexistence"])]
    except json.JSONDecodeError as err:
        return [Finding("JSON-STRICT", "high", relpath, f"not strict JSON ({err.msg} at line {err.lineno}); Herdr install/uninstall would fail on this file", tags=["coexistence"])]
    if not isinstance(doc, dict) or "hooks" not in doc:
        return findings
    total = 0
    per_event: dict[str, int] = {}
    for event, group, hook in _hook_entries(doc):
        total += 1
        per_event[event] = per_event.get(event, 0) + 1
        command = str(hook.get("command", ""))
        if event not in CLAUDE_HOOK_EVENTS:
            findings.append(Finding("HOOK-UNKNOWN-EVENT", "low", relpath, f"unknown hook event {event!r}", evidence=command[:120]))
        if event in BLOCKING_EVENTS and hook.get("type", "command") == "command":
            findings.append(Finding("HOOK-CAN-BLOCK", "info", relpath, f"{event} command hook can block or alter agent actions", evidence=command[:120], tags=["authority"]))
        if hook.get("async") and (hook.get("timeout") or 0) < 30 and ("claude" in command or "summary" in command):
            findings.append(Finding("HOOK-TIMEOUT-MISMATCH", "low", relpath, f"async {event} hook with timeout {hook.get('timeout')}s may be killed before it finishes", evidence=command[:120]))
        if HERDR_HOOK_MARKER in command and event == "SessionStart" and group.get("matcher") != HERDR_SESSIONSTART_MATCHER:
            findings.append(Finding("HERDR-HOOK-DRIFT", "medium", relpath, f"Herdr SessionStart hook present but matcher is {group.get('matcher')!r}, expected {HERDR_SESSIONSTART_MATCHER!r}", evidence=command[:120], tags=["coexistence"]))
        if len(command) > 1000:
            findings.append(Finding("HOOK-INLINE-BLOB", "medium", relpath, f"{event} hook command is {len(command)} chars of inline code; review what it loads", evidence=command[:120], tags=["exec"]))
    if total:
        findings.append(Finding("HOOK-INVENTORY", "info", relpath, f"{total} command hooks across {len(per_event)} events: " + ", ".join(f"{k}={v}" for k, v in sorted(per_event.items()))))
    return findings


def herdr_coexistence(relpath: str, text: str) -> list[Finding]:
    """Given a Claude settings.json (or candidate merged result), report Herdr hook presence and strictness."""
    findings: list[Finding] = []
    try:
        doc = parse_strict_json(text)
    except (DuplicateKeyError, json.JSONDecodeError) as err:
        return [Finding("JSON-STRICT", "high", relpath, f"settings not strict JSON: {err}; Herdr integration install/uninstall will refuse to edit", tags=["coexistence"])]
    herdr_entries = [(e, g, h) for e, g, h in _hook_entries(doc) if HERDR_HOOK_MARKER in str(h.get("command", ""))]
    session_start = [(g, h) for e, g, h in _hook_entries(doc) if e == "SessionStart"]
    if not herdr_entries:
        findings.append(Finding("HERDR-HOOK-MISSING", "medium", relpath, "no Herdr SessionStart hook in this file; `herdr integration status` cannot detect this (it reads only the script marker). Repair: `herdr integration install claude`", tags=["coexistence"]))
    else:
        for event, group, hook in herdr_entries:
            ok = event == "SessionStart" and group.get("matcher") == HERDR_SESSIONSTART_MATCHER and hook.get("timeout") == 10
            findings.append(Finding("HERDR-HOOK-PRESENT", "info" if ok else "medium", relpath,
                                    "Herdr SessionStart hook present and canonical" if ok else f"Herdr hook present under {event} with matcher {group.get('matcher')!r} timeout {hook.get('timeout')!r} (non-canonical)",
                                    evidence=str(hook.get("command", ""))[:140], tags=["coexistence"]))
    foreign = [(g, h) for g, h in session_start if HERDR_HOOK_MARKER not in str(h.get("command", ""))]
    if foreign:
        findings.append(Finding("SESSIONSTART-SHARED", "info", relpath, f"{len(foreign)} non-Herdr SessionStart hook(s) share the event; ordering is Claude's, Herdr's entry has timeout 10", evidence="; ".join(str(h.get('command', ''))[:60] for _, h in foreign)[:200], tags=["coexistence"]))
    return findings


def check_mcp_config(relpath: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        doc = parse_strict_json(text)
    except (DuplicateKeyError, json.JSONDecodeError) as err:
        return [Finding("JSON-STRICT", "low", relpath, f"invalid JSON: {err}")]
    servers = doc.get("mcpServers") if isinstance(doc, dict) else None
    if not isinstance(servers, dict):
        return findings
    for name, spec in servers.items():
        if not isinstance(spec, dict):
            continue
        command = str(spec.get("command", ""))
        args = [str(a) for a in spec.get("args", []) or []]
        joined = " ".join([command, *args])
        if re.search(r"\bnpx\b", command) or "npx" in args[:1]:
            pinned = any(re.search(r"@\d", a) for a in args)
            findings.append(Finding("MCP-NPX", "info" if pinned else "medium", relpath,
                                    f"MCP server {name!r} runs via npx ({'version pinned' if pinned else 'UNPINNED: fetches latest remote code at start'})", evidence=joined[:140], tags=["network", "exec"]))
        if "url" in spec and str(spec["url"]).startswith("http://"):
            findings.append(Finding("MCP-PLAIN-HTTP", "medium", relpath, f"MCP server {name!r} uses plaintext http", evidence=str(spec["url"])[:120], tags=["network"]))
        env = spec.get("env") or {}
        if isinstance(env, dict) and any(re.search(r"(?i)(token|secret|key|password)", k) for k in env):
            findings.append(Finding("MCP-ENV-SECRET", "low", relpath, f"MCP server {name!r} expects secret-like env: {', '.join(sorted(env))}", tags=["credentials"]))
        findings.append(Finding("MCP-INVENTORY", "info", relpath, f"MCP server {name!r}: {joined[:100] or spec.get('url', '')}"))
    return findings


FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)


def parse_frontmatter(text: str) -> dict | None:
    match = FRONTMATTER.match(text)
    if not match:
        return None
    data: dict = {}
    current_key = None
    for raw in match.group(1).split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        if re.match(r"^\s+-\s", line) and current_key:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(line.strip()[1:].strip().strip('"\''))
            continue
        if re.match(r"^\s+\S", line) and current_key:
            data[current_key] = (data.get(current_key) or "") if not isinstance(data.get(current_key), list) else data[current_key]
            continue
        key, _, value = line.partition(":")
        current_key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            data[current_key] = [v.strip().strip('"\'') for v in value[1:-1].split(",") if v.strip()]
        else:
            data[current_key] = value.strip('"\'') if value else None
    return data


def check_instruction_asset(relpath: str, text: str) -> list[Finding]:
    """SKILL.md / agent definitions: instruction-bearing inputs with optional executable surfaces."""
    findings: list[Finding] = []
    fm = parse_frontmatter(text)
    if fm is None:
        return findings
    name = fm.get("name") or "?"
    if "hooks" in fm:
        findings.append(Finding("SKILL-HOOKS", "medium", relpath, f"skill {name!r} declares hooks in frontmatter (executable on load)", tags=["exec", "authority"]))
    tools = fm.get("tools") or fm.get("allowed-tools") or []
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",")]
    powerful = sorted({t for t in tools if re.match(r"(?i)^(bash|write|edit|multiedit|powershell|task|agent)$", str(t))})
    if powerful:
        findings.append(Finding("ASSET-TOOLS", "info", relpath, f"{name!r} requests write/exec tools: {', '.join(powerful)}", tags=["authority"]))
    if fm.get("model") and str(fm.get("model")).lower() in ("opus", "sonnet", "haiku"):
        findings.append(Finding("ASSET-MODEL-PIN", "info", relpath, f"{name!r} pins a Claude model tier ({fm.get('model')}); non-Claude harnesses ignore or must map it"))
    if not any(k in fm for k in ("license", "metadata", "origin", "source")):
        findings.append(Finding("ASSET-NO-PROVENANCE", "low", relpath, f"{name!r} has no license/origin metadata in frontmatter", tags=["attribution"]))
    findings.append(Finding("ASSET-INVENTORY", "info", relpath, f"instruction asset {name!r}: {(fm.get('description') or '')[:100]}"))
    return findings


def check_herdr_plugin_manifest(relpath: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as err:
        return [Finding("MANIFEST-INVALID", "high", relpath, f"invalid TOML: {err}")]
    for key in ("id", "name", "version", "min_herdr_version"):
        if key not in doc:
            findings.append(Finding("MANIFEST-MISSING", "high", relpath, f"required manifest field missing: {key}"))
    if "platforms" not in doc:
        findings.append(Finding("MANIFEST-PLATFORMS", "low", relpath, "no top-level platforms; Herdr links with a warning"))
    sections = [("build", "build commands run at install"), ("startup", "startup hooks run after every restore"), ("events", "event hooks"), ("actions", "actions"), ("panes", "panes")]
    for section, label in sections:
        for item in doc.get(section, []) or []:
            command = item.get("command") or []
            if not isinstance(command, list) or not command:
                findings.append(Finding("MANIFEST-COMMAND", "medium", relpath, f"{section} entry without argv command"))
                continue
            head = str(command[0]).lower()
            if head in SHELL_WRAPPERS and len(command) > 1 and command[1] in ("-c", "/c", "-Command", "-EncodedCommand"):
                findings.append(Finding("MANIFEST-SHELL", "medium", relpath, f"{label}: {section} command wraps a shell ({' '.join(map(str, command))[:100]})", tags=["exec"]))
            if any(".." in str(part) for part in command):
                findings.append(Finding("MANIFEST-ESCAPE", "high", relpath, f"{section} command references a path outside the plugin root", evidence=" ".join(map(str, command))[:120]))
            if section == "events":
                on = item.get("on", "")
                if on in HIGH_CARDINALITY_EVENTS:
                    findings.append(Finding("MANIFEST-EVENT-CARDINALITY", "info", relpath, f"event hook on {on!r} spawns a process per event; budget it", tags=["performance"]))
            if section in ("build", "startup"):
                findings.append(Finding("MANIFEST-AUTORUN", "info", relpath, f"{label}: {' '.join(map(str, command))[:100]}", tags=["exec"]))
    findings.append(Finding("MANIFEST-INVENTORY", "info", relpath, f"plugin {doc.get('id')!r} v{doc.get('version')} min_herdr {doc.get('min_herdr_version')}: " + ", ".join(f"{s}={len(doc.get(s, []) or [])}" for s, _ in sections)))
    return findings
