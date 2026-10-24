# Phase 3: ECC vs Herdr, component by component

Baselines: Herdr v0.9.5 @ `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01` (research clone `C:\Herdr-dev\herdr`);
ECC `ecc-universal` 2.2.3, main @ `90606c8315ee09cafc303515c5f33024db6b9882` (`C:\Herdr-dev\ecc`, 915 commits past the
`v2.2.3` tag — main-branch state, not a release). Evidence lives in `research/01`–`06` (sourced, path:line) and
`research/07` (test runs). Classification vocabulary from the prompt: **already implemented**, **worth adopting**,
**worth improving**, **incompatible**, **unnecessary**.

## 1. Architectural framing

| | Herdr | ECC |
|---|---|---|
| What it is | Rust server + TUI that owns terminals, detects coding agents in panes, and exposes one JSON API/CLI (102 methods) for workspace/pane/agent/worktree/plugin control (`research/02 §1-2`) | Node/Markdown plugin bundle for Claude Code and seven other harnesses: 71 agents, 311 skills, 97 commands, 27 hook entries, rules, MCP config, installer (`research/04-06`) |
| Control model | Out-of-process authority: the server decides pane/agent identity and lifecycle; clients (TUI, CLI, plugins, SSH bridge) call in; no per-caller scopes (`02 §3,16`) | In-process prompt-level: hooks run inside the agent's own tool loop; "orchestration" is prompt delegation plus two shell drivers (`05 §3`) |
| Multi-agent | Any kind in any pane, cross-machine via saved SSH machines, events, waits, worktrees (`01 §3`, `02 §5`, `03 §4`) | tmux-pane-per-worker orchestrator that spawns `codex exec`; Codex is the only non-Claude worker target; no Cursor/Grok dispatch (`05 §3`, `06 §8`) |
| Persistence | `session.json` v3 + native agent resume per pane (`03 §2`) | Markdown session summaries per Stop + create-only Memory Vault (`04 §4`) |
| Memory / learning | **None** (zero hits for memory/knowledge/instinct; `03 §3`) | Instincts (observe→score→inject), learned skills, vault (`04 §3-4`) |
| Security posture | OS ACLs on socket/pipe, SDDL on Windows, strict JSON settings edits, Git trust per request; no API auth, no audit log (`03 §6`) | Static IOC scanner, secret regexes, consent-gated installer, but fail-closed blockers, transcript egress via `claude -p`, MCP probe executing configured servers (`04 §8`, `05 §5,7`) |
| Churn | one maintainer-controlled repo, release/preview channels, frozen wire contracts (`AGENTS.md`) | 1,642 commits / 183 authors in 90 days; 200 hook-touching commits; "Unreleased" is one feature (GateGuard) (`04 §9`, `05 §9`) |

Key consequence: ECC's hooks and orchestration assume they *are* the controller inside one harness. Herdr already
is the controller across harnesses. Anything from ECC that wants to own lifecycle, approvals, or dispatch is a
competing controller and is classified **incompatible** below, regardless of code quality.

## 2. Component matrix

