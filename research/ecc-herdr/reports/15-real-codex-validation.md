# Real-agent validation: Codex CLI under Herdr 0.9.5 (owner-authorized, 2026-10-24)

Authorization (owner, in chat): "run the same supervised real-agent validation with codex in an isolated research
session with a throwaway repository, no production profiles." Same script, isolation and approval policy as the Grok
runs (`research/14-real-grok-validation.md`), now parameterised by agent kind:
`prototypes/herdr-dispatch/integration/validate_real_grok.py --kind codex`.

## 1. Which Codex binary (and why it mattered)

No standalone `codex` CLI is installed: nothing on PATH, in npm's shim directory, WinGet, program directories or IDE
extension folders, and `~/.codex/packages/standalone/releases` (the location Herdr's `codex_standalone_binary_available`
probes) does not exist. The Codex **desktop app** is installed (MSIX `OpenAI.Codex`) and ships two CLI builds:

| Binary | Version | Outcome in a Herdr pane |
|---|---|---|
| `~/.codex/.sandbox-bin/codex.exe` | `codex-cli 0.159.0-alpha.12.1` | default flags: exits at once with "this CLI has no complete local package … rerun … with --no-daemon" (run 1); with `--no-daemon`: runs, but its file-reading tool host is unavailable and the agent cannot read files (run 2) |
| `%LOCALAPPDATA%\OpenAI\Codex\bin\<hash>\codex.exe` (+ command-runner, sandbox-setup, code-mode-host) | `codex-cli 0.163.0-alpha.11.2` | with `--no-daemon`: full interactive session, reads files, completes the task (run 3) |

Each binary was exposed to the research pane only (`herdr workspace create … --env PATH=<dir>;…`), never copied, moved or
put on any global PATH. `--no-daemon` keeps the run away from the desktop app's shared app-server daemon, whose own
`codex.exe app-server`/`exec-server` processes (running since 2026-10-23) were never touched. Herdr's 0.9.4 changelog
already documents Codex `--no-daemon` behaviour for its integration.

## 2. Results

| | Run 1 (`realcodex-…-616d36`) | Run 2 (`…-9494c9`) | Run 3 (`…-7413cb`) |
|---|---|---|---|
| Binary / flags | 0.159 alpha, `--sandbox read-only` | 0.159 alpha, `--sandbox read-only --no-daemon` | **0.163 alpha, `--sandbox read-only --no-daemon`** |
| Herdr detection | detected 1.1 s, process exited → `unknown` | detected 1.1 s → **blocked** (trust) → idle | detected 1.1 s → **blocked** (trust) → idle |
| `agent start` | never settled (CLI timeout race, fixed) | `agent_not_ready` (blocked during startup) — correct | `agent_not_ready` — correct |
| Policy | — | `1` "Trust and continue", `enter` | `1` "Trust and continue", `enter` |
| Prompt turn | — | 51 s; **agent could not read README** (tool host unavailable) | 25 s; `Called Read README.md`, correct three bullets |
| Script checks | 4 run before abort | 13/13 (but see agent side) | **13/13, task completed** |
| Memory capture / recall | — | 2,160 chars / 2 memories | 2,105 chars / 1 memory (1,653 chars vs 1,590 raw) |

Herdr's bundled `codex.toml` needed **no change**: its `trust_directory` rule (priority 950) matched Codex's
"Folder access / Trust this folder? … › 1. Trust and continue / 2. Quit" screen, so — unlike Grok 1.0.67 — the
`agent_blocked` safeguard engaged and the prompt was never typed into a dialog.

## 3. Fixes made during these runs

- Executor (`herdr_dispatch/executor.py`): a step's subprocess timeout now derives from the step's own `--timeout` (ms)
  plus 30 s; the fixed 120 s used before raced Herdr's 120 s start timeout in run 1.
- Validation script: preflight resolves the agent executable with `shutil.which` against the *child* PATH (Windows
  `CreateProcess` resolves a bare name against the parent PATH); `--kind {grok,codex,claude}`, `--extra-arg`,
  `--pane-path-prepend`; numbered-option parser for Codex/Claude dialogs; report file `real-agent-validation.json`.
- Memory summarizer: Codex footer chrome (`? for shortcuts`, `Ask Codex to do anything`) filtered; 23/23 unit tests.

## 4. Side effects on Codex's own state

Codex wrote to `~/.codex` during each run (sessions, history/log sqlite WALs, `config.toml` trust decision, a `skills`
refresh of 49 files, `tmp`), with the desktop app active at the same time, so counts are not attributable to the runs
alone: run 2 +17/61/−6, run 3 +11/62/−4 (added/modified/removed). This project did not read or edit any of it. The
throwaway paths are now recorded as trusted in Codex's config; removing them is the owner's call.

## 5. Verification statement

**Verified** (this machine, Herdr 0.9.5 release binary, isolated session): Herdr starts Codex CLI 0.163.0-alpha.11.2
directly (`agent start --kind codex`), reports its folder-trust prompt as `blocked`, accepts a supervised approval,
submits a prompt, tracks working→idle, reads the result; the memory plugin captures the real settle; the dispatch plan
runs end to end — all with `--no-daemon` and a read-only sandbox.

**Not verified**: Codex in its default daemon mode; the npm/standalone-installer Codex distributions; the 0.159 alpha
binary for real work (its tool host was unavailable); Claude Code; Cursor; Gemini.

Cost: three Codex sessions, one short turn each (25–51 s), no file changes by the agent.
