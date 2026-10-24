# Herdr integration candidate: ECC-derived integrations on Herdr 0.9.5

Branch `integration/ecc-candidate`, based on the Herdr v0.9.5 release commit `2ecf19a9`. This is a controlled
integration candidate, tested in a dedicated integration environment on one Windows 11 host. **Nothing in it is
production-ready**, and it is not proposed upstream (section 9).

Herdr stays the only orchestration authority. Every agent, pane, workspace and session operation goes through Herdr's
own CLI/API, Herdr's detection decides agent state, and its persistence owns the session. No component is compiled
into the binary except the two detection-manifest fixes and the Windows GNU build fix.

## 1. Status

| Item | What it is | State | Main evidence |
|---|---|---|---|
| Grok Build 1.0.67 detection fix | `grok.toml` 2026.10.24.1: trust dialog is a visible blocker; new footer spelling | **Tested.** Ready to report upstream as a bug | fixtures fail on v0.9.5, pass on the candidate; 3 real Grok runs |
| Codex 0.163 shared-picker fix | `codex.toml` 2026.10.24.1: the selection picker (rate-limit model switch) is a visible blocker | **Tested** (found in this round) | fixture fails on v0.9.5, passes on the candidate; live run blocked and dismissed |
| Windows GNU build | `crates/ghostty-vt/build.rs` maps `*-windows-gnu` to Zig and stages the archive under its GNU name | **Tested on one host.** Development artifact only, not a release artifact | release and debug builds, full test suite, clippy |
| `agent-memory` plugin | Per-project memory vault captured from Herdr's completed-turn signal | **Tested integration candidate** | 41 unit tests, 3 backend suites, lifecycle 22/22, 6 real-agent captures |
| `asset-gate` | Pre-install review bound to the exact reviewed content; explicit operator approval | **Tested prototype** | 18 unit tests, backend 12/12 against a real Herdr server |
| `dispatch` adapter | Role packet to an allowlisted plan of Herdr CLI steps | **Tested prototype** | 19 unit tests, backend 9/9, real Grok/Codex/Claude runs |
| `candidate_install.py` | Side-by-side builds in a dedicated environment with verified activate, rollback, uninstall | **Tested** in the integration environment | 4 unit tests, lifecycle 22/22 |

"Tested" means the listed tests pass on this host with the recorded binaries. It does not mean reviewed by Herdr's
maintainers, exercised on Linux or macOS, run under load, or hardened against a malicious local user (see
`SECURITY.md`).

## 2. Commits

| Commit | Subject |
|---|---|
| `d29f1132` | fix(detect): recognise grok build 1.0.67 trust dialog and shortcuts footer |
| `cad754d3` | fix(build): link vendored libghostty-vt for windows-gnu targets |
| `d71b8bb4` | test(detect): cover centered trust dialogs, footer spellings and approval lists |
| `727ee977` | test(detect): add captured agent screen fixtures with a binary smoke check |
| `dcd15cbe` | test(vendor): read vendored libghostty sources as utf-8 |
| `08dadb37` | feat(integrations): add agent memory, asset gate and dispatch candidates |
| `e7ff4c4b` | test(integrations): move captured agent screen check out of the test suite |
| `dfa2462c` | feat(integrations): add candidate installer, lifecycle test and security notes |
| `06281054` | fix(detect): treat the codex 0.163 shared picker as a blocker |
| `493f3706` | fix(integrations): make simulated and real agent turns deterministic |
| next commit | test(integrations): run the asset gate against a real herdr server |
| next commit | docs(integrations): add the integration candidate report |

The engine-level detection tests in `d71b8bb4` use synthetic manifests, as AGENTS.md requires. The captured-screen
check from `727ee977` was moved out of Herdr's test suite by `e7ff4c4b`, because AGENTS.md forbids classifying captured
CLI screens against bundled rules in Herdr's own tests.

Binaries used:

