# ECC × Herdr track roadmap

Status as of 2026-10-24. "Done" means the artifact exists in this track with the stated verification class; nothing
here is production-ready.

| Priority / status | Objective | Dependencies | Acceptance criteria / verification |
|---|---|---|---|
| P0 / Done (proposed upstream) | Recognise Grok Build 1.0.67's trust dialog and footer in Herdr's Grok manifest | none | offline: captured screens classify `blocked` / `idle`; Herdr validator passes; live: `agent start` reports `agent_not_ready` on the dialog (run 2, 13/13). Remaining: maintainer review and a compiled release |
| P0 / Partly done | Same supervised real-agent protocol for Codex, Claude Code, Cursor, Gemini | operator authorization; each CLI installed and authenticated by the operator | **Codex done in one configuration** (desktop-app package 0.163, `--sandbox read-only --no-daemon`, 13/13; bundled manifest handled the trust prompt). Open: Codex default daemon mode and npm/standalone distributions; Claude Code; Cursor; Gemini. Per kind: detection timing, trust/approval handling, prompt integrity, memory capture, no file changes; screen fixtures archived; any manifest drift fixed and validated the same way |
| P1 / Done | Memory plugin, asset gate, Herdr-native dispatch as tested prototypes | Herdr 0.9.5 release binary, Python 3.12, Node 24 | unit suites 23 / 15 / 8; disposable-backend checks 18/18 and 9/9; Grok and Codex real-agent runs |
| P1 / Open | Herdr core: `integration status` re-validates the Claude settings hook entry | Rust toolchain, maintainer review | a settings file with Herdr's entry removed reports "outdated", not "current"; `coexist` check is the stop-gap |
| P1 / Open | Memory plugin operator loop: `reject` / `supersede` actions, per-project retention | prototype A | a rejected memory never appears in recall; retention test |
| P1 / Open (lab) | Asset-gate rules as an optional lab reviewer | none (stdlib) | lab review report produced for a fixture submission containing hooks/MCP config; CI on Linux and Windows |
| P2 / Open (lab) | Screen-fixture grader and real-agent run-record schema in the lab's live-adapter design | lab roadmap P1 | fixtures and expected states versioned; records carry hashes and attempt ids |
| P2 / Open | Reviewed role-packet library (reviewer, planner, silent-failure-hunter, pr-test-analyzer) vetted by the gate, dispatchable through Herdr | prototypes B and C | each packet passes the gate "allow"; dispatch plan dry-run invariants hold |
| P2 / Open | Harness-neutral outcome log from memory captures and Herdr events before any scoring model | prototype A | log schema documented; no model calls |
| P3 / Deferred | Memory Vault MCP façade, worktree lifecycle classifier, evaluation harness adoption | none pressing | revisit after P0/P1 |

Blocked on this executor: compiling Herdr (no Rust/Zig/MSVC), Bun test suites, cross-machine validation.
