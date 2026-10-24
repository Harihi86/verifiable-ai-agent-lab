# ECC × Herdr: integration assessment and handoff

Date: 2026-10-24. Executor: Claude Code on `<research-host>` (Windows 11 Pro 10.0.26300), working directory `C:\Herdr-dev`.
Status vocabulary used throughout: **implemented** (code exists), **tested** (unit / contract / disposable-backend evidence in
`research/07-test-runs.md`), **proposed** (designed, not built), **blocked** (cannot be done on this executor or without
separate authorization), **unverified** (built but not exercised against the real target).

## 1. Verified baselines

| Item | Value |
|---|---|
| Herdr protected source | `C:\herdr`, v0.9.5, commit `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`, branch `dev/architecture`, tree `8aa25836…` — matches the expected baseline; no difference to report |
| Herdr research repository | `C:\Herdr-dev\herdr`, independent `--no-local` clone (no alternates/hardlinks/worktrees), branch `research/ecc-integration` from that commit |
| Herdr binary used for tests | `C:\Herdr-dev\runtime\bin\herdr-0.9.5\herdr.exe`, official release asset, sha256 `cd877c87…` (zip `d2c6c9c9…`), byte-identical to the production binary, which was never executed |
| ECC | `https://github.com/affaan-m/ECC` (resolved, no redirect), main @ `90606c8315ee09cafc303515c5f33024db6b9882` (2026-10-20), `ecc-universal` 2.2.3 + 915 commits, MIT; `C:\Herdr-dev\ecc`, never executed |
| Handoff archive / baseline JSON | not present on this machine; provenance recorded in `research/00-provenance.md` |
| Toolchain | Python 3.12.10, Node 24.19.0, git 2.55, gh 2.102; **no Rust, Zig, just, MSVC/SDK** |

## 2. Capability comparison (summary; full matrix in `research/12-phase3-comparison.md`)

| ECC capability | Herdr 0.9.5 | Verdict |
|---|---|---|
| Agent dispatch (incl. Grok, Cursor, Gemini) | native, 24 kinds, `agent start --kind grok` needs only a shell pane | already implemented in Herdr; ECC has no Grok/Cursor dispatch |
| Lifecycle detection | screen-manifest engine, hot reload | already implemented |
| Session persistence / resume | `session.json` + native resume per kind | already implemented |
| Cross-agent memory (Memory Vault) | **absent** | **worth adopting → Prototype A** |
| Mechanical session summaries | absent | adopted inside A (LLM summaries rejected) |
| Continuous learning / instincts | absent | **incompatible** (learned content gains authority; plaintext tool I/O; dead on native Windows) |
| Claude hook graph and blockers | Herdr installs one SessionStart hook | **unnecessary / incompatible**; coexistence check adopted → Prototype B |
| Security scanning (IOC scanner) | absent | **worth adopting (pattern) → Prototype B** |
| Cross-harness adapters | not Herdr's job; dispatch is native | **format worth adopting → Prototype C** |
| Orchestration (tmux + `codex exec`) | worktrees + agents + events | **incompatible** (competing controller) |
| Worktree management | API-level, persisted, trust-scoped | already implemented |
| Context optimization | absent | unnecessary (no real measurement in ECC) |
| Evaluation | absent | deferred (no runnable harness-neutral scorer) |
| MCP | none | unnecessary now |

Adoption strategy: **adopt ECC formats and patterns, not its runtime.** Herdr stays the only controller; ECC content enters
only as reviewed data (role packets, vault documents) through Herdr's plugin and CLI surfaces.

## 3. Integration architecture

See `research/13-phase4-decisions.md` §2 for the diagram. In one sentence: Herdr's server owns panes, detection,
dispatch, events and plugins; Prototype A is a Herdr plugin reacting to `pane.agent_status_changed`; Prototype C
emits only Herdr CLI steps; Prototype B runs before anything is installed and needs no Herdr at all.

## 4. Prototypes