| Build | Source | SHA-256 |
|---|---|---|
| Herdr v0.9.5 official Windows release (reference) | `2ecf19a9` | `cd877c8744296f4a38a2703bf13cf11728973649ec54959959c4587ffe5368b2` |
| Candidate release build 1 | Rust sources of `08dadb37` | `ee1342e94179854e07f12427be1a345390803cd1da7b1397f440555e2a316083` |
| Candidate release build 2 (final, installed as `candidate-493f3706`) | Rust sources of `06281054` = `493f3706` | `c7710ce439824c4c3063f75cb3681da240b3bbe2a8c07437b94a80bfe986bbe8` |

Builds 1 and 2 differ only in the bundled Codex manifest. Grok and Claude Code results from build 1 therefore hold for
build 2; Codex was rerun on build 2.

## 3. Reproducible build (Windows, no MSVC)

The host has no MSVC build tools or Windows SDK, so the candidate targets `x86_64-pc-windows-gnu` and links with Zig
through cargo-zigbuild. Every tool lives in a workspace toolchain directory with verified hashes
(`C:\Herdr-dev\toolchain\BOOTSTRAP.md`). No global PATH, registry, cargo/rustup home or security setting is changed.

| Component | Version |
|---|---|
| Rust | 1.96.1 (`rust-toolchain.toml`), GNU host toolchain, rustfmt and clippy |
| Zig | 0.16.0 |
| cargo-zigbuild | 0.24.0 |
| arocc (Zig package for libghostty-vt) | commit `f97cdfc3`, fetched with curl and `zig fetch` because Zig's HTTP client rejects GitHub's headers |
| Node | 24.19.0 (agent-memory needs 18 or later) |
| Python | 3.12.10 (asset-gate, dispatch and tests need 3.11 or later) |

Build:

```bash
. /c/Herdr-dev/toolchain/env.sh
cd /c/Herdr-dev/herdr
cargo zigbuild --release --target x86_64-pc-windows-gnu --locked
```

The binary is `target/x86_64-pc-windows-gnu/release/herdr.exe`. A clean release build took 16 min, an incremental
rebuild after a manifest change 3 min 50 s.

Lint, as `just check` runs it on Windows, for the GNU target:

```bash
cargo fmt --check
cargo-zigbuild clippy --all-targets --locked --target x86_64-pc-windows-gnu -- -D warnings
```

Tests, one process per test (the model `cargo nextest` uses; plain `cargo test` lets one failure poison shared
environment locks and cascade):

```bash
cargo-zigbuild test --target x86_64-pc-windows-gnu --locked --no-run --message-format json > artifacts.jsonl
python integrations/tools/run_isolated_tests.py artifacts.jsonl --sandbox-root <empty dir>
```

The runner points `XDG_*`, `APPDATA`, `LOCALAPPDATA`, `HOME` and `USERPROFILE` at the sandbox, because several Herdr
tests clear `XDG_*` and would otherwise write `herdr-dev` directories into the real profile. `TEMP` stays the real
temporary directory, because one test sets file ownership and needs a directory where the user holds WRITE_OWNER.

If `cargo-zigbuild.exe` is missing from the toolchain, re-extract it from the verified archive listed in
BOOTSTRAP.md.

## 4. Test results

All runs on 2026-10-24 on the research host.

### Herdr's own suites

| Suite | Result |
|---|---|
| Rust tests, 19 test binaries, one process per test, final sources (`493f3706`) | 3448 of 3449 pass; the one failure depends on the environment and passes with it corrected (below) |
| `cargo fmt --check` | pass |
| `cargo-zigbuild clippy --all-targets -D warnings` (GNU target) | pass, no warnings |
| Maintenance tests (`just test` Python modules) | 150 run: 145 pass, 5 skipped |
| `scripts/agent_detection_manifest_check.py --require-all-published` | pass |

The one environment-dependent Rust failure is
`windows_plugin_pane_commands_resolve_from_plugin_root_with_cwd_override`. The research shell sets
`NoDefaultCurrentDirectoryInExePath=1`, which stops `cmd /c slot.cmd` from resolving a batch file in the current
directory. That is correct Windows behaviour; the test passes with the variable unset.

### Detection fixtures (integration environment)

`integrations/detection-fixtures/test_fixtures.py` classifies five captured screens with `herdr agent explain --file`.

