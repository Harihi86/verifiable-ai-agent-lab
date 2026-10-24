# Security findings and regression-test recommendations

## 1. Herdr detection drift lets a prompt answer a trust dialog (confirmed live)

**Finding.** Herdr 0.9.5's bundled Grok manifest (`src/detect/manifests/grok.toml`, version `2026.10.05.1`) knows Grok
Build's option lists with a `┃ n (○)` gutter and its footer hints. Grok Build 1.0.67 renders its directory-trust prompt
as a centered dialog ("Do you trust the contents of this directory?" / `Yes, proceed   y` / `No, quit   n`) with
neither, while the window title is still the idle string `grok`. The `osc_title_idle` rule therefore wins and Herdr
reports **`idle`**; `agent start` returns success with `interactive_ready: true`.

**Impact.** Herdr's `agent prompt` refuses to send input only when it believes the agent is `blocked`. Here it sent the
role prompt; the first character (`Y`) answered "Yes, proceed", the rest landed in the input box (the echoed prompt
starts "ou are acting…"). Consequences: trust for a directory is granted by an accidental keystroke; a prompt starting
with `n` would quit the agent; an orchestrator relying on `agent_blocked` as its approval boundary has no boundary for
this dialog. The same build also changed its footer to `Ctrl+x:shortcuts`, so Herdr's footer-based idle and working
fallbacks cannot match it (the live run was carried by OSC title/progress rules only).

**Severity.** Medium for the orchestrator's authority model (an approval is bypassed, although only for a directory the
operator chose to dispatch into); low for data (no file was changed). Any kind whose UI drifts from its manifest can
exhibit the same class of failure.

**Fix (proposed upstream, validated).** `prototypes/herdr-dispatch/manifests/grok.toml` adds a visible blocker rule
`trust_directory_dialog_blocked` (priority 1195, `whole_recent`, contains the question plus either option label) and
accepts both footer spellings in `esc_cancel_hints_working` and `prompt_hints_idle`. Offline: the captured trust screen
classifies as `blocked`, the post-turn screen as `idle`; Herdr's manifest validator passes; live run 2 shows
`agent start` → `agent_not_ready` ("blocked during startup") and the policy answering the dialog explicitly. The change
sits on the source research branch as commit `5302348e` (bundled and published copies aligned); it is not compiled into
any binary.

**Regression tests recommended for Herdr.**
1. A screen-fixture test per supported agent build: store captured screens (`evidence/real-agent/fixtures/*.txt` is the
   pattern) and assert the classified state with `herdr agent explain --file <fixture> --agent <kind> --json`; fail when a
   dialog fixture classifies as anything but `blocked`. Herdr's `AGENTS.md` asks for engine tests rather than CLI-screen
   tests in the Rust suite, so this belongs in release smoke tooling, keyed by agent version.
2. A dispatch-level invariant: `agent prompt` must never write while the pane shows a dialog fixture; run against a
   disposable server with a replayed screen.
3. Version-drift alarm: when the detected agent version is newer than the manifest's evidence header (here 1.0.34 vs
   1.0.67), surface a warning in `agent start` output.

**Contrast with Codex (verified later the same day).** Herdr's bundled `codex.toml` already carries a `trust_directory`
blocker rule, and in the Codex runs it matched the "Folder access / Trust this folder? … 1. Trust and continue /
2. Quit" screen: `agent start` returned `agent_not_ready`, the prompt was never typed into the dialog, and the approval
was an explicit, logged policy action (`reports/15`, fixture `evidence/real-agent/fixtures/codex-0.163-trust-dialog-screen.txt`).
The failure class is therefore per-manifest drift, not a design flaw of the blocked-state mechanism; the recommended
regression tests below apply to every kind.

**Packaging observation (Codex).** On the research machine no standalone Codex CLI existed; the desktop app bundles two
builds, and only the complete package with `--no-daemon` could do real work from a pane. Herdr's standalone-binary probe
does not see either build. An orchestrator should record the exact executable and version it dispatched (the run records
here do) rather than assume "codex" means one thing.

## 2. Risks found in the evaluated third-party project (ECC) that drove rejections

From [`reports/11 §4`](reports/11-phase2-ecc-assessment.md) and [`reports/04 §8`](reports/04-ecc-hooks-learning-memory.md):