### A. `research.agent-memory` (Herdr plugin, Node, node-core only) — implemented, tested
- Files: `prototypes/herdr-agent-memory/{herdr-plugin.toml, package.json, THIRD-PARTY-NOTICES.md, src/on-agent-status.js, src/cli.js, src/lib/{vault-format,vault-store,herdr-client,summarize,transitions,capture}.js, tests/*.test.js, tests/fixtures/fake-herdr.js, integration/test_plugin_backend.py}`.
- Behaviour: on `working → idle|done` (per-pane transition, 15 s cooldown) it reads the pane through `HERDR_BIN_PATH`
  (`agent read`, fallback `pane read`), builds a mechanical summary (last lines, files, commands, error-like lines; ≤4000 chars),
  redacts secrets (ECC's pattern set), writes a create-only Markdown document (`herdr.agent-memory.v1`, JSON frontmatter,
  `trust: unreviewed`) under `HERDR_PLUGIN_STATE_DIR/vault/<project-key>/`, and reports a display-only `memory` token.
  Actions `recall`, `list`, `handoff`; CLI for orchestrators. Recall is explicit, lexical, budgeted (8000 chars), wrapped in a
  "HISTORICAL REFERENCE ONLY" guard; nothing is injected automatically or executed.
- Evidence: 21/21 unit tests; 18/18 backend checks (plugin link, event hook fired by a simulated agent, vault file written in
  652 ms, pane token visible, recall action and direct CLI recall, unlink). Adapted from ECC MIT code with notices.

### B. `agent-asset-gate` (Python stdlib) — implemented, tested
- Files: `prototypes/agent-asset-gate/{asset-gate.py, asset_gate/{rules,structural,scanner,__main__}.py, tests/test_gate.py}`; reports in `outputs/asset-gate/`.
- Behaviour: static scan of hooks/settings JSON, agent/skill Markdown, MCP configs, Herdr plugin manifests and scripts;
  11 text rules + secret literals + structural checks; decision allow/review/deny; test-fixture capping; `coexist` mode
  validates a Claude `settings.json` for strict JSON and Herdr's canonical SessionStart entry (the drift `herdr integration status` cannot see).
- Evidence: 15/15 unit tests; ECC corpus triaged (hooks 82 ms, scripts/hooks 517 ms, agents 461 ms, skills 4.6 s — all
  "review" with specific line-level findings that agree with the hand-written research); caught a real defect in this
  research (literal bidirectional characters that had been decoded into two source files).

### C. `herdr-dispatch` (Python stdlib) — implemented; plan/executor tested in simulation; real agent start **unverified**
- Files: `prototypes/herdr-dispatch/{herdr-dispatch.py, herdr_dispatch/{roles,kinds,plan,executor}.py, tests/test_dispatch.py, integration/test_dispatch_backend.py}`.
- Behaviour: parses an ECC-format agent definition as a role packet; builds a plan whose steps are only Herdr CLI calls
  (`workspace|worktree create`, `agent start <name> --kind <kind> --pane`, `agent prompt --wait`, `agent read`, optional
  handoff into A); Grok is started by Herdr directly, never through Codex; Claude model tiers are dropped for other kinds with
  a warning; native flags are opt-in and annotated with verification status; `--dry-run` and `--simulate` modes.
- Evidence: 8/8 unit tests; 9/9 simulated backend checks (all five steps, 1.5 s end to end, handoff stored in the vault).

### Shared: isolation harness and probes (`prototypes/common/`) — implemented, tested
`herdr_isolated.py` (6/6 unit tests), `smoke_backend.py`, `live_api_probe.py`, `measure_baseline.py`, `herdr_socket.py`,
`isolation_audit.py`, `sync_to_repo.py`.

## 5. Test results and limitations (details: `research/07-test-runs.md`)

| Layer | Result |
|---|---|
| Upstream Python maintenance tests (clone) | 150 run, 2 toolchain errors (cargo / C build), 5 skipped; UI hot-path 6/6 |
| Upstream Rust tests, Bun tests, `just` | **blocked** (no toolchain) |
| Prototype unit tests | harness 6/6, A 21/21, B 15/15, C 8/8 |
| Mocked contract tests | A's fake-Herdr CLI tests; B's synthetic fixtures; C's dry-run against the real binary's argv contract |
| Disposable local Herdr backend | smoke, probe, baseline, A 18/18, C 9/9 — all with per-run resolution records |
| Native agent: **Grok Build 1.0.67** (owner-authorized, 2026-10-24) | two supervised runs in isolated sessions with throwaway repositories: run 1 (bundled manifests) 12/12 checks but exposed a detection gap; run 2 (patched manifest as local override) **13/13** — `agent start --kind grok` → trust prompt reported `blocked` → policy-approved → prompt → correct answer → memory capture → handoff. `research/14-real-grok-validation.md`, `research/07 R12–R13` |
| Native agents claude/codex/cursor/gemini | **not exercised** (not authorized) |
| Cross-machine / SSH / <remote-machine> | **not exercised** (not authorized; link intentionally paused) |