| Fixture | Expected | v0.9.5 | Candidate |
|---|---|---|---|
| Grok 1.0.67 trust dialog | blocked (visible blocker) | **idle** | blocked |
| Grok 1.0.67 idle after turn | idle | idle | idle |
| Codex 0.163 trust dialog | blocked | blocked | blocked |
| Codex 0.163 idle after turn | recorded only | idle | idle |
| Codex 0.163 rate-limit model picker | blocked (visible blocker) | **idle** | blocked |

### Integration components

| Suite | Result |
|---|---|
| agent-memory unit tests (`node --test`) | 41/41 |
| asset-gate unit tests | 18/18 |
| dispatch unit tests | 19/19 |
| harness unit tests | 8/8 |
| installer unit tests | 4/4 |

Backend suites start a disposable Herdr server in fresh config and state roots.

| Suite | v0.9.5 | Debug candidate | Final candidate |
|---|---|---|---|
| Plugin backend (link, capture, recall, unlink) | 19/19 | 19/19 | 19/19 |
| Plugin lifecycle backend (restart, kill, upgrade, rollback, uninstall of the plugin) | 23/23 | 23/23 | 23/23 |
| Dispatch backend (simulated plan, handoff into the vault) | 9/9 | 9/9 | 9/9 |
| Asset-gate backend (refusals before Herdr is called, approved link, approval log) | 12/12 | not run | 12/12 |
| Candidate lifecycle (section 5) | n/a | n/a | 22/22 |

The gate backend test refuses three installs before Herdr is called: no approval, a wrong digest, and the right
digest after a reviewed file was modified. It then links the unmodified plugin with the matching approval.

### Real agents on the candidate

Each run starts the agent through `herdr agent start` in an isolated named session with a throwaway repository, then
submits a read-only role prompt, reads the answer through Herdr, writes a handoff note, and checks that the memory
plugin captured the turn. A logged policy answers only folder-trust and read-only permission dialogs for the throwaway
repository, and dismisses model-switch suggestions with Esc. Any other dialog aborts the run.

| Agent | Build | Flags after `--` | Result | What the run showed |
|---|---|---|---|---|
| Grok Build 1.0.67 | 1 | `--no-subagents --disable-web-search --max-turns 3` | 11/13 | `agent start` reported ready on a blank screen; the trust dialog painted about 2 s later; `agent prompt` refused with `agent_blocked`. The validator had no retry yet |
| Grok Build 1.0.67 | 1 | same | 13/14 | trust dialog blocked during `agent start`; `agent prompt --wait` returned `agent_prompt_stalled` because Grok started its turn about 12 s later |
| Grok Build 1.0.67 | 1 | same | **14/14** | full pass, no manifest override |
| Codex 0.163.0-alpha.11.2 | 1 | `--sandbox read-only --no-daemon` | **14/14** | full pass; after the turn Codex opened the rate-limit model picker, which v0.9.5 and build 1 classify as idle |
| Claude Code 2.1.286 | 1 | `--model haiku --setting-sources project --disallowedTools Bash Edit Write NotebookEdit WebFetch WebSearch --strict-mcp-config` | 6/7, then abort | Herdr blocked the trust dialog correctly; the validator could not parse Claude's cursor list |
| Claude Code 2.1.286 | 1 | same | **14/14** | full pass |
| Codex 0.163.0-alpha.11.2 | 2 | `--sandbox read-only --no-daemon` | **14/14** | the rate-limit picker was detected live as blocked and dismissed with Esc; the model stayed unchanged |
| Codex 0.163.0-alpha.11.2, default daemon mode | 2 | `--sandbox read-only` | 5/7, aborted: **not usable** | the app-bundled CLI exits at once: "this CLI has no complete local package; install a packaged Codex CLI or use the standalone installer", and it suggests `--no-daemon`. No daemon was started or attached: the host's Codex processes were identical before and after. `agent start` still waited its full 120 s timeout, although Codex had exited within a second |
| Cursor | n/a | n/a | not run | `cursor-agent` is not installed on the host |

The Codex executable comes from the Codex desktop app's own package directory, and only that run's pane gets it on
its PATH. The package with the code-mode host and command runner is required; an earlier run with a bare `codex.exe`
reported its tool host as unavailable.

## 5. Installation, upgrade, rollback and uninstall