| Risk | Severity | Note |
|---|---|---|
| Observer loop runs a model with unconfined Write fed by tool outputs (prompt injection → arbitrary file writes) | high when enabled | off by default; non-functional on native Windows |
| Hooks send transcript excerpts to the model provider (`claude -p`) | medium | on by default on PreCompact and by thresholds at Stop |
| MCP health probe executes configured MCP server commands on every `mcp__*` call | medium | on |
| Plaintext persistence of prompts, tool I/O and diff previews under the home directory | medium | on in standard/strict profiles |
| Learned content gains authority: instinct lines injected every session, generated skills auto-discovered, generated block rules enforced | medium | on |
| Fail-closed blockers (exit 2 on any exception; deny first edit per file) | medium (availability) | on |
| Inline resolvers `require()` code found under the plugin cache | low-medium | on |

Lesson applied in the prototypes: recalled memory is wrapped as "HISTORICAL REFERENCE ONLY", carries
`trust: unreviewed`, is never injected automatically and never executed; nothing in the prototypes calls a model.

## 3. Findings about the research tooling itself (fixed)

| Finding | Where | Fix | Test |
|---|---|---|---|
| Literal bidirectional/zero-width characters were written into two source files because escape sequences in tool input were decoded; the asset gate flagged its own code | `asset_gate/rules.py`, `herdr_dispatch/roles.py` | character classes built with `chr()`; a source scan found no residual control characters | gate self-scan now "review" only for an intentional regex-definition line |
| A synchronous pipe read blocked `close()` on Windows, leaving a research server running after a script finished | `prototypes/common/herdr_socket.py` | `CancelSynchronousIo` on the reader thread before closing | subsequent runs teardown cleanly (`reports/07 R13`) |
| Memory capture titled a Grok session with a footer-hint line, then with a telemetry banner line | `summarize.js` | terminal-chrome filter (key hints, box borders, banner phrases) | `summarize.test.js` chrome test |
| A gate scan of the prototypes was "deny" only because test fixtures contain fake tokens and a test bidi character | `asset_gate/rules.py` | findings under test/fixture paths capped at `low` unless `--strict` | `FixtureCapTests` |
| The dispatch executor's fixed 120 s subprocess timeout raced Herdr's own 120 s `agent start` timeout (Codex run 1) | `herdr_dispatch/executor.py` | a step's CLI timeout is derived from its own `--timeout` plus a margin | `test_dispatch.py` 8/8 |
| The real-agent preflight resolved a bare executable name against the parent PATH, not the child's | `validate_real_grok.py` | `shutil.which` against the research PATH | run records show the resolved path and version |

## 4. Static pre-install gate: what it catches and what it does not

`prototypes/agent-asset-gate` scans hooks/settings JSON, agent and skill Markdown, MCP configs, Herdr plugin manifests
and scripts for: inline interpreter execution, remote content piped into a shell (critical), outbound network calls,
credential and key-store paths, user-global config writes, direct driving of another agent CLI, destructive or
guard-bypassing commands, encoded payload handling, authority-widening prompt text, hidden characters, secret-shaped
literals (critical), oversized inline hook commands, blocking hook events, unpinned `npx` MCP servers, missing
provenance metadata, and Herdr hook coexistence problems (non-strict JSON, missing or drifted SessionStart entry).
It does not execute anything, resolve dependencies, or reason semantically; "review" means a human reads the line.
Corpus results over ECC are in `evidence/asset-gate/`.

## 5. Safety tests worth keeping as regression suites

- Vault format: refuse foreign schema, path-like ids, oversized bodies, control/bidi characters, unknown or duplicate
  frontmatter; redact the secret pattern set; create-only writes; recall budget and guard header
  (`prototypes/herdr-agent-memory/tests`).
- Dispatch invariants: every plan step is a Herdr CLI call with `authority: herdr`; Grok plans never mention Codex;
  Claude-only model tiers are dropped with a warning; unknown placeholders in role text are never substituted
  (`prototypes/herdr-dispatch/tests`).
- Approval policy: only trust prompts for the dispatched path or read-only permissions inside it are answered; chosen
  options never contain "always", "yolo" or "all" (policy in `validate_real_grok.py`; a unit test for its option parser
  against the captured 1.0.67 screen is recommended).
- Isolation: before/after snapshots of protected and user roots, and a check that no research server process survives a
  run (`prototypes/common/isolation_audit.py`).