Simulated agents proved Herdr's event, state and plugin machinery; the Grok runs proved the real path for one kind and
found that Herdr's bundled Grok manifest has drifted against Grok Build 1.0.67 (trust dialog not recognised, footer text
changed). Other kinds remain to be validated under authorization.

## 6. Security assessment

- ECC risks that drove rejections: Haiku observer with unconfined Write; `claude -p` transcript egress from hooks; MCP
  health probe executing configured servers; plaintext tool I/O persistence; learned content gaining authority;
  fail-closed blockers; inline resolvers loading code from the plugin cache (`research/11 §4`, `04 §8`).
- Herdr facts relevant to any plugin: the API has no per-caller scopes, so a plugin or any socket client acts with the
  user's full authority; plugins are unsandboxed (`research/02 §8,16`). Prototype A therefore writes only under its state
  dir, never edits agent configs, never sends keys, and treats every pane text as data.
- Prototype A specifics: secret redaction before write and refusal on residual hits; control/bidi rejection; create-only,
  size-capped documents; recall text carries an explicit non-instruction guard; `trust` can only be `unreviewed`.
- Prototype B specifics: read-only; "deny" blocks only a human installer step; calibrated against ECC and against this
  research's own code (which it flagged correctly twice).
- Residual: lexical secret patterns miss unknown token formats; a compromised agent could still write misleading memories
  (mitigated by provenance fields and the untrusted framing, not prevented).

## 7. Performance and resource measurements (this machine, release 0.9.5, headless)

| Measurement | Value |
|---|---|
| Server start → first API success (baseline) | 438 ms |
| `workspace list` round-trip, baseline / with plugin A linked (median) | 43.0 ms / 42.5 ms |
| Server working set, empty headless | ~18.5 MiB |
| Agent settle → memory document on disk (A) | 652 ms (includes `node` start and two CLI callbacks) |
| `plugin action invoke` round-trip | 86 ms |
| Simulated dispatch, 5 steps (C) | ≈1.5 s total |
| Real Grok Build 1.0.67: `agent start` → detected / ready | detected ≈1.1 s after start; ready 4.6 s (run 1), 7.1 s incl. trust prompt + approval (run 2) |
| Real Grok Build: prompt → settled (one read-only turn) | 7.5 s / 8.9 s; agent context shown ≈15K tokens of 256K |
| Real Grok Build: settle → memory document on disk | within the plugin's 30 s poll (captured on the first `working→idle`) |
| Gate scan of all ECC skills (599 files, 4.8 MB) | 4.6 s |
| Token usage | **not measured** (no tokenizer; recall is bounded by characters: 8000 per digest) |

## 8. Rejected and deferred

Rejected: continuous learning/instincts, the hook graph and its blockers, tmux/Codex orchestrator, context profiles,
LLM session summaries, MCP health probe, `multi-*` commands, `core.hooksPath` global edits, CC-BY-SA skill.
Deferred: Memory Vault MCP server, evaluation harness/agent-evaluator, worktree lifecycle classifier, ECC reviewer prompts
as role packets (usable via C once reviewed), a Herdr-side MCP façade.

## 9. Remaining risks and unresolved issues

0. **Detection drift (found live):** Herdr 0.9.5's bundled `grok.toml` reports `idle` while Grok Build 1.0.67 shows its
   directory-trust dialog, so `agent prompt` types into the dialog (run 1: the prompt's first letter granted trust; a prompt
   starting with `n` would have quit Grok). The footer text also changed (`Ctrl+x:shortcuts`). A validated manifest fix is
   staged on the research branch (bundled + published copies) and proven live in run 2; until upstream ships it, use the
   local override `prototypes/herdr-dispatch/manifests/grok.toml` and treat any new working directory as needing a
   supervised trust approval.