Steps 1 and 3 to 6 are what `tools/test_candidate_lifecycle.py` exercises end to end on one session. Step 2 is
exercised by `asset-gate/integration/test_gate_backend.py`. Neither touches a user installation: no PATH entry,
registry key, `%USERPROFILE%\.herdr` or existing Herdr profile is read or written.

1. **Install both builds side by side.** Each install directory gets the release zip layout (`herdr.exe`, `conpty/`,
   `THIRD-PARTY-NOTICES/`) and an `install-manifest.json` with the SHA-256 of every file. A staging directory is
   published by an atomic rename.

   ```bash
   python integrations/tools/candidate_install.py --root <env> install v0.9.5 --binary <release>/herdr.exe --reference-release <release>
   python integrations/tools/candidate_install.py --root <env> install candidate --binary target/x86_64-pc-windows-gnu/release/herdr.exe --reference-release <release> --activate
   ```

2. **Review and link the plugin.** Run the asset gate, read the report, then link only with an approval that names
   the exact report digest:

   ```bash
   cd integrations/asset-gate
   python -m asset_gate review-plugin ../agent-memory --json report.json
   python -m asset_gate review-plugin ../agent-memory --install --approve <report_sha256> --herdr-bin <abs herdr.exe> --herdr-session <session> --operator <name>
   ```

   The install command reviews the files again and refuses unless the fresh digest equals the approved one. Only then
   does it call Herdr's own `plugin link`. A `deny` result also needs `--override-deny <reason>`. Every attempt,
   refused or not, is appended to `approvals.jsonl` in the work directory.

3. **Upgrade.** Stop the server, `activate candidate`, start the server on the same session. Verified: the workspace
   is restored, the plugin stays linked, memories are intact, and the build that serves is proven by its
   classification of the Grok trust-dialog fixture.

4. **Abnormal termination.** Killing the server and starting it again restores the workspace. The plugin's
   `[[startup]]` hook runs `fsck` after restore, removes stale temporary files and writes `fsck-report.json`; the test
   checks that the report is newer than the kill.

5. **Rollback.** Stop the server and run `rollback`; the previous build is re-verified against its manifest before it
   becomes active. A modified install cannot be activated.

6. **Uninstall.** `plugin unlink research.agent-memory`, then `uninstall --all` removes the environment. Remove the
   session's config and state roots to remove Herdr state. The plugin vault lives in Herdr's plugin state directory and
   goes with them.

## 6. Compatibility and limitations

- **Artifact flavour.** The candidate is a GNU build (mingw-w64 CRT, different unwinding and static linking) of a
  project whose official Windows artifact is MSVC with a static CRT. It is for development and testing only. An MSVC
  build of the same commits was not produced.
- **Platforms.** Only Windows 11 was exercised. Linux and macOS builds and runs were not attempted. Cross-machine
  (SSH) operation was out of scope.
- **ConPTY.** Runs from the build directory use the system ConPTY, because the hash-verified app-local bundle is
  absent there. Installed builds carry the bundle and use it. Both configurations passed the backend suites.
- **Herdr version.** The plugin declares `min_herdr_version = "0.9.5"`. Its completed-turn signal relies on
  `completion_seq`, which resets in each server process and is keyed together with the terminal id, which Herdr
  reallocates on restore.
- **Agent versions.** Validated with Grok Build 1.0.67, Codex 0.163.0-alpha.11.2 and Claude Code 2.1.286. Every agent
  release can change its UI; the detection fixtures need a new capture per supported agent version. Cursor was not
  validated, because `cursor-agent` is not installed.
- **Codex modes.** The Codex CLI shipped inside the Codex desktop app works only with `--no-daemon`. Default daemon
  mode needs a packaged Codex CLI from the standalone installer, which this host does not have. When an agent exits
  during startup like this, `agent start` waits for its full `--timeout` instead of failing fast.
- **Readiness and stall windows.** `agent start` can report ready before an agent paints a startup dialog, and
  `agent prompt --wait` gives up after a fixed 5 s if no turn starts. Herdr stays safe in both cases: it refuses to
  type into a blocked agent and reports the stall. Callers must handle `agent_blocked` and `agent_prompt_stalled`.
  The dispatch executor waits with `agent wait` after a stall; it never retypes a prompt and never answers a dialog.
