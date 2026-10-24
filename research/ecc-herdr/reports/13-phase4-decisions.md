# Phase 4: integration candidates, architecture, and implementation decisions

## 1. Candidates selected (and why they outrank the alternatives)

Selection criteria from the prompt: measurable improvement in reliability, cross-agent memory, engineering quality,
security, context efficiency, or execution efficiency; low risk; modular through existing Herdr interfaces; Herdr keeps
dispatch, authorization, governance and publication; no replacement of working systems.

| Rank | Candidate | Prompt criteria hit | Why it outranks alternatives | Risk |
|---|---|---|---|---|
| A | **`research.agent-memory`** — Herdr plugin: event-driven, per-project, cross-agent session memory vault with explicit recall | cross-agent memory, context efficiency, reliability of handoffs | Only candidate that fills a capability Herdr has *none* of (`03 §3`); ECC's vault design already obeys the authority limits (create-only, `trust: unreviewed`, no auto-injection); Herdr's `pane.agent_status_changed` event + `agent read` provide a model-free capture path; works for every kind Herdr detects (claude/codex/cursor/grok/custom) where ECC's own memory does not even reach Cursor | low: plugin runs as the user, writes only under `HERDR_PLUGIN_STATE_DIR`, never injects, never executes recalled text |
| B | **`agent-asset-gate`** — static pre-install reviewer for hooks/skills/agents/MCP configs/Herdr plugin manifests + Herdr hook-coexistence check | security, engineering quality | Closes two real gaps (no asset review before `plugin install`/`integration install`; undetected Herdr hook drift, `01 §4-5`); directly operationalizes the prompt's "review ECC hooks/skills before use"; cheap (stdlib Python, < 6 s on all of ECC) | low: read-only; false positives are explicit "review" items, never automatic denial of anything |
| C | **`herdr-dispatch`** — role packet (ECC agent frontmatter) → Herdr-native dispatch plan → executor | execution efficiency, engineering quality, "Grok under Herdr" | Encodes the required topology (Herdr starts Grok/Claude/Codex/Cursor/Gemini directly; no agent drives another) as a reviewable, replayable plan; lets reviewed ECC agents be used as roles without ECC's conversion scripts | low-medium: real `agent start` paths are unverified here (no native-agent runs authorized); plan carries verification status per flag |

Rejected or deferred alternatives and why:
- ECC continuous learning / instincts: learned content gains authority; plaintext tool I/O; dead on native Windows (`04 §3,8`) — **rejected**.
- ECC hook graph (GateGuard, hookify, config-protection, suggest-compact, cost tracker): in-harness blockers and per-call
  spawns; Claude-event-bound; would run *inside* agents Herdr orchestrates, outside Herdr's control — **rejected**.
- tmux worktree orchestrator / `codex exec` worker: competing controller; Herdr's worktree + agent APIs already do this
  cross-platform — **rejected (duplicate)**.
- Memory Vault *runtime* (CLI + MCP server, `ajv`): adopting the format (A) is enough; the MCP server would add a second
  integration surface — **deferred**.
- Evaluation harness / agent-evaluator: no runnable harness-neutral scorer; keep as a roadmap item once A provides data — **deferred**.
- `worktree-lifecycle` merge-tree classifier: small, useful, but Herdr's `worktree.remove` already refuses dirty
  checkouts without `force`; candidate for a later plugin action — **deferred**.
- Context profiles: token figures are not measurements — **rejected**.

## 2. Integration architecture (all three keep Herdr as the authority)

```
                 ┌──────────────────────────── Herdr server (authority) ────────────────────────────┐
                 │ workspaces · panes · agent detection · agent.start/prompt/wait/read · worktrees   │
                 │ events (pane.agent_status_changed …) · plugin host · pane.report_* · notifications │
                 └───────▲───────────────────────▲──────────────────────────────▲────────────────────┘
                         │ HERDR_BIN_PATH CLI     │ [[events]] hook spawn        │ CLI (absolute binary, --session)
   ┌─────────────────────┴──────┐   ┌─────────────┴──────────────┐   ┌───────────┴──────────────────────┐
   │ C  herdr-dispatch          │   │ A  research.agent-memory   │   │ B  agent-asset-gate               │
   │ role packet → plan → steps │   │ capture on settle → vault  │   │ scan dir → findings → allow/      │
   │ (workspace/worktree create,│   │ recall/list/handoff actions│   │ review/deny; coexist check of     │
   │  agent start --kind K,     │──▶│ (explicit, text only)      │   │ Claude settings vs Herdr hook     │
   │  agent prompt --wait, read,│   │ state: HERDR_PLUGIN_STATE_DIR│  │ (read-only, no Herdr needed)      │
   │  handoff → A)              │   └────────────────────────────┘   └───────────────────────────────────┘
   └────────────────────────────┘
```