| # | Capability | Herdr 0.9.5 state (evidence) | ECC state (evidence) | Classification | Rationale |
|---|---|---|---|---|---|
| 1 | Agent dispatch (start/prompt/wait/read) across kinds | Implemented and tested for 24 kinds, incl. claude/codex/cursor/grok/gemini; `agent start --kind grok` needs only a shell pane + `grok` on PATH (`01 §3-4`) | No dispatch of Grok/Cursor/Gemini; Codex via tmux shell driver (`05 §3`, `06 §8`) | **already implemented** (Herdr) / **incompatible** (ECC orchestrator) | Prompt requirement "Grok under Herdr, not via Codex" is met by Herdr's own `agent start`; prototype C encodes it as a plan |
| 2 | Lifecycle detection (idle/working/blocked) | Screen-manifest engine, hot-reloadable, per-agent TOML; hooks only carry session identity (`01 §1-2`) | Hooks observe Claude tool events; no lifecycle model for other CLIs | **already implemented** | ECC has nothing comparable for non-Claude agents |
| 3 | Session persistence and resume | `session.json` + resume argv per kind, atomic writes, backups/snapshots (`03 §2`) | Markdown session summaries, 30-day prune, re-injected at startup (`04 §4A`) | **already implemented** (process resume) / **worth adopting** (summary content, see #5) | Different layers: Herdr restores processes, ECC restores *context*; Herdr lacks the latter |
| 4 | Cross-agent memory | **absent** (`03 §3`) | Memory Vault: create-only Markdown, JSON frontmatter, secret refusal, lexical search, explicit recall; not shared with Cursor by default (`04 §4B`) | **worth adopting** → prototype A | Herdr sees every agent's pane uniformly, so a Herdr-owned vault is cross-agent by construction; ECC's design (no auto-injection, `trust: unreviewed`) matches the prompt's authority limits |
| 5 | Session summary capture | absent | Mechanical summary at Stop (last prompts, files, tools) + optional `claude -p` LLM summary (`04 §4A`) | **worth adopting (mechanical part only)** → prototype A; LLM part **unnecessary/risky** | `claude -p` from hooks spends tokens and exports transcripts (`04 §8`); Herdr's `agent read` gives the raw material without any model call |
| 6 | Continuous learning / instincts | absent | Observation capture on by default (tool I/O to `~/.local/share/ecc-homunculus`), Haiku observer off by default and dead on native Windows; instincts injected every SessionStart; `/learn` writes auto-discovered skills (`04 §3`) | **incompatible** | Learned content gains execution/approval authority (injected instructions, generated skills, hookify block rules) — explicitly forbidden by the prompt; plaintext tool I/O persistence; Windows-dead |
| 7 | Hooks (Claude settings.json) | Herdr writes one SessionStart entry, CST-preserving, strict JSON, idempotent; drift undetected if a third party rewrites the file (`01 §5`) | 27 entries, each a 1.4 KB inline `node -e` resolver; 6 blocking pre-hooks; per-call git/python spawns (`04 §2`) | **worth improving** (Herdr) / **unnecessary** (ECC hooks as a whole) → prototype B coexistence check | Additive coexistence works; the real risks are JSONC/duplicate-key files and undetected removal of Herdr's entry — a cheap validator closes that gap |
| 8 | Hook-level blockers (GateGuard, config-protection, block-no-verify, hookify) | not a Herdr concern (Herdr never blocks tool calls) | fail-closed exit-2 guards, deny on first edit per file (`04 §2,8`) | **incompatible** | Authority belongs to Herdr/operator, not to prompt-derived rules; availability risk; Claude-event-bound |
| 9 | Context optimization | absent (Herdr has no token model) | `suggest-compact` (transcript-tail heuristics), context monitor; profiles are a preview with `bytes/4` token estimate, "not a tokenizer" (`04 §5`) | **unnecessary** (for Herdr) | Measurement is not real; the useful part (bounded recall budgets) is already inside prototype A |
| 10 | Security scanning of agent assets | absent (plugin install shows a preview only; `02 §9`) | `scan-supply-chain-iocs.js` (zero-dep IOC matcher, CI cron), validators check format not malice (`05 §5`) | **worth adopting (pattern, not code)** → prototype B | A pre-install gate for skills/hooks/MCP/plugins fills a real Herdr gap and reviews ECC itself |
| 11 | Evaluation / scoring | absent | eval-harness is journaling/receipts; scoring lives in prompts and a GAN shell loop; latency/cost scripts transcript-based (`05 §6`) | **deferred** | No runnable, harness-neutral scorer exists to adopt; Herdr events + memory give the raw data for a later evaluator |
| 12 | Worktree management | `worktree.{list,create,open,remove}`, groups, restore gating, request-scoped Git trust (`02 §5`) | `git worktree add -b` scripts, seed overlays, merge-tree classifier; Unix/tmux-leaning (`05 §4`) | **already implemented** | Herdr's is API-level and persisted; ECC's lifecycle classifier (`git merge-tree` dirty/unmerged detection) is a possible later improvement |
| 13 | Cross-harness adapters | Herdr dispatches every CLI natively; no instruction-format conversion (not its job) | Only Claude→Pi is generated from an IR; others hand-maintained; Gemini/Qwen rewrite `tools:`; model tiers left as Claude names (`05 §2`) | **worth adopting (format only)** → prototype C | Reusing ECC's agent frontmatter as the role-packet format lets reviewed ECC agents be dispatched by Herdr without ECC's conversion scripts |
| 14 | Specialist agents / skills content | n/a | ~89 of 311 skills relevant; 71 agents share one frontmatter schema; opinionated rules (immutability, 80 % coverage, mandatory online research) (`06 §2-5`) | **selective** | Dispatchable as role packets through C; rules conflicting with Herdr's AGENTS.md (immutability vs `&mut self`, mandatory web research) must not be adopted as policy |
| 15 | MCP | none exposed or consumed (`03 §5`) | `.mcp.json` (one pinned npx server), memory MCP server, health-check hook that probes configured servers (`04 §2`, `05`) | **unnecessary now** | Herdr's API is the integration surface; an MCP façade over the Herdr socket is a possible future adapter, not an ECC adoption |
| 16 | Installer / global state | `herdr integration install` per agent, idempotent, uninstall removes only its own entries (`01 §5`) | consent-gated, ID-tracked merges, install-state for uninstall; legacy Codex sync sets `git config --global core.hooksPath` (`05 §7`) | **already implemented** (Herdr) | ECC's install-state pattern is good practice but Herdr already has equivalent scoping |
| 17 | Notifications | `notification.show` API/CLI, rate-limited (`02 §12`) | `desktop-notify` Stop hook, no-op on native Windows (`04 §2`) | **already implemented** | — |
| 18 | Remote / SSH / cross-machine | saved machines, API forwarding, strict host keys, private SSH config (`03 §4`) | none | **already implemented** | — |

## 3. Concrete gaps, duplication, conflicts, simplifications

Gaps in Herdr that ECC evidence highlights:
- G1. No cross-agent memory or context handoff between agents/sessions (→ prototype A).
- G2. No pre-install review of instruction-bearing/executable assets; `plugin install` previews commands but checks nothing (→ prototype B).
- G3. `herdr integration status` cannot see that a third party removed Herdr's Claude hook entry (reads only the script marker; `01 §4-5`) (→ B's `coexist` check; proposed Herdr change in `13-phase4-decisions.md`).
- G4. No portable "role packet" so the same reviewed instructions reach claude/codex/cursor/grok/gemini consistently (→ prototype C).

