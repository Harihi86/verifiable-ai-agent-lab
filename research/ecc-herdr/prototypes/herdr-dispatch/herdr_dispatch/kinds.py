"""Per-agent-kind delivery adapters.

Every kind is started by Herdr (`herdr agent start <name> --kind <kind> --pane <pane>`). The adapter only decides
how a role's instructions and model hint reach that agent. Two delivery levels exist:

- "prompt": instructions are sent as the first `agent prompt` (works for every kind; the default).
- "native-flag": extra argv after `--` on `agent start`. Flags are listed with a verification status; only
  flags whose presence is verified in Herdr's own source are enabled by default. Unverified vendor flags are
  opt-in via `native_flags=True` and are always reported in the plan so a reviewer can check them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Herdr-supported kinds for `agent start --kind` (docs/next/.../agent-automation.mdx, verified list).
HERDR_KINDS = (
    "pi", "claude", "codex", "gemini", "cursor", "devin", "agy", "cline", "omp", "mastracode", "opencode",
    "copilot", "kimi", "kiro", "droid", "amp", "grok", "hermes", "kilo", "qodercli", "qwen", "letta", "maki", "muse",
)
CLAUDE_MODEL_TIERS = {"opus", "sonnet", "haiku"}


@dataclass
class KindAdapter:
    kind: str
    executable: str
    # Herdr-verified facts (research/01 §3-4): resume command recorded by Herdr for this kind.
    herdr_resume_argv: list[str]
    # Candidate native flags: name -> (argv template, verification status)
    native_flags: dict[str, tuple[list[str], str]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


ADAPTERS: dict[str, KindAdapter] = {
    "claude": KindAdapter(
        kind="claude", executable="claude", herdr_resume_argv=["claude", "--resume", "<session-id>"],
        native_flags={
            "model": (["--model", "{model}"], "vendor-documented, not verified on this machine"),
            "system_prompt": (["--append-system-prompt", "{instructions}"], "vendor-documented, not verified on this machine"),
        },
        notes=["Herdr integration v11 installs a SessionStart hook for session capture (research/01 §5); not required for dispatch."],
    ),
    "codex": KindAdapter(
        kind="codex", executable="codex", herdr_resume_argv=["codex", "resume", "<session-id>"],
        native_flags={"model": (["-m", "{model}"], "appears in Herdr docs example `-- -m gpt-5.4` (agent-automation.mdx); value semantics unverified")},
        notes=[
            "No system-prompt flag known; instructions are delivered as the first prompt.",
            "On Windows Herdr sends a paste boundary before Enter for Codex prompts (docs).",
            "Live-validated 2026-10-24 (research/07 R15-R17, research/15): Herdr 0.9.5 bundled codex.toml reports Codex's folder-trust prompt as blocked; "
            "with the desktop app's complete package (codex-cli 0.163.0-alpha.11.2) and `--sandbox read-only --no-daemon` the whole plan completed. "
            "The app's ~/.codex/.sandbox-bin build (0.159 alpha) cannot do real work from a pane. No standalone CLI was installed on that machine.",
            "Verified in `codex --help` 0.159/0.163: -s/--sandbox <MODE>, -a/--ask-for-approval <POLICY>, -m/--model, -C/--cd, --no-daemon, --no-alt-screen, exec, resume.",
        ],
    ),
    "cursor": KindAdapter(
        kind="cursor", executable="cursor-agent", herdr_resume_argv=["cursor-agent", "<resume-args>"],
        native_flags={"model": (["--model", "{model}"], "vendor-documented, not verified on this machine")},
        notes=["Herdr resolves `cursor-agent.cmd` on Windows (research/01 §6)."],
    ),
    "grok": KindAdapter(
        kind="grok", executable="grok", herdr_resume_argv=["grok", "--resume", "<session-id>"],
        native_flags={"model": (["-m", "{model}"], "verified present in `grok --help` (Grok Build 1.0.67, 2026-10-24); model ids not enumerated")},
        notes=[
            "Verified in `grok --help` 1.0.67: --permission-mode {default,acceptEdits,auto,dontAsk,bypassPermissions,plan}, --no-subagents, --disable-web-search, --max-turns N, --deny/--allow rules, -p single-turn, -r/--resume.",
            "Live-validated 2026-10-24 (research/07 R12-R13): Herdr 0.9.5 starts Grok Build 1.0.67 directly and detects it in ~3 s; "
            "the bundled grok manifest does NOT recognise 1.0.67's directory-trust dialog (reports idle) nor its 'Ctrl+x:shortcuts' footer; "
            "use the patched manifest in prototypes/herdr-dispatch/manifests/grok.toml (local override) until upstream ships it.",
            "A new working directory always triggers Grok's trust prompt; dispatching into an untrusted directory requires a supervised approval step.",
            "Grok Build is started and prompted directly by Herdr: `agent start --kind grok` needs only a shell pane with `grok` on PATH (research/01 §4).",
            "Lifecycle state comes from Herdr's bundled grok.toml manifest (OSC title/progress, `[stop]` chip, `ctrl+.:shortcuts` footer).",
            "No Codex or other agent is involved in controlling Grok.",
        ],
    ),
    "gemini": KindAdapter(
        kind="gemini", executable="gemini", herdr_resume_argv=[],
        native_flags={"model": (["-m", "{model}"], "vendor-documented, not verified on this machine")},
        notes=["Detection only in Herdr 0.9.5 (2-rule manifest, no integration, no resume); readiness is the least deterministic (research/01 §4)."],
    ),
}


def adapter_for(kind: str) -> KindAdapter:
    if kind not in HERDR_KINDS:
        raise ValueError(f"unsupported Herdr agent kind: {kind!r}")
    return ADAPTERS.get(kind) or KindAdapter(kind=kind, executable=kind, herdr_resume_argv=[], notes=["generic adapter: prompt-level delivery only"])


def map_model_hint(kind: str, model_hint: str | None) -> tuple[str | None, str | None]:
    """ECC model tiers are Claude-specific. Returns (model_for_kind, warning)."""
    if not model_hint:
        return None, None
    if kind == "claude":
        return model_hint, None
    if model_hint.lower() in CLAUDE_MODEL_TIERS:
        return None, f"model tier {model_hint!r} is Claude-specific; dropped for kind {kind!r} (same limitation ECC's Pi emitter documents)"
    return model_hint, f"model {model_hint!r} passed through to {kind!r} unverified"


def extra_start_args(kind: str, *, model: str | None, instructions: str, native_flags: bool) -> tuple[list[str], list[str]]:
    """Argv appended after `--` on `agent start`, plus reviewer notes about verification status."""
    adapter = adapter_for(kind)
    args: list[str] = []
    notes: list[str] = []
    if not native_flags:
        return args, [f"{kind}: prompt-level delivery (no native flags); instructions go in the first prompt"]
    for flag_name, (template, status) in adapter.native_flags.items():
        if flag_name == "model" and not model:
            continue
        rendered = [part.format(model=model or "", instructions=instructions) for part in template]
        args.extend(rendered)
        notes.append(f"{kind} native flag {flag_name}: {' '.join(template)} [{status}]")
    return args, notes
