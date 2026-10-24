# Component integration assessment (ECC → Herdr)

Condensed from [`reports/12-phase3-comparison.md`](reports/12-phase3-comparison.md) and
[`reports/13-phase4-decisions.md`](reports/13-phase4-decisions.md). Vocabulary: **already implemented** (in Herdr),
**worth adopting**, **worth improving**, **incompatible**, **unnecessary**, **deferred**.

## Framing

Herdr is an out-of-process authority: a server that owns terminals, detects coding agents in panes, and exposes one
JSON API for workspace, pane, agent, worktree and plugin control across local and SSH-connected machines. ECC is an
in-process harness bundle: instruction assets plus Claude Code hooks that run inside one agent's tool loop, with
prompt-level "orchestration" and two shell drivers. Anything from ECC that wants to own lifecycle, approvals or
dispatch competes with Herdr; anything that is a *format* or a *pattern* can be adopted without ECC's runtime.

## Matrix

| Capability | Herdr 0.9.5 | ECC 2.2.3 (@90606c83) | Verdict |
|---|---|---|---|
| Agent dispatch across kinds (incl. Grok, Cursor, Gemini) | native `agent start --kind …`; Grok needs only a shell pane and `grok` on PATH (live-verified) | Codex via tmux driver only; no Grok/Cursor dispatch | already implemented |
| Lifecycle detection | hot-reloadable screen manifests | Claude hook events only | already implemented (but see drift finding) |
| Session persistence / native resume | `session.json` + per-kind resume commands | Markdown summaries | already implemented |
| Cross-agent memory | absent | Memory Vault (create-only, explicit recall, secret refusal) | **worth adopting → Prototype A** |
| Mechanical session summary | absent | at Stop, Claude only | adopted inside A (model-free) |
| LLM summaries / observer | n/a | `claude -p` from hooks; Haiku observer | unnecessary / incompatible (egress, authority) |
| Continuous learning (instincts, generated skills, hookify rules) | absent | injected every session | incompatible (learned content gains authority; dead on Windows) |
| Claude hook graph and blockers | one SessionStart entry | 27 entries, 6 blockers | unnecessary / incompatible; coexistence check adopted → Prototype B |
| Asset security scanning | absent | zero-dep IOC scanner (mature) | **worth adopting (pattern) → Prototype B** |
| Cross-harness instruction format | n/a (dispatch is native) | agent frontmatter / IR; conversion mostly hand-maintained | **format worth adopting → Prototype C** |
| Orchestration | worktrees + agents + events + waits | tmux + `codex exec` | incompatible (competing controller) |
| Worktree management | API-level, persisted, trust-scoped | shell scripts, Unix-leaning | already implemented (lifecycle classifier deferred) |
| Context optimization | none | heuristics; token figures are byte estimates | unnecessary |
| Evaluation | none | journaling/receipts; scoring in prompts | deferred |
| MCP | none | one pinned server; memory MCP; health probe | unnecessary now |
| Installer / global state | per-agent `integration install`, idempotent | consent-gated, ID-tracked | already implemented |

## What was built, and how it stays modular

| Prototype | Herdr interface used | Ownership kept by Herdr | Status |
|---|---|---|---|
| A `research.agent-memory` | plugin manifest `[[events]] on = "pane.agent_status_changed"`, `HERDR_BIN_PATH` callbacks (`pane get`, `agent read`), raw `pane.report_metadata`, actions `recall`/`list`/`handoff`; state under `HERDR_PLUGIN_STATE_DIR` | Herdr decides when an agent settled; the plugin reads what Herdr exposes; nothing is injected into any agent; recall is text with a non-instruction guard | tested; real-agent verified (Grok, Codex 0.163 `--no-daemon`) |
| B `agent-asset-gate` | none at scan time (pure Python); `coexist` reads a Claude `settings.json` to check Herdr's canonical hook entry | a human runs it before `herdr plugin install` / `integration install`; "deny" blocks only that human step | tested; corpus-run |
| C `herdr-dispatch` | only Herdr CLI steps: `workspace`/`worktree create`, `agent start --kind K --pane`, `agent prompt --wait`, `agent read`; optional handoff into A | every step `authority: herdr`; no agent drives another; native agent flags are opt-in and annotated with verification status | tested; real-agent verified (Grok twice, Codex 0.163 `--no-daemon` once) |

Herdr core changes proposed (not implemented here): make `integration status claude|codex|cursor` re-validate the
settings entry (drift gap); ship the Grok manifest fix (commit `5302348e` on the source branch).

## Recommendations

1. Adopt ECC **formats and patterns** (vault document, agent frontmatter, IOC-style static matching, secret regexes,
   create-only writes, bounded recall) — not its hook graph, learning loop, or orchestrator. Everything built here is
   node-core or Python-stdlib only.
2. Keep Herdr as the only authority: plugin surface for capabilities, CLI steps for dispatch, human gate for installs.
3. Before trusting dispatch into untrusted directories, close the detection-drift gap for each agent build in use
   (manifest regression fixtures per version).
4. What production would additionally require: a Rust toolchain build of Herdr with the manifest change, maintainer
   review, real-agent validation of Codex in its default daemon mode and of Claude Code, Cursor and Gemini under the
   same supervised protocol, and an operator review loop for memories (reject/supersede).

## Measurements (research machine, release binary, headless)

| Measurement | Value |
|---|---|
| Server start → first API success | 438 ms |
| `workspace list` round-trip, baseline / with memory plugin linked (median) | 43.0 / 42.5 ms |
| Empty headless server working set | ~18.5 MiB |
| Simulated settle → memory document on disk | 652 ms |
| Real Grok: detected after start / ready (run 1, run 2 incl. trust approval) | ≈1.1 s / 4.6 s, 7.1 s |
| Real Grok: one read-only turn | 7.5 s, 8.9 s (agent UI showed ≈15K of 256K context) |
| Real Codex 0.163 (`--no-daemon`, read-only sandbox): start → ready incl. trust approval / one read-only turn | 9.2 s / 26.3 s (the 0.159 alpha took 51 s and could not read files) |
| Gate scan of all ECC skills (599 files, 4.8 MB) | 4.6 s |
| Token usage | not measured (no tokenizer); recall bounded to 8,000 characters |
