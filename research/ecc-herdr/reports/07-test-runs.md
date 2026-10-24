# Test run log (chronological)

All commands run on `<research-host>`, Windows 11 Pro 10.0.26300, from the research workspace.
Full outputs are kept under `C:\Herdr-dev\runtime\logs\`.

## R1. Upstream Herdr Python maintenance tests (research clone, baseline)

- Date: 2026-10-24 16:12 (+08:00)
- Working dir: `C:\Herdr-dev\herdr` (clean checkout of v0.9.5 @ `2ecf19a9`, branch `research/ecc-integration`)
- Tool: `python` 3.12.10
- Command (mirrors `just maintenance-test` minus the `bun test` step, which cannot run because `bun` is not installed):

```
python -m unittest scripts.test_agent_detection_manifest_check scripts.test_changelog scripts.test_config_reference_check scripts.test_docs_translation_parity scripts.test_hermes_integration_asset scripts.test_package_windows_conpty scripts.test_preview scripts.test_release scripts.test_unix_installer scripts.test_vendor_libghostty_vt scripts.test_vendor_portable_pty scripts.test_windows_cross scripts.test_windows_input
python -m unittest scripts.test_ui_hot_path_architecture
```

- Result: `Ran 150 tests in 48.226s — FAILED (errors=2, skipped=5)`; exit code 1. UI hot-path suite: `Ran 6 tests — OK`; exit code 0.
- The two errors are both `FileNotFoundError: [WinError 2]` from `subprocess` and are toolchain blockers, not code regressions:
  - `scripts.test_vendor_libghostty_vt.VendorLibghosttyVtTests.test_embedded_libghostty_logging_is_silenced` (needs a C/Zig build step)
  - `scripts.test_vendor_portable_pty.VendorPortablePtyTests.test_cargo_metadata_resolves_portable_pty_to_vendored_tree` (needs `cargo metadata`)
- Side effects observed: the tests created temporary files under the user's `%TEMP%` (e.g. `...\Temp\tmp3qcqxpvk\libc.txt`, printed by `test_windows_cross`). They used Python's `tempfile` and are owned by the upstream test code. Nothing was written under `C:\herdr`.
- Log: `C:\Herdr-dev\runtime\logs\herdr-maintenance-tests-baseline.log`
- Not run (toolchain absent): `cargo nextest` (Rust unit/integration tests), `bun test` suites (`scripts/release-workflows.test.ts`, `src/integration/assets/*.test.ts`, `scripts/docs`).

## R2. Isolation harness unit tests

- Command: `cd C:\Herdr-dev\prototypes\common && python -m unittest -v tests.test_herdr_isolated`
- See result appended below after the run.
- Result (2026-10-24 16:16): `Ran 6 tests in 0.062s — OK`, exit 0. Verifies: all `HERDR_*` and `XDG_*` keys are stripped, production PATH entries are removed, every root the child sees points under the runtime root, the only `HERDR_*` key set is `HERDR_CONFIG_PATH`, commands use the absolute workspace binary with an explicit `--session`.

## R3. Disposable isolated Herdr backend smoke (release binary, headless)

- Date: 2026-10-24 16:18 (+08:00). Command: `python C:\Herdr-dev\prototypes\common\smoke_backend.py` → exit 0.
- Session: `smoke-20261024-161827-ee8af3`; root `C:\Herdr-dev\runtime\sessions\smoke-20261024-161827-ee8af3\`.
- Resolved before start (`logs\resolution.json`): binary `C:\Herdr-dev\runtime\bin\herdr-0.9.5\herdr.exe` (sha256 `cd877c87…` verified), config `herdr-research.toml`, `XDG_CONFIG_HOME=<root>\xdg-config`, `XDG_STATE_HOME=<root>\xdg-state`; PATH entries removed from the child: `C:\herdr\.local\<private>` and the <private-pilot-path> pilot runtime dir; inherited `HERDR_*`/`XDG_*` keys present in the calling shell: none.
- Server reported (stderr): api socket `<root>\xdg-config\herdr\sessions\<session>\herdr.sock`, client socket `…\herdr-client.sock`, log `…\herdr-server.log`. All inside the runtime root.
- Steps and exit codes: `--version` → `herdr 0.9.5` (0); `server --help` (0); `workspace list` before server → `server_not_running` (1, expected, error JSON names the isolated socket path); server ready after polling `workspace list`; `session list --json` (0, shows `default` not running and the research session running, both under the isolated config dir); `api schema --output` (0, 272,578 bytes, sha256 prefix `9e2af207` — identical to `docs/next/api/herdr-api.schema.json` in the clone); `api snapshot` (0); `workspace list`/`pane list`/`agent list`/`plugin list` (0, all empty); `server agent-manifests --json` (0, every manifest `source_kind: "bundled"`, no remote fetch); `server stop` (0, server process exit 0).
- `herdr-server.log` (11 lines): no update check, no manifest download, no remote/SSH/machine activity; `persist.restore` reported a missing session file (fresh state) and `persist.clear` on stop.
- Files created, all under the session root: `herdr-research.toml`, `logs\*`, `xdg-config\herdr\.plugins.lock`, `xdg-config\herdr\sessions\<session>\herdr-server.log`.
- Outside roots checked before/after (`%APPDATA%\herdr[-dev]`, `%LOCALAPPDATA%\herdr[-dev]`, `C:\herdr\.local\{profiles,services,runtime}`): unchanged (entry counts and latest mtimes identical).
- Conclusion: a disposable Herdr backend can be exercised on this machine under full isolation. This proves CLI/API reachability only; no agents were started.

## R4. Baseline measurement (isolated backend, no plugins)

- Date: 2026-10-24 16:20. Command: `python C:\Herdr-dev\prototypes\common\measure_baseline.py --runs 20 --label baseline` → exit 0.
- Session `measure-baseline-20261024-162048-dfb90b`; raw JSON at `<root>\logs\measure-baseline.json`.

| Metric | Value |
|---|---|
| server start → first successful `workspace list` | 438 ms |
| `workspace list` CLI round-trip, 20 runs (min / median / p95 / max) | 40.1 / 43.0 / 48.4 / 70.5 ms |
| server working set after warm-up (empty headless server) | 19,382,272 bytes (~18.5 MiB) |

- Scope: this machine, release binary 0.9.5, headless server with zero workspaces. It is a reference point for measuring plugin/event-hook overhead later, not a benchmark of Herdr.

## R5. Live API probe over the Windows named pipe (simulated custom agent)

- Date: 2026-10-24 16:22–16:30. Commands: `python C:\Herdr-dev\prototypes\common\live_api_probe.py`, then `python C:\Herdr-dev\prototypes\common\debug_ws_events.py`.
- Sessions `probe-20261024-162215-0e2b55`, `wsev-20261024-162455-bf9449`; raw results in each `<root>\logs\`.
- Verified: `ping` over `\.\pipe\<socket path>` (protocol 22, version 0.9.5); `events.subscribe` acknowledges; pane-scoped subscriptions require `pane_id` (server returns `invalid_request` otherwise); `pane report-agent` from an external process with source `custom:research` drives `working` → `idle`, emits `pane.agent_status_changed` (`{"event":"pane.agent_status_changed","data":{"agent","agent_status","pane_id","workspace_id"}}`), shows in `agent list`; `pane.report_metadata` tokens appear in `pane get`; `pane release-agent` clears it.
- Finding: lifecycle events arrive with underscore names (`"event":"workspace_created"`, `data.type:"workspace_created"`, `tab_created`, `layout_updated`) while sampled events use dotted names; subscribers must match both forms. First probe iteration mis-read this as a missing event.
- `events.wait` requires a `match_event` field (not probed further).
- Housekeeping: the second script's client hung on closing a pipe while a reader thread was blocked; its research server (`wsev-…`) was stopped explicitly through its own session socket (`server stop`, exit 0). Unrelated `herdr.exe` processes visible on the machine (created before this project's runs, not inspectable from this account) were left untouched.

## R6. `research.agent-memory` plugin: unit tests

- Command: `cd C:\Herdr-dev\prototypes\herdr-agent-memory && node --test "tests/**/*.test.js"` (Node v24.19.0)
- First run: 19/21 (two transition tests failed because "never captured" was treated as a recent capture; fixed in `src/lib/transitions.js`). Second run: **21/21 pass**, 0 fail.
- Coverage: vault format round trip and rejections (schema, id, kind, trust, size, control/bidi chars, unknown/duplicate frontmatter), secret detection and redaction, project keying at git root, create-only writes, project isolation, tamper tolerance, ranking (title 8 / tags 6 / body ≤5) and recall budget, settle-transition detection and cooldown, event hook end to end against a fake Herdr CLI (captures `working→idle`, writes under the plugin state dir, never writes into the project, redacts a GitHub token, skips repeat idles), cross-agent capture for `codex` and `grok` into one project vault, pane-read fallback, CLI handoff/recall/list/stats and secret refusal.