Duplicated functionality (do not adopt from ECC): worktree scripts, tmux orchestrator, session-resume hooks, notification hook, installer.

Architectural conflicts (reject): GateGuard/hookify/config-protection blockers; instinct injection and `/learn`-generated skills; `claude -p` summary/observer calls from hooks; MCP health probe executing configured server commands; `git config --global core.hooksPath`; `multi-*` commands depending on an external `ccg-workflow` runtime that writes to `~/.claude/bin`.

Simplifications available: adopt ECC *formats* (vault document, agent frontmatter) and *patterns* (IOC matching, secret regexes, create-only writes, bounded recall) without ECC's runtime, Node dependency tree, or hook graph. Every prototype here is node-core or Python-stdlib only.

## 4. What measurably improves, and what does not

| Prompt criterion | Candidate | Measured (research/07) | Not measured |
|---|---|---|---|
| Cross-agent memory | A | capture 652 ms after settle; recall digest bounded to 8000 chars; unit tests prove codex+grok captures share one project vault | real agents; recall quality |
| Security | B | 5 ECC areas triaged in < 6 s total; 15 unit tests; caught a real hidden-character defect in this research | semantic analysis; runtime behaviour |
| Reliability / engineering quality | A, B, C | all three have unit + backend integration tests; isolation verified per run | regression against Rust test suite (toolchain absent) |
| Context efficiency | A | recall digest vs raw read sizes recorded per run | token counts with a real tokenizer |
| Execution efficiency | A | unrelated API round-trip unchanged (42.5 vs 43.0 ms median) with hooks linked | behaviour under many simultaneous agents |