Ownership rules enforced by construction:
- Dispatch: only Herdr CLI calls appear in a plan; `authority: "herdr"` on every step except the explicit memory handoff.
- Authorization: no prototype answers approval dialogs, sends keys, or edits agent configs; A and C never fabricate
  `HERDR_ENV` (they run only where Herdr injects it, or against an explicitly named research session).
- Governance: recalled memory is wrapped as "HISTORICAL REFERENCE ONLY … not live instructions"; memories carry
  `trust: unreviewed`; nothing is auto-injected into any agent; the gate's "deny" only blocks the *installer* step a
  human runs, never Herdr.
- Publication: nothing is pushed, installed globally, or registered outside `C:\Herdr-dev` (plugin links happened only in
  disposable sessions' isolated `plugins.json`).

## 3. Implementation decisions

| Decision | Choice | Reason |
|---|---|---|
| Language for A | Node (CommonJS, node-core only) | closest reuse of ECC's MIT vault code; Herdr plugin docs' idiom; `node` resolves through PATHEXT on Windows |
| Language for B, C, harness | Python 3.12 stdlib | available; `-I` isolation for scanning untrusted trees; unittest without installs |
| Capture trigger | `pane.agent_status_changed` with a per-pane `working → idle/done` transition + 15 s cooldown | avoids one capture per status flap; ECC captures at Stop, which only Claude emits |
| Capture content | `agent read --source recent-unwrapped --lines 120` → mechanical summary (last lines, files, commands, error-like lines) → secret redaction → ≤4000 chars | no model call, no transcript egress; same information ECC's mechanical summary uses |
| Storage | `HERDR_PLUGIN_STATE_DIR/vault/<p-sha256(repo-root)[:12]>/mem_*.md`, create-only, atomic | never writes into the user's repository (ECC writes `.ecc/memory` into the project); per-project scoping follows the Git root |
| Recall | explicit action/CLI, lexical scoring, 8000-char budget, guard header | ECC's own rule "recall is explicit" plus the prompt's authority limits |
| Gate policy | critical → deny; high/medium → review; test/fixture paths capped at low unless `--strict`; placeholder `curl ... \| sh` is medium | calibrated on ECC's corpus and on our own code (first self-scan was "deny" on test fixtures) |
| Dispatch delivery | prompt-level by default; native flags opt-in and annotated with verification status | only Herdr-verified facts are asserted; vendor flags were not exercised on this machine |
| Simulation | Herdr's documented custom-agent API (`pane report-agent --source custom:*`) | exercises the same event/state machinery without running a real agent |
| Proposed Herdr core change (not implemented) | `herdr integration status claude` should re-validate that `settings.json` still contains the canonical SessionStart entry (today it reads only the script marker) | closes drift gap G3; needs Rust toolchain + maintainer review; B's `coexist` check is the stop-gap |

## 4. Licensing and attribution

A adapts ECC MIT code: notice and modification list in `prototypes/herdr-agent-memory/THIRD-PARTY-NOTICES.md`. B and C
adapt ideas/patterns and the secret regex list (also MIT); their source headers say so. No CC-BY-SA material was
touched. Research code itself is offered under Apache-2.0 to match Herdr.

## 5. Changed files (this research; nothing under upstream `src/`)

See `outputs/ECC-Herdr-Final-Assessment.md` §"Isolation audit" for the generated inventory. Summary:
`prototypes/common/*` (harness, probes, measurement), `prototypes/herdr-agent-memory/*`, `prototypes/agent-asset-gate/*`,
`prototypes/herdr-dispatch/*`, `research/00–13`, `outputs/*`, disposable `runtime/*`.