## R7. `research.agent-memory` plugin: integration with a disposable isolated Herdr backend

- Command: `python C:\Herdr-dev\prototypes\herdr-agent-memory\integration\test_plugin_backend.py`
- First run (session `plugin-20261024-163831-89e8bf`): 16/18 checks; the two failures were a wrong CLI flag in the test (`plugin action invoke` takes no `--workspace`). Second run (session `plugin-20261024-164206-eb8b02`): **18/18 checks pass**.
- What the backend run demonstrates: `plugin link` registers the plugin with no event-name warnings and the registry (`plugins.json`) lands inside the isolated `XDG_CONFIG_HOME`; a simulated agent (`pane report-agent --source custom:research`) going `working → idle` fires the manifest `[[events]] on = "pane.agent_status_changed"` hook; the hook captured the pane's recent output (which contained the test text `tests/cli/agents.rs`) into `…\xdg-state\herdr\plugins\research.agent-memory\vault\<project-key>\mem_*.md` with `schema: "herdr.agent-memory.v1"` and `source_agent: "codex-sim"`; the plugin log shows one `captured:true` record and one skip for the `working` event; the plugin reported a display-only `memory` token that `pane get` shows; `plugin action invoke research.agent-memory.recall` ran and its log contains the `HISTORICAL REFERENCE ONLY` guard and the agent name; direct CLI recall (`node src/cli.js recall actions.rs --project <cwd> --json`) returned ≥1 memory; `plugin unlink` succeeded.
- Timings (this machine): idle report → vault file on disk 652 ms (includes Herdr event dispatch, `node` start, two CLI callbacks, file write); `plugin action invoke` round-trip 86 ms; `workspace list` median with the plugin linked 42.5 ms vs 43.0 ms baseline (R4), i.e. no measurable overhead on unrelated API calls.
- Not demonstrated: a real claude/codex/cursor/grok process (not authorized); multi-client or remote-machine behaviour.

