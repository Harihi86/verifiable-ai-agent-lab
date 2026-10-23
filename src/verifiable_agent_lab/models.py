"""Owner-authored requirements and evidence outcomes."""

import math
import re
from dataclasses import asdict, dataclass
from enum import StrEnum


class Outcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_RUN = "NOT_RUN"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]
    mandatory: bool = True
    input_files: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.name or not self.command or any(not isinstance(v, str) for v in self.command):
            raise ValueError("A check needs a name and a nonempty argument vector")
        if type(self.mandatory) is not bool:
            raise ValueError("mandatory must be a boolean")


@dataclass(frozen=True)
class Task:
    id: str
    objective: str
    checks: tuple[Check, ...]
    dependencies: tuple[str, ...] = ()
    timeout_seconds: float = 10
    max_attempts: int = 3
    max_output_bytes: int = 100_000
    requires_human_acceptance: bool = False

    def __post_init__(self):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", self.id):
            raise ValueError("Task id must be a short filesystem-safe identifier")
        if not self.objective.strip():
            raise ValueError("An objective is required")
        if len({c.name for c in self.checks}) != len(self.checks):
            raise ValueError("Check names must be unique")
        if not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be finite and in (0, 3600]")
        if type(self.max_attempts) is not int or self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if type(self.max_output_bytes) is not int or not 128 <= self.max_output_bytes <= 10_000_000:
            raise ValueError("max_output_bytes must be in [128, 10000000]")
        if type(self.requires_human_acceptance) is not bool:
            raise ValueError("requires_human_acceptance must be a boolean")
        if self.id in self.dependencies:
            raise ValueError("A task cannot depend on itself")

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data["checks"] = tuple(
            Check(
                c["name"],
                tuple(c["command"]),
                c.get("mandatory", True),
                tuple(c.get("input_files", [])),
            )
            for c in data.get("checks", [])
        )
        data["dependencies"] = tuple(data.get("dependencies", []))
        return cls(**data)

    def to_dict(self):
        return asdict(self)


def decide(checks, review, integrity, requires_human_acceptance=False):
    """Fail closed: agreement or optional passes cannot override missing evidence."""
    if not integrity:
        return Outcome.INCONCLUSIVE, "Source or acceptance files changed during verification"
    mandatory = [c for c in checks if c["mandatory"]]
    if any(c["outcome"] == Outcome.FAIL for c in mandatory):
        return Outcome.FAIL, "A mandatory check failed"
    if any(f["disposition"] == "confirmed" for f in review["findings"]):
        return Outcome.FAIL, "Review contains a confirmed defect"
    if any(c["outcome"] == Outcome.BLOCKED for c in mandatory):
        return Outcome.BLOCKED, "A mandatory check could not be launched"
    if not mandatory or any(c["outcome"] == Outcome.NOT_RUN for c in mandatory):
        return Outcome.NOT_RUN, "Mandatory execution evidence is missing"
    if any(c["outcome"] != Outcome.PASS for c in mandatory):
        return Outcome.INCONCLUSIVE, "A mandatory check has unresolved execution evidence"
    if review["outcome"] != Outcome.PASS or review["findings"]:
        return Outcome.INCONCLUSIVE, "Review has unresolved concerns or is incomplete"
    if requires_human_acceptance:
        return Outcome.BLOCKED, "Technical checks passed; owner acceptance is still required"
    return Outcome.PASS, "Configured technical checks passed for this source snapshot"