- **Simulated agents.** Herdr clears a self-reported agent once its pane's shell has no child process. Simulations
  therefore hold the pane with a short-lived Node process.
- **Plugin trust.** Herdr does not sandbox plugins. The integrations enforce their own allowlists in code and are only
  as trustworthy as the files on disk; see `SECURITY.md`.
- **Test environment.** Herdr's Rust tests need one process per test and a sandboxed profile; one test assumes
  `NoDefaultCurrentDirectoryInExePath` is unset.

## 7. Side effects outside the integration environment

The real-agent runs use each agent's existing login in the user's own home directory, as authorised. Nothing is copied
or edited by the harness, but the agents record their own state:

- Grok writes its session history and adds each throwaway path to `trusted_folders.toml`.
- Codex adds a project trust entry for each throwaway path to its `config.toml`, and writes session and history
  records. Other Codex sessions on the host were active at the same time, so the home-directory diff also contains
  their changes.
- Claude Code records the folder-trust answer for each throwaway path in its user configuration and appends to its
  history.

The trust entries name directories that were deleted after the runs. They were left in place, because removing them
means editing the agents' own configuration files.

## 8. Findings fixed in this round

1. **Codex shared picker misclassified (security).** Codex 0.163 can open its rate-limit model-switch picker after a
   completed turn. Herdr 0.9.5 classified it as idle, so the next `agent prompt` would have typed into it and Enter
   would have switched the model. Fixed in `codex.toml` 2026.10.24.1 and verified live.
2. **Simulation race.** Backend tests and the dispatch `--simulate` plan reported a custom agent right after an
   `echo`. Herdr clears that report once the shell is idle, so the tests failed on v0.9.5 too. Fixed with an occupant
   process.
3. **Late startup dialog.** Grok can paint its trust dialog after `agent start` reported ready. Herdr refused the
   prompt correctly. The validator now resolves the dialog under its policy and submits once more.
4. **Stalled prompt.** The dispatch executor treated `agent_prompt_stalled` as failure. It now waits for the turn to
   start, then for it to settle, using only allowlisted `agent wait` calls.
5. **Debug app directory.** Debug builds keep state under `herdr-dev`. The harness now resolves the directory the
   running server uses.
6. **Fixture placement.** The captured-screen check moved out of Herdr's own test suite (AGENTS.md).
7. **Corrupted test paths.** Two test strings contained control characters from an earlier edit; restored.

## 9. Upstream path and publication

Herdr's `CONTRIBUTING.md` does not accept implementation pull requests from people outside its approved-contributor
list, and the owner's GitHub account is not on it. This branch must therefore not be opened as a pull request against
`herdrdev/herdr`. The policy asks for a short, factual bug report instead, without root-cause analysis or patches.
Two reports are ready to file by the owner:

> **Grok Build 1.0.67 trust dialog is treated as idle.** Current: in a new directory, Grok Build 1.0.67 shows "Do you
> trust the contents of this directory?" and `herdr agent get` reports the agent as idle, so `herdr agent prompt`
> types into the dialog. Expected: blocked, and `agent prompt` refuses. Reproduction: `herdr agent start g --kind
> grok` in an untrusted directory, then `herdr agent prompt g "you may start"`. Effect: the prompt's first letter
> selects "Yes, proceed", so the prompt approves the trust dialog. Herdr 0.9.5 (stable), Windows 11, headless server
> driven through the CLI.

> **Codex rate-limit model picker is treated as idle.** Current: after a turn, Codex 0.163.0-alpha.11.2 can show
> "Approaching rate limits / Switch to … ?" with numbered choices and the footer "enter select · esc back", and Herdr
> reports idle. Expected: blocked, so `agent prompt` does not type into the picker. Reproduction: keep a Codex session
> near its usage limit, finish a turn, then run `herdr agent get <pane>`. Effect: the next prompt's Enter selects
> "Switch to …". Herdr 0.9.5 (stable), Windows 11.

The reviewable pull request for this branch has to live in a repository the owner controls. The evidence (this
document, `SECURITY.md`, test reports, build logs and sanitized real-agent records) is synchronized to the
`verifiable-ai-agent-lab` research track.