## R8. `agent-asset-gate`: unit tests and corpus scans

- Unit tests: `cd C:\Herdr-dev\prototypes\agent-asset-gate && python -m unittest tests.test_gate` → first run 12/14 (CLI test used `python -I -m`, which cannot import from cwd; `AGENT-SPAWN` missed `spawnSync('claude', ['-p'])`), fixed; later runs **15/15 pass** (after adding the test-fixture capping test).
- Corpus scans (static, read-only; `python -I C:\Herdr-dev\prototypes\agent-asset-gate\asset-gate.py scan <path>` run from `C:\Herdr-dev\runtime\tmp`; reports in `C:\Herdr-dev\outputs\asset-gate\`):

| Target (ECC @ 90606c83) | Files (exec / instruction) | Time | Decision | Why |
|---|---|---|---|---|
| `hooks/` | 9 (2 / 2) | 82 ms | review | EXEC-INLINE×32 (27 `node -e` inline root resolvers), HOOK-INLINE-BLOB×28 (>1000-char hook commands), GLOBAL-CONFIG×4, HOOK-CAN-BLOCK×19, HOOK-TIMEOUT-MISMATCH×6 |
| `scripts/hooks/` | 61 (61 / 0) | 517 ms | review | CRED-PATH×1, GLOBAL-CONFIG×2, AGENT-SPAWN×1 (`claude -p` summaries), DESTRUCTIVE×1 |
| `agents/` | 71 (0 / 71) | 461 ms | review | CRED-PATH×3, DESTRUCTIVE×4, EXEC-INLINE×10, PIPE-SHELL×1 (prose: "`curl ... \| sh` in a bug report is an attack"), ASSET-MODEL-PIN×71, ASSET-NO-PROVENANCE×71 |
| `.mcp.json` | 1 | 1 ms | allow | one `npx` server, version pinned (`chrome-devtools-mcp@1.10.1`) |
| `skills/` | 599 (131 / 444) | 4.6 s | review | AGENT-SPAWN×57, GLOBAL-CONFIG×25, DESTRUCTIVE×24, EXEC-INLINE×24, CRED-PATH×8, OBFUSCATION, PIPE-SHELL×2 (prose) |

- Calibration changes made from these runs: placeholder pipe-to-shell mentions (`curl ... | sh`) are `medium` not `critical`; findings under `tests/`, `fixtures/`, `*.test.*` are capped at `low` unless `--strict` (the first scan of our own plugin was "deny" purely because its tests contain fake tokens and a bidi test character).
- Self-scan of the prototypes: `herdr-agent-memory` allow; `common` allow; `agent-asset-gate` review (its own `PIPE-SHELL` regex definition line); `herdr-dispatch` review (`AGENT-SPAWN`×4 on the per-kind resume-command table in `kinds.py`, which is exactly the kind of agent-driving code the rule exists to surface).
- The gate also caught a real defect in this research: `rules.py` and `roles.py` initially contained literal U+202A..U+FEFF characters (my escape sequences were decoded on write). Both now build the class with `chr()`; a follow-up source scan found no remaining control/bidi characters outside that fixed test string.
- Scope: text/structural indicators only (no execution, no dependency resolution, no semantic analysis). "review" means a human must read the flagged lines; it is not a verdict of malice.

## R9. `herdr-dispatch`: unit tests and simulated dispatch against the isolated backend

- Unit: `cd C:\Herdr-dev\prototypes\herdr-dispatch && python -m unittest tests.test_dispatch` → **8/8 pass** (after fixing token substitution: `str.format` broke on braces inside role text and on dry runs; now only `{pane_id|workspace_id|agent_status|seq}` are substituted). Covers: parsing a real ECC agent definition (`ecc/agents/code-reviewer.md`, data only), Herdr agent-name coercion, refusal of hidden characters, Grok plan shape (`agent start <name> --kind grok --pane …`, no Codex anywhere, every step `authority: herdr`), Claude model hint kept / Claude tiers dropped for other kinds with a warning, native flags opt-in and annotated "not verified", worktree variant, memory handoff step, JSON/Markdown round trip, CLI plan + dry run against the absolute workspace binary.
- Integration: `python C:\Herdr-dev\prototypes\herdr-dispatch\integration\test_dispatch_backend.py`. Runs 1–3 exposed two simulation defects, both fixed: (a) a custom-reported agent has no live *name* until `agent rename` (the real flow gets it from `agent start <name>`); (b) running `pane run echo …` after reporting the occupant returned the pane to its prompt and Herdr's safety net cleared the custom agent (documented behaviour). Run 4 (session `dispatch-20261024-165544-5e05cf`): **9/9 checks pass** — plan built from the ECC agent for kind `grok`; step 1 workspace create 149 ms; step 2 (simulated start: pane text, report idle, rename) 831 ms; step 3 (simulated prompt: working → idle) 106 ms; step 4 `agent read code-reviewer` 45 ms and contains the pane text; step 5 handoff written into the agent-memory vault via `node …\cli.js handoff` 418 ms; the rename response shows `name: code-reviewer`, `agent_status: idle`.
- Observation (not fixed, recorded for the roadmap): `agent wait <name>` returned `agent_not_found` for a custom-source agent in a side probe (`namediag-20261024-165138-850d19`) while `agent read`/`rename` by name worked; waits on custom-reported agents may need the pane id.
- Scope: the real `agent start --kind grok|claude|codex|cursor|gemini` path was **not** exercised (native-agent runs are not authorized by the prompt). The plan's argv for that step is taken from Herdr's documented CLI and research/01 §3–4; it is marked unverified in the plan output.

## R10. Isolation audit

- Command: `python C:\Herdr-dev\prototypes\common\isolation_audit.py --json C:\Herdr-dev\outputs\isolation-audit.json` (2026-10-24 ~17:00).
- Protected source `C:\herdr`: HEAD `2ecf19a9…` and tree `8aa25836…` unchanged; `git diff-index --quiet HEAD` clean; no untracked files; newest `.git` metadata mtime 15:37:39 (before this project started at ~15:48); newest tracked-file mtime before start. **Unmodified.**
- `C:\herdr\.local`: newest file is `profiles\default\config\herdr\sessions\<production-session>\herdr-server.log` (16:57:27, still being written). That is the log of a production Herdr session **not started by this project**: its five `herdr.exe` processes were created 16:20:25–16:20:54 (none from the workspace binary; not inspectable from this account), no research session ever pointed at that profile (all 12 `resolution.json` records show `XDG_CONFIG_HOME` under `C:\Herdr-dev\runtime\sessions\<name>\`), and the only bare `herdr --version` this project ever ran was a PATH probe at ~16:02 that resolved to the <private-pilot-path> pilot copy and printed a version string. The project did not read, attach to, or signal that server.
- User roots changed during the window, none by research code: `%APPDATA%\herdr\sessions\<production-session>\herdr-server.log` (same production log through the compatibility link), `~/.claude\skills\synced\…` (Claude Code skill sync, 16:53), `~/.cursor\skills-cursor\.sync-manifest.json` (Cursor sync, 16:31), `~/.codex\*.sqlite-wal` and a 2026-10-23 rollout file (an active Codex session, 16:59). `~/.claude\settings.json`, `~/.claude\hooks`, `~/.ssh`, `~/.grok`, `~/.gemini`, `~/.herdr`, `%LOCALAPPDATA%\herdr[-dev]`, `%APPDATA%\herdr-dev`: unchanged.
- Research processes: zero `herdr.exe` from `C:\Herdr-dev\runtime\bin` running at audit time; every research server exited through `server stop` (exit 0 recorded per run).
- Workspace inventory and the full JSON are in `C:\Herdr-dev\outputs\isolation-audit.json`.

## R11. Research commit

- `git -C C:\Herdr-dev\herdr log --oneline -2` → `89d920d2 feat(research): add ecc integration research, prototypes and handoff`, `2ecf19a9 release: v0.9.5`.
- `git diff --name-only 2ecf19a9..HEAD | grep -v '^research/ecc-integration/'` → empty (no upstream path touched). Working tree clean after commit. Protected `C:\herdr` HEAD unchanged (`2ecf19a9`, `dev/architecture`).

## R12. Real Grok Build run 1 — bundled manifests (owner-authorized)

- Date: 2026-10-24 17:09. Command: `cd C:\Herdr-dev\prototypes\herdr-dispatch && python integration/validate_real_grok.py --max-turns 3`. Session `realgrok-20261024-170910-8091d7`.
- Grok: `<USERPROFILE>\.grok\bin\1.0.67\grok.exe`, `grok 1.0.67 (2fe064390d07)`, started by Herdr with `agent start grok-probe --kind grok --pane w1:p1 --timeout 120000 -- --no-subagents --disable-web-search --max-turns 3`.
- Result: 12/12 checks of that script version; exit 0. `pane_agent_detected` 1.1 s after start, `idle` at 4.6 s, prompt turn 7.5 s, correct three-bullet answer, no files changed by the agent, memory capture 2,343 chars, recall returned it, `memory=1 notes` token on the pane.
- Finding: the screen at "idle" was Grok 1.0.67's directory-trust dialog, which the bundled `grok.toml` does not recognise; the prompt's first character answered it. Details and consequences in `research/14-real-grok-validation.md §2`.
- Teardown defect in my event client (blocking `close()` while a reader thread waited on the pipe) was cancelled from outside with `CancelSynchronousIo` on that Python process only; the script then completed its normal teardown (pane close, unlink, `server stop` exit 0). Fixed in `prototypes/common/herdr_socket.py`.
- Grok-home side effects (Grok's own): 977 files added (952 = marketplace Git clone), 8 modified incl. `trusted_folders.toml`.

## R13. Real Grok Build run 2 — patched manifest as isolated local override

- Date: 2026-10-24 17:27. Command: `python -X utf8 integration/validate_real_grok.py --max-turns 3 --manifest-override C:/Herdr-dev/prototypes/herdr-dispatch/manifests/grok.toml`. Session `realgrok-20261024-172705-b30c8d`. (A preceding invocation, session `realgrok-20261024-172641-cd9309`, aborted before starting a server because the shell stripped backslashes from the override path; its directory is empty apart from the prepared config.)
- Offline pre-check: `herdr agent explain --file <captured screen> --agent grok --json` in a serverless isolated session — trust screen: bundled → `idle`/no rule; patched → `blocked` (`trust_directory_dialog_blocked`); post-turn screen with patched → `idle` (`prompt_hints_idle`, `Ctrl+x:shortcuts`). Upstream validator on the patched bundled+published copies: `agent detection manifests ok`; `scripts.test_agent_detection_manifest_check` 13/13.
- Result: **13/13 checks**, exit 0. `agent start` returned `agent_not_ready` ("blocked during startup") 4.6 s in; status `blocked`; policy sent `y` for "Yes, proceed" (logged); idle 0.2 s later; prompt delivered intact; turn 8.9 s; answer correct; capture 1,661 chars with chrome filtered; handoff written; recall 2 memories / 3,035 chars vs raw read 1,643 chars.
- Grok-home side effects: 26 added, 21 modified; `trusted_folders.toml` now lists both throwaway paths.

## R14. Isolation audit after the real-agent runs

- Command: `python C:\Herdr-dev\prototypes\common\isolation_audit.py --json C:\Herdr-dev\outputs\isolation-audit.json` (17:3x).
- Protected `C:\herdr`: HEAD/tree/index/`.git` unchanged. `C:\herdr\.local\<private>` changed at 17:10:41 and again at 17:28:35. No file under `prototypes/`, `research/` or `outputs/` references `<private-service-registry>`, `<private-launcher>`, `<private-launcher>` or `<private-launcher>`; every research server used isolated XDG roots (16 session records). The writer is outside this project (the production service manager or the production session that has been running since 16:20); the proximity to the two Grok runs (about 90 s after each start) is noted as an unexplained coincidence, not a causal path, since neither Grok nor the research harness has any reference to that file.
- User roots changed: as in R10 plus `~/.grok` (expected: Grok's own session, cache, log and trust files from the authorized runs).
- No research `herdr.exe` running; 5 foreign `herdr.exe` processes left untouched.

## R15. Real Codex run 1 — app-bundled binary, default flags (owner-authorized)

- Date: 2026-10-24 17:42. Session `realcodex-20261024-174232-616d36`. No `codex` exists on PATH, in npm, WinGet or program dirs, and `~/.codex/packages/standalone/releases` (what Herdr's `codex_standalone_binary_available` checks) is absent; the Codex desktop app (MSIX `OpenAI.Codex`) ships `~/.codex/.sandbox-bin/codex.exe` = `codex-cli 0.159.0-alpha.12.1`, a full CLI by `--help`. It was made visible to the research pane only via `workspace create --env PATH=<that dir>;…` (no copy, no global change).
- `agent start codex-probe --kind codex --pane w1:p1 --timeout 120000 -- --sandbox read-only`: Herdr detected `codex.exe` 1.1 s after start, then the process exited with `Error: this CLI has no complete local package; install a packaged Codex CLI or use the standalone installer … rerun the same command with --no-daemon`; detection went Codex → none → `unknown`. `agent start` never settled, and my executor's fixed 120 s subprocess timeout raced Herdr's 120 s start timeout (TimeoutExpired); the script's `finally` teardown ran (server exit 0). Executor fixed: a step's CLI timeout now derives from its own `--timeout` plus 30 s.
- Also fixed: the preflight probe used a bare executable name, which Windows resolves against the parent PATH, not the child env; it now resolves with `shutil.which` against the research PATH.

## R16. Real Codex run 2 — same binary with `--no-daemon`

- Date: 2026-10-24 17:46. Session `realcodex-20261024-174616-9494c9`. Flags after `--`: `--sandbox read-only --no-daemon`. **13/13 script checks**, exit 0.
- Herdr side (verified): `pane_agent_detected` 1.1 s after start; the bundled `codex.toml` `trust_directory` rule reported Codex's "Folder access / Trust this folder? … › 1. Trust and continue / 2. Quit" screen as **blocked** 4.5 s in; `agent start` returned `agent_not_ready`; policy sent `1`, then `enter` when the same dialog persisted; idle 0.3 s later; brief working/idle flicker (Codex startup), then `agent prompt --wait` → working → idle after 51.4 s; `agent read` 1,787 chars; memory capture 2,160 chars (`source_agent: "codex"`); handoff; recall 2 memories / 3,030 chars; pane token `memory=2 notes`.
- Agent side (**not** achieved): Codex (model label "GPT-6.1-Sol xhigh") reported "Could not read README.md because the tool host is unavailable … Browser security policy blocked local-file access; no files changed" — its file-reading surface was not available in this `--no-daemon` configuration of the app-bundled alpha binary. The three bullets the check accepted are that failure report, so the task was not completed. Nothing in the repository changed.
- Codex-home side effects (Codex's own, with the desktop app concurrently active so attribution is mixed): 17 added, 61 modified (49 under `skills`, `config.toml` — "Your trust decision will be saved", sessions, sqlite WALs), 6 removed. Not touched by this project.
- Processes: none from this run remained; the desktop app's own `codex.exe app-server`/`exec-server` processes (running since 2026-10-23) were left alone.

## R17. Real Codex run 3 — complete packaged binary with `--no-daemon` (verified)

- Date: 2026-10-24 17:48. Session `realcodex-20261024-174838-7413cb`. Binary: the Codex desktop app's complete package `%LOCALAPPDATA%\OpenAI\Codex\bin\<package-id>\codex.exe` = `codex-cli 0.163.0-alpha.11.2` (beside `codex-command-runner.exe`, `codex-windows-sandbox-setup.exe`, `codex-code-mode-host.exe`), made visible to the research pane only via `--env PATH=…`; flags after `--`: `--sandbox read-only --no-daemon` (the app's shared app-server daemon was never contacted).
- Result: **13/13 checks**, exit 0, and this time the agent completed the task: "Called Read README.md" and three correct bullets ("No files changed; nothing remains to do"), model label "GPT-6.1-Sol xhigh", "Worked for 25s".
- Herdr timeline: `agent start` issued +5.2 s; `pane_agent_detected` +6.3 s; **blocked** (bundled `trust_directory` rule on "Folder access / Trust this folder? … › 1. Trust and continue / 2. Quit") +9.8 s, `agent start` → `agent_not_ready`; policy `1` then `enter`; idle +12.7 s; startup working/idle flicker; `agent prompt --wait` +14.4 s → working +16.1 s → idle +40.5 s; read + handoff +40.7 s. start→ready 9.2 s; prompt→settled 26.3 s.
- Memory plugin: capture 2,105 chars (`source_agent: "codex"`), pane token `memory=3 notes` (two auto-captures from the startup flicker/turn plus the handoff), recall for "README" 1 memory / 1,653 chars vs raw read 1,590 chars. Capture title landed on Codex's footer (`? for shortcuts`); the summarizer's chrome filter was extended for Codex's footer lines afterwards (23/23 unit tests).
- Codex-home side effects (Codex's own; desktop app concurrently active): 11 added, 62 modified (49 under `skills`, `config.toml` trust decision, sessions, sqlite WALs), 4 removed. Not touched by this project. No process from the runs remained.
- Verification statement: Herdr 0.9.5 dispatch of Codex (`agent start --kind codex`, trust-prompt detection, prompt/wait/read) and the two prototypes are **verified with Codex CLI 0.163.0-alpha.11.2 in `--no-daemon`, read-only sandbox mode on this machine**. Not verified: Codex's default daemon mode, the standalone `npm`/installer distributions, Claude Code, Cursor, Gemini.
