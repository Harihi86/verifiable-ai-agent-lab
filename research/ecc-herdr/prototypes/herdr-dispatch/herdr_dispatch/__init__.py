"""herdr-dispatch: role packet -> Herdr-native dispatch plan -> executor.

Herdr stays the single orchestration, authorization, and execution authority: every step is a Herdr CLI
call (workspace/worktree creation, `agent start --kind <kind>`, `agent prompt --wait`, `agent read`).
Grok Build, Claude Code, Codex, Cursor, and Gemini are all started the same way, directly by Herdr;
no agent is used to drive another agent.

Role packets reuse the ECC agent definition format (Markdown + `name/description/tools/model`
frontmatter, the `ecc.agent-ir.v1` fields) so reviewed ECC agents can be dispatched without conversion
tooling. Model tiers and tool lists that only Claude understands are reported as dropped, mirroring the
fidelity limits ECC's own Pi emitter documents.
"""

__version__ = "0.1.0"
