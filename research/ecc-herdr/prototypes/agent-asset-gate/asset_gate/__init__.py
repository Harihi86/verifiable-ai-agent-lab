"""agent-asset-gate: static, read-only review of third-party agent assets before installation.

Scope: Claude Code hooks/settings fragments, agent and skill Markdown (frontmatter), MCP configs,
Herdr plugin manifests, and the scripts they reference. Nothing is executed. Output is a JSON/Markdown
report with a decision (allow / review / deny) that a human or Herdr-side installer can gate on.

Detection ideas adapted from ECC's `scripts/ci/scan-supply-chain-iocs.js` (static IOC matching, false-positive
guards), ECC's memory-vault secret patterns, and the Herdr conflict analysis in research/01 (Claude
settings.json strictness and SessionStart hook coexistence).
"""

__version__ = "0.1.0"
