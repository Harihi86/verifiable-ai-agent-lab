"""Role packets: parse ECC-style agent Markdown into a harness-neutral structure."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")  # Herdr live agent name rule (docs/agent-automation)
MAX_INSTRUCTION_CHARS = 12000
# Built with chr() so this file never contains the characters it refuses.
HIDDEN_CHARS = re.compile("[" + chr(0x202A) + "-" + chr(0x202E) + chr(0x2066) + "-" + chr(0x2069) + chr(0x200B) + "-" + chr(0x200D) + chr(0xFEFF) + "]")


@dataclass
class RolePacket:
    name: str
    description: str
    instructions: str
    tools: list[str] = field(default_factory=list)
    model_hint: str | None = None
    source: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_frontmatter(block: str) -> dict:
    data: dict = {}
    for raw in block.split("\n"):
        line = raw.rstrip()
        if not line.strip() or line.startswith(" "):
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            data[key.strip()] = [v.strip().strip("\"'") for v in value[1:-1].split(",") if v.strip()]
        else:
            data[key.strip()] = value.strip("\"'")
    return data


def herdr_agent_name(candidate: str) -> str:
    """Coerce an arbitrary role name into Herdr's `[a-z][a-z0-9_-]{0,31}` live-agent name."""
    slug = re.sub(r"[^a-z0-9_-]+", "-", candidate.lower()).strip("-")
    if not slug or not slug[0].isalpha():
        slug = f"r-{slug}" if slug else "role"
    return slug[:32]


def load_role(path: str | Path) -> RolePacket:
    text = Path(path).read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    warnings: list[str] = []
    if not match:
        raise ValueError(f"{path}: no frontmatter; expected ECC-style agent definition")
    meta = _parse_frontmatter(match.group(1))
    body = text[match.end():].strip()
    if len(body) > MAX_INSTRUCTION_CHARS:
        warnings.append(f"instructions truncated from {len(body)} to {MAX_INSTRUCTION_CHARS} chars")
        body = body[:MAX_INSTRUCTION_CHARS]
    if HIDDEN_CHARS.search(text):
        raise ValueError(f"{path}: hidden/bidirectional characters present; refuse to dispatch unreviewed text")
    tools = meta.get("tools") or []
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",") if t.strip()]
    raw_name = str(meta.get("name") or Path(path).stem)
    name = herdr_agent_name(raw_name)
    if name != raw_name:
        warnings.append(f"role name {raw_name!r} coerced to Herdr agent name {name!r}")
    model = meta.get("model")
    return RolePacket(
        name=name,
        description=str(meta.get("description") or "").strip(),
        instructions=body,
        tools=list(tools),
        model_hint=str(model).strip() if model else None,
        source=str(path),
        warnings=warnings,
    )