1. Real-agent behaviour of A and C is verified for Grok Build only; claude/codex/cursor/gemini remain unverified (see §5).
2. `agent wait <name>` returned `agent_not_found` for a custom-source agent while `agent read` by name worked — needs
   confirmation in Herdr source before relying on waits for custom agents.
3. Lifecycle event names differ in form (`workspace_created` vs `pane.agent_status_changed`); subscribers must handle both.
4. Herdr's `integration status` cannot detect removal of its Claude hook entry (G3); B is a stop-gap, a core fix is proposed.
5. Plugin A spawns one `node` per settle transition; under many simultaneous agents this is bounded by Herdr's 32-concurrent
   plugin command limit, not by A itself.
6. A production Herdr session (`<production-session>`) was observed running during the audits, and
   `C:\herdr\.local\<private>` was rewritten at 17:10:41 and 17:28:35 by something outside this project (no
   research file references it); both facts should be confirmed by the owner against the migration note that said all
   Windows Herdr processes were stopped.
7. The Harihi Works orchestration/governance layer could only be observed by file names; no sanitized modules were available.
8. Grok's own state changed as a consequence of the authorized runs: two throwaway paths were added to
   `~/.grok/trusted_folders.toml`, Grok cloned/refreshed its plugin marketplace caches (its own network activity), and it
   wrote session/log files. This project does not edit Grok's config; the owner may remove the two stale trust entries.

## 10. Prioritized roadmap

1. **Ship the Grok manifest fix** (`src/detect/manifests/grok.toml` + `distribution/agent-detection/grok.toml`, staged on
   the research branch, validator-clean, live-proven): this is the one change with a safety consequence. Then validate
   A and C with `codex`/`claude`/`cursor` the same supervised way (each new agent build may have similar drift).
2. **Core fix for G3**: make `herdr integration status claude|codex|cursor` re-validate the settings entry (Rust change,
   maintainer review; proposal in `research/13 §3`).
3. **Promote B into the install path**: run the gate as a pre-step of `herdr plugin install`/`integration install`
   documentation, and publish B's `coexist` as a `herdr doctor`-style check.
4. **A: operator review loop** — add `reject`/`supersede` actions so a human can curate memories; add per-project retention.
5. **C: role packet library** — a reviewed subset of ECC agents (reviewer, planner, silent-failure-hunter, pr-test-analyzer)
   vetted by B, dispatchable through Herdr.
6. **Evaluation**: use A's captures and Herdr events to build a minimal, harness-neutral outcome log before considering any
   scoring model.
7. **Requests to the owner**: sanitized Harihi Works adapter/role modules for a real comparison; decision on whether
   future research tasks should route through `<owner-entry-skill>` (this one did not, see `research/10 §5`).

## 11. Reproduction (exact, absolute paths)

