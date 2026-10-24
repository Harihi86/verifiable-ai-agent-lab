"""Rule definitions: text patterns plus structural checks. Pure functions, no I/O."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Iterable

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class Finding:
    rule: str
    severity: str
    file: str
    message: str
    line: int | None = None
    evidence: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# --- text rules -----------------------------------------------------------------------------------
# (rule id, severity, compiled regex, message, tags)
TEXT_RULES: list[tuple[str, str, re.Pattern[str], str, list[str]]] = [
    ("EXEC-INLINE", "medium", re.compile(r"\b(?:node\s+(?:-e|--eval)|python3?\s+-c|bash\s+-c|sh\s+-c|powershell(?:\.exe)?\s+[^\n]*?(?:-EncodedCommand|-enc\b|-Command|-c\s)|Invoke-Expression|\biex\b)", re.IGNORECASE),
     "inline code execution through a shell or interpreter flag", ["exec"]),
    ("PIPE-SHELL", "critical", re.compile(r"\b(?:curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^\n|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh|iex|Invoke-Expression|powershell|pwsh)\b", re.IGNORECASE),
     "remote content piped straight into a shell", ["exec", "network"]),
    ("NET-FETCH", "low", re.compile(r"\b(?:curl\s|wget\s|Invoke-WebRequest|Invoke-RestMethod|fetch\(|https?\.request\(|axios\.|urllib\.request|requests\.(?:get|post)\(|net\.connect\()", re.IGNORECASE),
     "outbound network call", ["network"]),
    ("NET-URL", "info", re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+"),
     "URL literal", ["network"]),
    ("CRED-PATH", "high", re.compile(r"(?:~|\$HOME|%USERPROFILE%|\bos\.homedir\(\))?[\\/]?\.(?:ssh|aws|gnupg|netrc|npmrc|pypirc|git-credentials|docker/config\.json)\b|\bid_(?:rsa|ed25519|ecdsa)\b|\.claude[\\/]\.credentials\.json|\.codex[\\/]auth\.json|known_hosts|\bCredential ?Manager\b|\bkeychain\b", re.IGNORECASE),
     "references a credential or SSH/key store path", ["credentials"]),
    ("GLOBAL-CONFIG", "medium", re.compile(r"\bgit\s+config\s+--global\b|core\.hooksPath|\bsetx\s+PATH\b|\[Environment\]::SetEnvironmentVariable|\bHKCU:|\bSet-ItemProperty\b|~/\.(?:claude|codex|cursor|gemini|grok|config/opencode)/(?:settings\.json|config\.toml|hooks\.json|config\.json|settings)", re.IGNORECASE),
     "writes or targets user-global agent or system configuration", ["global-config"]),
    ("AGENT-SPAWN", "medium", re.compile(r"(?:\bclaude\b[^\n]*?(?:[\s'\"]-p\b|[\s'\"]--print\b|--dangerously-skip-permissions)|\bcodex\b[\s'\",]+(?:exec|-q\b|--quiet)|\bgemini\b[\s'\",]+-p\b|\bcursor-agent\b|\bgrok\b[\s'\",]+(?:-p|--prompt|--resume)\b|\bopencode\b[\s'\",]+run\b)", re.IGNORECASE),
     "drives another coding-agent CLI directly (competing controller / token spend)", ["orchestration"]),
    ("DESTRUCTIVE", "high", re.compile(r"\brm\s+-rf\s+(?!\$TMPDIR|/tmp/|\"?\$\{?tmp)|Remove-Item\b[^\n]*-Recurse\b[^\n]*-Force|\bgit\s+push\b[^\n]*--force\b|\bgit\s+reset\s+--hard\b|\b--no-verify\b|\bdel\s+/[sq]\b", re.IGNORECASE),
     "destructive or guard-bypassing command", ["destructive"]),
    ("OBFUSCATION", "medium", re.compile(r"\batob\(|Buffer\.from\([^\n]*['\"]base64['\"]\)|FromBase64String|\bbase64\s+(?:-d|--decode)\b|\\x[0-9a-f]{2}(?:\\x[0-9a-f]{2}){8,}", re.IGNORECASE),
     "encoded or obfuscated payload handling", ["obfuscation"]),
    ("PROMPT-WIDEN", "medium", re.compile(r"\b(?:ignore (?:all |any )?(?:previous|prior|above) instructions|do not ask (?:for )?permission|without asking(?: the user)?|never ask the user|bypass(?:ing)? (?:the )?(?:permission|approval|safety|guard)|disable (?:the )?(?:hook|guard|sandbox|verification)|you are now (?:an?|the) )", re.IGNORECASE),
     "instruction text that tries to widen authority or suppress approvals", ["instruction-bearing"]),
    ("HIDDEN-CHARS", "high", re.compile("[" + chr(0x202A) + "-" + chr(0x202E) + chr(0x2066) + "-" + chr(0x2069) + chr(0x200B) + "-" + chr(0x200D) + chr(0x2060) + chr(0xFEFF) + "]"),
     "zero-width or bidirectional control characters (hidden instruction vector)", ["instruction-bearing"]),
]
# Note: the HIDDEN-CHARS class is built with chr() so this source file never contains the characters it detects.

# Secret literals (same set as ECC memory-vault-format.js, MIT).
SECRET_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("provider API key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b", re.IGNORECASE)),
    ("Stripe key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b")),
    ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{20,}\b")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    ("GitHub token", re.compile(r"\bgh[pors]_[A-Za-z0-9]{16,}\b")),
    ("GitHub token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{16,}\b")),
    ("Google API key", re.compile(r"\bAIza[A-Za-z0-9_-]{16,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("private key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
]

# Lines that are clearly pattern definitions / documentation of the indicator, not use of it.
FALSE_POSITIVE_CONTEXT = re.compile(r"(?:re\.compile|new RegExp|pattern\s*[:=]|/\\b|SECRET_PATTERNS|label\s*:|^\s*[#/]{1,2}\s|^\s*\*\s|^\s*-\s+`)", re.IGNORECASE)

TEXT_EXTENSIONS = {
    ".js", ".cjs", ".mjs", ".ts", ".tsx", ".py", ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".cmd", ".bat",
    ".json", ".jsonc", ".toml", ".yaml", ".yml", ".md", ".mdx", ".txt", ".ini", ".cfg", ".env", ".example", ".lua", ".rb",
}
EXECUTABLE_EXTENSIONS = {".js", ".cjs", ".mjs", ".ts", ".py", ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".cmd", ".bat", ".lua", ".rb"}
INSTRUCTION_EXTENSIONS = {".md", ".mdx", ".txt"}


TEST_PATH = re.compile(r"(?:^|/)(?:tests?|__tests__|fixtures?|testdata|spec)(?:/|$)|\.(?:test|spec)\.[a-z]+$", re.IGNORECASE)
CAP_FOR_TESTS = "low"


def cap_for_test_paths(findings: Iterable[Finding], strict: bool = False) -> list[Finding]:
    """Secret-shaped strings and tricky characters inside test fixtures are expected; cap them unless --strict."""
    capped: list[Finding] = []
    for finding in findings:
        if not strict and TEST_PATH.search(finding.file) and SEVERITY_ORDER[finding.severity] > SEVERITY_ORDER[CAP_FOR_TESTS]:
            finding.severity = CAP_FOR_TESTS
            finding.tags = [*finding.tags, "test-fixture-capped"]
        capped.append(finding)
    return capped


def iter_text_findings(relpath: str, text: str, *, instruction_file: bool) -> Iterable[Finding]:
    lines = text.split("\n")
    for number, line in enumerate(lines, start=1):
        if len(line) > 4000:
            line = line[:4000]
        definitional = bool(FALSE_POSITIVE_CONTEXT.search(line))
        for rule, severity, pattern, message, tags in TEXT_RULES:
            if rule == "PROMPT-WIDEN" and not instruction_file:
                continue
            match = pattern.search(line)
            if not match:
                continue
            sev = severity
            placeholder = rule == "PIPE-SHELL" and bool(re.search(r"\.\.\.|…|<[a-z-]+>|\{[a-z_]+\}", match.group(0)))
            if placeholder:
                sev = "medium"  # describes the pattern (e.g. "curl ... | sh" in a checklist) rather than running it
            elif definitional and rule not in ("HIDDEN-CHARS", "PIPE-SHELL"):
                sev = "info"  # a scanner, docs table, or regex definition mentioning the indicator
            if rule == "NET-URL" and ("github.com" in match.group(0) or "example.com" in match.group(0)):
                continue  # noise: source links
            yield Finding(rule, sev, relpath, message, number, match.group(0)[:160], tags + (["definitional"] if definitional else []))
        for label, pattern in SECRET_RULES:
            match = pattern.search(line)
            if match and not definitional:
                yield Finding("SECRET-LITERAL", "critical", relpath, f"possible {label} literal", number, match.group(0)[:12] + "...", ["secret"])


def max_severity(findings: Iterable[Finding]) -> str:
    best = "info"
    for finding in findings:
        if SEVERITY_ORDER[finding.severity] > SEVERITY_ORDER[best]:
            best = finding.severity
    return best


def decide(findings: list[Finding]) -> tuple[str, str]:
    """Policy: critical -> deny; high/medium -> review; otherwise allow. Returns (decision, reason)."""
    worst = max_severity(findings)
    if worst == "critical":
        return "deny", "critical finding present (secret literal or remote code piped to a shell)"
    if worst in ("high", "medium"):
        counts = {}
        for finding in findings:
            if finding.severity in ("high", "medium"):
                counts[finding.rule] = counts.get(finding.rule, 0) + 1
        summary = ", ".join(f"{rule}x{count}" for rule, count in sorted(counts.items()))
        return "review", f"needs human review: {summary}"
    return "allow", "only informational or low findings"