All commands in `C:\Herdr-dev\prototypes\README.md`; each creates its own `C:\Herdr-dev\runtime\sessions\<name>\` with a
`logs\resolution.json` written before the server starts. Minimal full check:

```
cd C:\Herdr-dev\prototypes\common && python -m unittest tests.test_herdr_isolated
python C:\Herdr-dev\prototypes\common\smoke_backend.py
cd C:\Herdr-dev\prototypes\herdr-agent-memory && node --test "tests/**/*.test.js"
python C:\Herdr-dev\prototypes\herdr-agent-memory\integration\test_plugin_backend.py
cd C:\Herdr-dev\prototypes\agent-asset-gate && python -m unittest tests.test_gate
cd C:\Herdr-dev\prototypes\herdr-dispatch && python -m unittest tests.test_dispatch
python C:\Herdr-dev\prototypes\herdr-dispatch\integration\test_dispatch_backend.py
python C:\Herdr-dev\prototypes\common\isolation_audit.py
```

## 12. Isolation audit (full data: `outputs/isolation-audit.json`, narrative: `research/07 §R10`)

- Changed/created files: only under `C:\Herdr-dev\` (`prototypes/`, `research/`, `outputs/`, `runtime/`, the `herdr` clone
  on branch `research/ecc-integration`, the `ecc` clone) plus this executor's own memory note under
  `%USERPROFILE%\.claude\projects\C--Herdr-dev\memory\`. Upstream maintenance tests created temp files under `%TEMP%`.
- Processes created: research `herdr.exe` servers for 16 named sessions (all stopped, exit 0), their pane shells, `node`
  plugin commands, Python test processes, and — in the two authorized runs — one `grok.exe` each, started by Herdr inside
  the research pane and ended with the pane. None remain.
- Outside the runtime root, the authorized Grok runs caused Grok itself to write under `~/.grok` (sessions, logs, caches,
  marketplace clone, two `trusted_folders.toml` entries); nothing else outside `C:\Herdr-dev` was written by research code.
- Configuration/state/cache roots used: `C:\Herdr-dev\runtime\sessions\<name>\{xdg-config,xdg-state,xdg-data,xdg-cache,home,tmp}` only.
- Protected source: HEAD, tree, index and `.git` metadata unchanged; no untracked files. `C:\herdr\.local` shows writes
  only from the independently running production session's own log.
- Operational environment: `~/.claude/settings.json`, `~/.claude/hooks`, `~/.ssh`, `~/.grok`, `~/.gemini`, `~/.herdr`,
  `%LOCALAPPDATA%\herdr` unchanged; no plugin registered in any production `plugins.json`; no integration installed; no PATH,
  service, scheduled task, or global git config change; cross-machine link untouched; no SSH or MCP connection used.

## 13. Rollback

Everything is contained in `C:\Herdr-dev`. To remove the research components: delete `C:\Herdr-dev\prototypes`,
`C:\Herdr-dev\runtime` (all disposable sessions, logs, the downloaded binary) and optionally `research`, `outputs`,
`C:\Herdr-dev\herdr` and `C:\Herdr-dev\ecc`. To disable without deleting: nothing is active — no plugin is linked in any
live Herdr, no hook is installed, no process runs. The executor memory note can be removed from
`%USERPROFILE%\.claude\projects\C--Herdr-dev\memory\`. No action on `C:\herdr` or any Herdr installation is required.
Optional, owner's choice: delete the two `[folders.'C:\Herdr-dev\runtime\sessions\realgrok-…\tmp\throwaway-repo']`
blocks from `~/.grok/trusted_folders.toml` and the matching `~/.grok/sessions/C%3A%5CHerdr-dev…` directories that Grok
created during the authorized runs.

## 14. Implemented / tested / proposed / blocked at a glance

| Work item | Status |
|---|---|
| Independent clone, pinned ECC, provenance | implemented, verified |
| Isolation harness + audit | implemented, tested |
| Prototype A (memory plugin) | implemented, unit + backend tested, **validated with real Grok Build** (claude/codex/cursor unverified) |
| Prototype B (asset gate) | implemented, unit tested, corpus-run |
| Prototype C (dispatch) | implemented, unit + simulated backend tested, **real `agent start --kind grok` validated twice** (other kinds unverified) |
| Grok manifest fix (trust dialog + footer) | **proposed upstream change, validator-clean, live-proven** (not compiled into a binary here; data-only) |
| Herdr core fix for hook drift (G3) | proposed |
| Role-packet library, memory curation actions, evaluation log | proposed (roadmap) |
| Rust build/tests, Bun tests, `just` recipes | blocked (toolchain) |
| Native-agent and cross-machine validation | blocked (authorization) |

## 15. Research commit identity

Branch `research/ecc-integration` in `C:\Herdr-dev\herdr`; research commit `89d920d2` ("feat(research): add ecc integration
research, prototypes and handoff") on top of baseline `2ecf19a9` (v0.9.5). The diff against the baseline adds only
`research/ecc-integration/` (77 files). Review with:

```
git -C C:\Herdr-dev\herdr diff --stat 2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01..research/ecc-integration
```
Two later commits on the same branch add the owner-authorized real-agent validation: `fix(detect): recognise grok build
1.0.67 trust dialog and shortcuts footer` (the only change outside `research/ecc-integration/`: `src/detect/manifests/grok.toml`
and `distribution/agent-detection/grok.toml`, kept aligned, validator-clean, live-proven) and `docs(research): add real grok
validation evidence and prototype updates`. Nothing was pushed, merged, or published.
