# Herdr persistence, remote, security, testing (v0.9.5 @ 2ecf19a9)

Source: independent clone at `C:\Herdr-dev\herdr`, HEAD `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`, `git describe` = `v0.9.5`; changelog dates 0.9.5 at 2026-10-14 (`CHANGELOG.md:5`). Static reading only; no binaries, cargo, just, node or Python were executed. All paths below are relative to that clone. Tags: VERIFIED-IN-SOURCE (code read), DOC-ONLY (only docs/next or CHANGELOG say so), INFERRED (my conclusion from evidence, not stated directly).

## 1. Summary (10 bullets)

1. Session persistence is a JSON snapshot (`version: 3`) of workspaces/tabs/BSP layout/panes written atomically (tmp + fsync + rename + parent fsync) to `<data_dir>/session.json`, debounced 5 s, with checkpoints before signaled pane exits and on shutdown. VERIFIED-IN-SOURCE (`src/persist/io.rs:45-67`, `src/app/mod.rs:44`, `src/app/session.rs:14-130`).
2. Per pane it saves `cwd`, label, agent name, managed agent kind, a native agent session reference (`id` or absolute `path`), an agent-reported resume argv, and launch argv; on restore it spawns a shell and types `claude --resume <id>` / `codex resume <id>` / etc. followed by CR. Default on, 100 ms spacing. VERIFIED-IN-SOURCE (`src/persist/snapshot.rs:100-129`, `src/agent_resume.rs:199-312`, `src/app/agent_resume.rs:240-312`).
3. Directory names: release build uses `herdr`, debug build uses `herdr-dev` (`cfg!(debug_assertions)`). Config/session dir = `$XDG_CONFIG_HOME/<app>` else `%APPDATA%\<app>` (Windows) / `~/.config/<app>` (Unix). State dir = `$XDG_STATE_HOME/<app>` else `%LOCALAPPDATA%\<app>` / `~/.local/state/<app>`. VERIFIED-IN-SOURCE (`src/config/io.rs:22-94`).
4. There is no memory, knowledge-base, notes, journal or cross-agent learning feature. The only durable agent-related state is the per-pane session reference for native resume, optional pane screen history (`experimental.pane_history`), and agent-detection manifests. VERIFIED-IN-SOURCE (grep results; `src/config/model.rs:1077-1083`).
5. No MCP server or client exists in Herdr. "MCP" appears only in Claude/Qwen detection regexes, a Cursor hook-name cleanup, and test fixtures. VERIFIED-IN-SOURCE (`distribution/agent-detection/claude.toml:36-128`, `src/integration/targets.rs:1287-1294`, `src/detect/mod.rs:1408`).
6. Remote machines run plain OpenSSH (`ssh -C … -T <target>`) with `StrictHostKeyChecking=yes` always; Herdr never writes `~/.ssh/config`. With `remote.manage_ssh_config=true` (default) it writes a private temporary config that `Include`s the user/system configs and adds keepalives, plus (Unix only) a scoped ControlMaster socket. VERIFIED-IN-SOURCE (`src/remote/attach.rs:756-776, 1213-1250, 2940-2983`, `src/config/model.rs:1061-1072`).
7. Saved machines live in `<state_dir>/client/endpoints.json` (id, label, target, session, enabled; passwords in target rejected); "API forwarding" means `herdr --machine <id> <api cmd>` runs the API request through an SSH stdio bridge to `herdr --session <s> remote-api-bridge` on the host. Live handoff is `--handoff` opt-in, Unix-only, and documented as experimental. VERIFIED-IN-SOURCE (`src/client/endpoint/catalog.rs:18-68, 373-383`, `src/remote/saved.rs:43-111`, `src/remote/args.rs:54-58`, `src/platform/mod.rs:46-47`); DOC-ONLY for "experimental" wording (`docs/next/website/src/content/docs/connecting-machines.mdx:128`).
8. Authorization is purely OS-level: Unix sockets are chmod 0600; Windows named pipes get an SDDL DACL for SYSTEM + the account SID plus a mandatory integrity label (HI when the server is elevated unless `--allow-unelevated-clients` / `[server] allow_unelevated_clients`). There is no API token, no per-request authentication, and no audit log. VERIFIED-IN-SOURCE (`src/api/server.rs:29,305`, `src/platform/windows.rs:45-131`, `src/cli/server.rs:5-6`, `src/server/headless/bootstrap.rs:30-34`); INFERRED for "no further auth" (absence after grep).
9. Network by default (release builds): background version check against `https://herdr.dev/latest.json` (or `preview.json`; Homebrew installs query `formulae.brew.sh`) and agent-detection manifest check against `https://herdr.dev/agent-detection/index.toml`, both at app start and every 30 min via `curl`; disable with `[update] version_check = false` and `[update] manifest_check = false`. Debug builds never auto-check. VERIFIED-IN-SOURCE (`src/app/mod.rs:42, 181-186, 585-605`, `src/update.rs:25-27, 328-359`, `src/detect/manifest_update.rs:16-17, 497-556`).
10. Tests: `just test` = `cargo nextest` + Python `unittest` maintenance modules + Bun tests. Nearly all Rust integration tests are `#![cfg(unix)]`; only `tests/session_delete.rs` and `tests/windows_server_security.rs` run on Windows. Pure-Python modules (no Rust) are runnable with `python -m unittest scripts.test_<x>` from the repo root; CI on Windows runs `just check` (fmt, clippy, `just test`, build) plus ConPTY smoke/packaging scripts. VERIFIED-IN-SOURCE (`justfile:7-17`, `.github/workflows/ci.yml:51-66, 190-203`, `scripts/windows_check.ps1:32-47`, cfg gates listed in §8).

## 2. Session persistence and restore

### 2.1 Where files live (exact names)

Resolution (VERIFIED-IN-SOURCE, `src/config/io.rs:22-94`):

- `app_dir_name()` = `"herdr-dev"` when `cfg!(debug_assertions)`, else `"herdr"` (`src/config/io.rs:22-28`).
- `config_dir()` = `$XDG_CONFIG_HOME/<app>` if set (all platforms, including Windows); else Windows `%APPDATA%\<app>` → `%USERPROFILE%\AppData\Roaming\<app>` → `$HOME/.config/<app>` → `%TEMP%\<app>`; Unix `$HOME/.config/<app>` → temp (`io.rs:30-68`).
- `state_dir()` = `$XDG_STATE_HOME/<app>` if set; else Windows `%LOCALAPPDATA%\<app>` → `%USERPROFILE%\AppData\Local\<app>` → `$HOME/.local/state/<app>` → `%TEMP%\<app>-state`; Unix `$HOME/.local/state/<app>` (`io.rs:37-94`).
- `config_path()` = `$HERDR_CONFIG_PATH` or `config_dir()/config.toml` (`io.rs:195-200`; constant at `src/config.rs:56`).
- Session data dir: default session = `config_dir()`; named session (`--session <name>` / `HERDR_SESSION`) = `config_dir()/sessions/<name>` (`src/session.rs:10-11, 159-169`). API socket `herdr.sock`, client socket `herdr-client.sock` inside it (`session.rs:171-187`). `HERDR_SOCKET_PATH` overrides the API socket path (`src/api/mod.rs:20`, `session.rs:175-183`).

Concrete layout, release build on Windows (debug: replace `herdr` by `herdr-dev`; Unix: `~/.config/herdr` and `~/.local/state/herdr`):

| Path | Content | Evidence |
|---|---|---|
| `%APPDATA%\herdr\config.toml` | user config | `src/config/io.rs:195-200` |
| `%APPDATA%\herdr\session.json` | layout snapshot | `src/persist/io.rs:11-13` |
| `%APPDATA%\herdr\session-history.json` | pane screen history (only with `experimental.pane_history`) | `src/persist/io.rs:15-17`, `src/persist/writer.rs:54-57` |
| `%APPDATA%\herdr\session-backups\` | up to 3 copies of unreadable/newer session files | `src/persist/writer.rs:122-124` |
| `%APPDATA%\herdr\session-snapshots\` | up to 48 layout snapshots, ≥15 min apart | `src/persist/writer.rs:78-120` |
| `%APPDATA%\herdr\plugins.json` | installed plugin registry | `src/persist.rs:5` |
| `%APPDATA%\herdr\herdr.sock`, `herdr-client.sock` | API / client endpoints (Windows: marker file; real endpoint is `\\.\pipe\<path>`) | `src/session.rs:171-187`, `src/ipc.rs:66-80`, `src/platform/windows.rs:35` |
| `%APPDATA%\herdr\herdr.log`, `herdr-client.log`, `herdr-server.log` | rotating tracing logs, filter `HERDR_LOG` | `src/logging.rs:12-37` |
| `%APPDATA%\herdr\sessions\<name>\…` | same files per named session | `src/session.rs:163-169` |
| `%APPDATA%\herdr\agent-detection\<agent>.toml` | local detection manifest overrides | `src/detect/manifest.rs:1119-1125` |
| `%LOCALAPPDATA%\herdr\agent-detection\` | downloaded remote manifest cache + status | `src/detect/manifest_update.rs:497-499` |
| `%LOCALAPPDATA%\herdr\client\endpoints.json`, `endpoint-selection.json` | saved SSH machines | `src/client/endpoint/catalog.rs:373-383` |
| `%LOCALAPPDATA%\herdr\client\ssh-metadata\<id>.json` | cached remote OS + executable path | `src/client/endpoint/ssh_metadata.rs:50-60` |
| `%LOCALAPPDATA%\herdr\client-shell\local-*.json`, `remote-*.json` | client UI preferences | `src/client/shell/preferences.rs:33-55` |
| `%LOCALAPPDATA%\herdr\plugins\<id>\` | plugin state | `src/plugin_paths.rs:49-53` |
| `%LOCALAPPDATA%\herdr\product-announcements.json` | seen announcements | `src/product_announcements.rs:8, 77-78` |
| `%LOCALAPPDATA%\herdr\remote\` | Windows-only private dir for SSH bridge pipes and temp ssh configs | `src/platform/windows.rs:719-734, 789-795` |

Integration tests confirm the names: `config_home/herdr-dev/session.json` (`tests/api_ping.rs:459`), `herdr-dev/sessions/shutdown/herdr.sock` (`tests/host_shutdown.rs:124`), `herdr-dev/plugins.json` (`tests/cli/plugins.rs:673`). VERIFIED-IN-SOURCE.

### 2.2 Save format and atomic write

- `SNAPSHOT_VERSION = 3` (`src/persist/snapshot.rs:12`). `SessionSnapshot { version, workspaces, active, selected, sidebar_width, sidebar_section_split, collapsed_space_keys }` (`snapshot.rs:16-29`); `WorkspaceSnapshot { id, custom_name, identity_cwd, worktree_space, public_pane_numbers, next_public_pane_number, public_tab_numbers, next_public_tab_number, tabs, active_tab }` (`snapshot.rs:52-71`); `TabSnapshot { custom_name, layout (BSP Pane|Split{direction,ratio,first,second}), panes, zoomed, focused, root_pane }` (`snapshot.rs:87-97, 139-153`). Legacy pre-tab layout is migrated (`snapshot.rs:73-84, 155-`). VERIFIED-IN-SOURCE.
- `PaneSnapshot { cwd, label?, agent_name?, managed_agent_kind?, agent_session?: {source, agent, kind: id|path, value}, agent_resume?: {source, agent, argv}, launch_argv? }` (`snapshot.rs:100-129`; kind enum `src/agent_resume.rs:16-21`). Pane screen content is never in `session.json`; history goes to `session-history.json` (`src/persist/io.rs:222-234` test asserts this). VERIFIED-IN-SOURCE.
- Atomic write: resolve symlinks manually (handles dangling stow links), `create_dir_all`, write `<file>.json.tmp`, `sync_all`, `platform::replace_file` (Unix `rename`; Windows `MOVEFILE_WRITE_THROUGH`), then fsync parent dir on Unix (`src/persist/io.rs:19-67`, `src/platform/client_state.rs:13-32`). A locked destination on Windows leaves the old file intact and removes the tmp (`io.rs:236-280` test). VERIFIED-IN-SOURCE.
- Load: missing → info; newer `version` → ignored with warning; parse error → ignored (`io.rs:94-133`). Before the first overwrite of an unloadable file the writer copies it to `session-backups/` (keep 3) (`src/persist/writer.rs:22-27, 122-124`). VERIFIED-IN-SOURCE; behavior also documented at `docs/next/website/src/content/docs/session-state.mdx:39-53` (DOC-ONLY for the manual recovery procedure).

### 2.3 When saves happen

- `SESSION_SAVE_DEBOUNCE = 5 s` (`src/app/mod.rs:44`); dirty state schedules a background save thread `herdr-session-save`; a second request while one is running re-arms at +250 ms (`src/app/session.rs:14-88`). `save_session_now` on shutdown (`session.rs:90-129`); the headless server calls `save_session_on_shutdown()` after the loop exits if `policy.persist_session` (`src/server/headless.rs:696-699`). VERIFIED-IN-SOURCE.
- Pane exits classified `Interrupted` (Windows `0xC000013A`; Unix signal) or `Handoff` trigger `checkpoint_session_before_pane_exit()` before the exit is applied, so a shutdown-time kill cannot replace the layout with an empty one (`src/app/api.rs:270-279`, `src/platform/mod.rs:161-168`, `src/platform/windows.rs:162-169`). VERIFIED-IN-SOURCE.
- `AppPolicy::PRODUCTION { restore_session: true, persist_session: true, persist_plugin_registry: true, background_updates: true }`; `HANDOFF_REPLACEMENT` has `restore_session: false` (it imports live panes instead) (`src/app/mod.rs:72-103`). VERIFIED-IN-SOURCE.

### 2.4 Restore and native agent resume

- On start, `policy.restore_session.then(persist::load)` (`src/app/mod.rs:404`); `persist::restore(...)` rebuilds workspaces (`src/persist/restore.rs:66-95`); `restore_handoff` (Unix) merges imported live panes (`restore.rs:96-`). VERIFIED-IN-SOURCE.
- For each pane with a saved `agent_session`/`agent_resume`, `pane_restore_startup` computes an `AgentResumePlan` only when `session.resume_agents_on_restore` is true and the (source, agent) pair is official; duplicate session refs across panes are resumed once (`restore.rs:535-575, 883-919`). The plan is stored on the terminal as `pending_agent_resume_plan` (`restore.rs:594-604`, `src/terminal/state.rs:163, 304-308`). VERIFIED-IN-SOURCE.
- Execution (`src/app/agent_resume.rs:48-97, 240-312`): candidates are started one at a time with `startup_per_agent_delay_ms` spacing (default 100; 0 disables) after host theme is known; Herdr spawns the pane's normal shell (`TerminalRuntime::spawn`) in the saved `cwd` and writes the shell-quoted command plus `\r` to the PTY (`shell_command_from_argv`, `agent_resume.rs:356-380`). If the cwd is missing or the shell fails, `restore_error` is set on the pane instead. VERIFIED-IN-SOURCE. Docs: `configuration.mdx:557-561`.
- Resume argv per agent (`src/agent_resume.rs:204-312`): `claude --resume <id>`; `codex resume <id>`; `copilot --resume=<id>`; `devin|droid|qodercli|qwen|grok|hermes --resume <id>`; `kimi|pi|opencode|kilo --session <id|path>`; `mastracode --thread <id>`; `omp --resume=<id|path>`; `cursor-agent[.cmd] --resume <id>`; `agy --conversation <id>`; `letta --conversation <id>` or `--conversation default --agent <id>`. Official sources are `herdr:<agent>` (`agent_resume.rs:328-350`). Gemini, Amp, Cline, Kiro, Maki, Muse, Antigravity IDE have no resume plan. VERIFIED-IN-SOURCE.
- Validation: session ids ≤512 chars, no control chars; paths absolute ≤4096 (`agent_resume.rs:352-361`); agent-reported resume argv must start with a bare command name, ≤64 args, ≤8192 bytes, no control chars or apostrophes (`agent_resume.rs:56-89`). VERIFIED-IN-SOURCE.
- Where session ids come from: Herdr-installed agent hooks (e.g. `src/integration/assets/claude/herdr-agent-state.sh:1-40`, `.ps1:1-40`) run on `SessionStart` only inside Herdr panes (`HERDR_ENV=1`, `HERDR_PANE_ID`) and call `herdr pane report-agent-session <pane> --source herdr:claude --agent … --agent-session-id <id>` (`src/cli/pane.rs:1297-1298, 1402-1403`). Explicit `codex resume <id>` launches are also persisted from argv (`agent_resume.rs:135-151`). VERIFIED-IN-SOURCE.
- Config keys: `[session] resume_agents_on_restore = true`, `startup_per_agent_delay_ms = 100` (`src/config/model.rs:267-282`); `[experimental] pane_history = false` (`model.rs:1077-1083`, wired at `src/app/mod.rs:668`). VERIFIED-IN-SOURCE.

### 2.5 Related tests

- `tests/session_restore.rs:57` `server_restores_while_git_metadata_is_blocked` (unix; writes a v3 snapshot with `identity_cwd` + blocked `.git/config` FIFO, expects API readiness).
- `tests/session_delete.rs:80-169` (no cfg gate → runs on Windows): exact-name delete, case-sensitivity, running-session refusal, idempotence.
- `tests/host_shutdown.rs:110` `host_shutdown_saves_layout_before_releasing_delay_lock` (Linux only; private D-Bus `login1` mock).
- `tests/detach_reattach.rs:286-744` (unix): detach/reattach, processes survive, `server_persists_after_client_connection_drop` (522-575), headless size, output accumulated while detached.
VERIFIED-IN-SOURCE (function names at those lines).

## 3. Memory/knowledge features (what exists; what does not)

- Grep of `src/**/*.rs` for `knowledge`, `instinct`, `journal`, `notebook`, `cross-agent`, `shared context`: 0 hits each. `memory` (20 hits) are Win32 memory APIs/comments (`src/platform/windows.rs:487-2708`), `transcript` (18) is terminal scrollback matching in `src/terminal/history_read.rs:75-436`, `learn` (1) is a comment about a terminal probe (`src/client/terminal_setup.rs:165`). VERIFIED-IN-SOURCE.
- What exists:
  - Per-pane native agent session reference + resume (section 2.4). VERIFIED-IN-SOURCE.
  - Optional pane screen history replay (`experimental.pane_history`, `session-history.json`); docs say to treat it like shell history (`session-state.mdx:66-69`). VERIFIED-IN-SOURCE / DOC-ONLY.
  - Pane text read API used by tests (`pane_read_recent`, `tests/detach_reattach.rs:191-207`) — a read of live screen, not a store. VERIFIED-IN-SOURCE.
  - Agent-detection manifests (bundled, remote-updated, locally overridable) — rules for state detection, not knowledge about the user's work (`src/detect/manifest_update.rs`, `src/detect/manifest.rs:1119-1125`). VERIFIED-IN-SOURCE.
  - Transient pane-to-pane messaging exists (docs list "pane-to-pane messages" among things interrupted by handoff, `session-state.mdx:123`); it is not persisted. DOC-ONLY/INFERRED.
- What does not exist: any cross-agent memory, learned patterns, notes/journal, knowledge base, or transcript archive. INFERRED from the greps above.

## 4. Remote SSH machines, API forwarding, handoff

### 4.1 Explicit remote attach (`herdr --remote <target>`)

- Flags: `--remote <target>` (not starting with `-`), `--remote-keybindings local|server`, `--handoff` (`src/remote/args.rs:35-127`). Env: `HERDR_REMOTE_PREFERENCES_IDENTITY`, `HERDR_REATTACH_COMMAND`, `HERDR_REMOTE_KEYBINDINGS` (`args.rs:1-3`); `HERDR_REMOTE_BINARY` supplies a local binary/package for install (docs `persistence-remote.mdx:99-102`; env name in `src/remote/attach.rs:2530`). VERIFIED-IN-SOURCE.
- `run_remote` loads `remote.manage_ssh_config`, builds `RemoteSsh`, prepares/installs remote Herdr, ensures the remote server is ready, then starts an SSH stdio bridge (`attach.rs:41-70`). VERIFIED-IN-SOURCE.
- SSH command (VERIFIED-IN-SOURCE): program `ssh`, always `-C` (`attach.rs:1230-1232`); with managed config `-F <tmp>/config` and, on Unix, `-S <ctl> -o ControlMaster=auto -o ControlPersist=600` (`1235-1250`); non-interactive variants add `-o BatchMode=yes -o NumberOfPasswordPrompts=0 -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o ServerAliveInterval=15 -o ServerAliveCountMax=4` (`1213-1227`); then `-T <target>` (`838-849`). Interactive authentication helper runs `ssh … -o BatchMode=no -o StrictHostKeyChecking=yes -o NumberOfPasswordPrompts=3 -T <target> exit` with `SSH_ASKPASS_REQUIRE=never` (`attach.rs:756-776`); `scp` is used for binary copy with the same options (`attach.rs:851-854, 1253-1270`).
- Remote-side command: `<herdr> --session <name> remote-client-bridge [--idle-timeout-v1]` (`attach.rs:397-425`); on the host it starts the server daemon if needed and forwards stdio to `herdr-client.sock` (`src/remote/host.rs:6-63`); `--idle-timeout-v1` enables idle cleanup after ~1 min (docs `connecting-machines.mdx:94`). VERIFIED-IN-SOURCE / DOC-ONLY for the minute.
- Host keys: `StrictHostKeyChecking=yes` in every spawned ssh; "Host key verification failed"/"REMOTE HOST IDENTIFICATION HAS CHANGED" are surfaced with a hint to add the key to known_hosts (`src/remote.rs:41-67`); saved machines classify it as needs-attention (`src/remote/saved.rs:121-146`). Herdr never adds `UserKnownHostsFile` or disables checking (no such option in grep of `attach.rs`). VERIFIED-IN-SOURCE.

### 4.2 Managed SSH config (does Herdr write `~/.ssh/config`?)

- No. `write_managed_ssh_config` creates a **private temporary** directory and `config` file: Unix `$TMPDIR/herdr-ssh-<pid>-<n>/config` (dir 0700, file 0600, `src/platform/unix_common.rs:356-411`); Windows `%LOCALAPPDATA%\herdr\remote\ssh-<pid>-<n>\config` in a directory with SDDL `D:P(A;OICI;GA;;;SY)(A;OICI;GA;;;OW)` (`src/platform/windows.rs:719-765, 789-791`). Contents: `Include "<~/.ssh/config>"` (Windows literally `~/.ssh/config`), `Include "/etc/ssh/ssh_config"` or `%PROGRAMDATA%\ssh\ssh_config` when present, then `Host *` / `ServerAliveInterval 15` / `ServerAliveCountMax 4` (`src/remote/attach.rs:2904-2983`). User settings win because they are included first (`attach.rs:2938-2939`). VERIFIED-IN-SOURCE.
- Unix control socket: `/tmp/hssh-<euid>/…` validated (parent root-owned sticky, dir 0700, no symlink, owner uid) (`unix_common.rs:608-640, 669`); Windows has `multiplexing: false` (`windows.rs:707-717`). VERIFIED-IN-SOURCE.
- Disable: `[remote] manage_ssh_config = false` → plain `ssh` without `-F`/`-S` (`src/config/model.rs:1061-1072`; `attach.rs:786-803`). Interactive SSH recovery (`herdr machine reconnect`) requires it to be true and Unix multiplexing (`attach.rs:730-752`). Docs: `persistence-remote.mdx:78`, `configuration.mdx:119-122`. VERIFIED-IN-SOURCE.
- ssh-agent: on Unix the host-side bridge registers an agent address for panes (`host.rs:23-24`, `src/remote/ssh_agent.rs`); Herdr does not turn on `ForwardAgent` (docs `connecting-machines.mdx:106-108`). VERIFIED-IN-SOURCE / DOC-ONLY.

### 4.3 Remote install/update of Herdr

- If no compatible `herdr` is found on the host, interactive runs offer to copy the local binary (matching platform) or download the release asset: stable builds fetch `https://herdr.dev/latest.json` and pick the asset for the *current client version*; preview builds fetch `https://herdr.dev/preview.json` by build id; download uses `curl -sfL --max-time 120` on the **local** machine and verifies SHA-256 when the manifest provides one (`src/remote/attach.rs:33-34, 2446-2470, 2517-2560`). Non-interactive/background paths never install (docs `persistence-remote.mdx:76`, `connecting-machines.mdx:98`). VERIFIED-IN-SOURCE / DOC-ONLY.
- Replacement policy: a running server is kept unless it predates endpoint-protocol generation 1, lacks surface-interest/health-check (saved machines), or is not a detached daemon; otherwise stop (default answer No) or `--handoff` (`src/remote/restart_policy.rs:16-62`; `tests/support/mod.rs:19` `CURRENT_ENDPOINT_PROTOCOL_GENERATION = 1`). VERIFIED-IN-SOURCE.

### 4.4 Saved machines (`herdr machine …`)

- Subcommands: `list [--json]`, `status [<label-or-id>] [--json]`, `reconnect <label-or-id>` (interactive terminal only), `add <ssh-target> [--label] [--remote-session <name>]`, `rename <id> --label`, `remove <id>`, `enable <id>`, `disable <id>` (`src/cli/machine.rs:11-18, 194`). VERIFIED-IN-SOURCE.
- Storage: `<state_dir>/client/endpoints.json` (`{version:1, selected_profile?, ssh:[{id, label, target, session, enabled}]}`) and `endpoint-selection.json` (`src/client/endpoint/catalog.rs:10-16, 18-26, 76-98, 373-383`). Limits: 64 profiles, 64 KiB file, label ≤128 B, target ≤1024 B, `user:password@` targets rejected, session name validated (`catalog.rs:10-16, 44-68`). Writes go through `store_private_json` (size check, refuses symlink/non-file, tmp + `sync_all` + rename; file created via `create_private_state_file` = 0600 on Unix, `create_new` on Windows) (`catalog.rs:334-364`, `src/platform/client_state.rs:3-11`). VERIFIED-IN-SOURCE.
- Metadata cache: `<state_dir>/client/ssh-metadata/<id>.json` with `{os, executable}` validated per OS (`src/client/endpoint/ssh_metadata.rs:10-60`). Docs: profiles hold no passwords/keys/tickets (`connecting-machines.mdx:120-122`). VERIFIED-IN-SOURCE / DOC-ONLY.
- Bridge sockets are named by profile id, never target/session (`src/remote/saved.rs:148-153, 182-188`). VERIFIED-IN-SOURCE.

### 4.5 "API forwarding" (`herdr --machine <label-or-id> <api command>`)

- Global option `--machine LABEL-OR-ID` "Run an API command on a saved SSH machine" (`src/cli/spec.rs:15`). `SavedSshApiBridge::start` resolves/validates the profile, uses or discovers remote metadata, then runs over SSH `<remote herdr> --session <s> remote-api-bridge` guarded by a `--check` that must print `herdr-api-bridge-v1`, otherwise exits 78 with a stale-metadata marker so the client rediscovers before any mutation (`src/remote/saved.rs:43-111`, `src/remote/attach.rs:2666-2716`, `src/remote.rs:15-39`). On the host `remote-api-bridge` connects to the session's `herdr.sock` and relays stdio (`remote.rs:15-29`). Tests: `tests/machine_api.rs:224-639` (never replays a lost mutation, protocol mismatch never sends, status reports remote identity). VERIFIED-IN-SOURCE.

### 4.6 Live handoff

- Opt-in via `--handoff` on `herdr --remote` and `herdr update` (`src/remote/args.rs:54-58`, `src/update.rs:1115`); applied only if the running server advertises the capability and a restart is otherwise required (`restart_policy.rs:39-62`, `attach.rs:2273`). Unix only: `persist::restore_handoff` is `cfg(unix)` (`src/persist.rs:16-17`), platform comment "Windows has no live handoff" (`src/platform/mod.rs:46-47`), `tests/live_handoff.rs:1` `#![cfg(unix)]`, CI excludes it on macOS (`.github/workflows/ci.yml:62`). Mechanism: old server pauses PTY readers, captures a snapshot, passes PTY fds in batches of 64 over a 0600 Unix socket, 30 s ready/commit timeouts (`src/server/headless/lifecycle.rs:57-100`, `src/server/handoff.rs:20-33, 329-333`). VERIFIED-IN-SOURCE.
- "Experimental": the code has no `experimental.*` config gate for handoff; the label comes from docs/changelog ("Live handoff is experimental and opt-in", `connecting-machines.mdx:128`, `session-state.mdx:127-131`; `distribution/latest.json:79`). DOC-ONLY.

## 5. MCP

- Herdr neither exposes nor consumes MCP servers. Total "mcp" hits across `src/`, `docs/next`, `skills/`, `README.md`, `AGENTS.md`, `distribution/`: 21, all of them: Claude Code detection regexes for "MCP tasks still running" and "MCP server … requests your input" (`distribution/agent-detection/claude.toml:36-43, 118-128`), Qwen approval text (`qwen.toml:59`), removal of a legacy Cursor `beforeMCPExecution` hook entry when (re)installing Herdr's Cursor hooks (`src/integration/targets.rs:1287-1294`), test fixtures (`src/detect/mod.rs:1408, 1424`, `src/platform/windows.rs:5065, 5083`), and changelog prose. No `Cargo.toml` dependency and no docs page mention MCP. VERIFIED-IN-SOURCE.

## 6. Permissions and security model

- Transport ACLs (VERIFIED-IN-SOURCE):
  - Unix: API socket and client socket restricted to 0600 after bind (`src/api/server.rs:29, 305`, `src/server/socket_paths.rs:12, 72`, `src/ipc.rs:331-336`); handoff socket 0600 (`src/server/handoff.rs:329-333`); clipboard image staging 0600/0700 (`src/server/clipboard_image.rs:100-110`).
  - Windows: both listeners are named pipes created with `local_server_security_descriptor()` = `D:P(A;;GA;;;SY)(A;;GRGW;;;<account SID>)S:(ML;;NRNW;;;HI|ME)`; the integrity label is `HI` when the server token is elevated and `ME` otherwise or when unelevated clients are allowed (`src/ipc.rs:66-80`, `src/platform/windows.rs:45-131`). Bridge/private listeners use their own SDDL (`src/ipc.rs:138-160`). A permission-denied connect prints guidance to restart with `--allow-unelevated-clients` (`windows.rs:133-145`).
  - Elevation consent: `herdr server --allow-unelevated-clients` (`src/cli/server.rs:5-6, 268`) or `[server] allow_unelevated_clients = true` (default false; `src/config/model.rs:1041-1045`, applied in `src/server/headless/bootstrap.rs:30-34`). Test `tests/windows_server_security.rs:49-` spawns `herdr --session integrity-test server` with `XDG_CONFIG_HOME`/`XDG_STATE_HOME` set, creates a LUA restricted token and low/medium integrity tokens, and checks both endpoints for each (config, flag) combination; consent is process-local.
- Client validation beyond the ACL: none found. `src/api/server.rs` has no token/auth handling (grep hits only `pane.clear_agent_authority` and a test map). `HERDR_ENV=1` is an environment marker injected into pane processes for nested-launch blocking (`src/main.rs:3-4, 453-457`, `src/pane.rs:202`), not a credential. Any process able to open the socket/pipe can issue every API method, including `server.stop`. INFERRED (absence).
- Git trust: worktree API params carry `trust_repository: bool` (`src/api/schema/worktrees.rs:10-57`); when set, git is invoked as `git -c safe.directory=<repo_root> -C <repo_root> …` for that request only (`src/worktree.rs:154-170`); CLI flag `--trust-repository` (changelog `distribution/latest.json:79`). VERIFIED-IN-SOURCE / DOC-ONLY for flag name.
- Input hardening relevant to restore: resume argv/session-ref validation (§2.4); `ssh` targets must not start with `-` (`src/remote/args.rs:119-127`); SSH target with embedded password rejected (`catalog.rs:62-68`); profile ids must be 32 hex (`saved.rs:162-175`). VERIFIED-IN-SOURCE.
- Audit log: none. The only "audit" hits are a Win32 comment and a Kitty graphics field (`src/platform/windows.rs:427`, `src/server/clients.rs:146`). Operational logs are structured `tracing` events in `herdr*.log` with `HERDR_LOG` filtering (`src/logging.rs:12-37`); events like `persist.restore`, `persist.snapshot` are emitted (`src/persist/io.rs:99-131`, `writer.rs:31-34`). VERIFIED-IN-SOURCE.
- Secrets: Herdr does not copy local plugins, config, executables or secrets to SSH hosts (docs `connecting-machines.mdx:112`). DOC-ONLY.

## 7. Network activity by default and how to disable

Conditions: all checks run only when `AppPolicy.background_updates` is true and the build is not a debug build (`src/app/mod.rs:181-186`); they are spawned in `App::new` (`src/app/mod.rs:585-605`) and re-run every `AUTO_UPDATE_CHECK_INTERVAL = 30 min` (`src/app/mod.rs:42, 645-648`). The headless server constructs the `App`, so the server process performs them (INFERRED from `src/server/headless.rs` owning `self.app`). HTTP is done by spawning `curl` (`src/update.rs:6`, `src/noninteractive_process`).

| Feature | Default | Config key / flag to disable | Evidence |
|---|---|---|---|
| Version check: `https://herdr.dev/latest.json` (stable) or `https://herdr.dev/preview.json` (preview channel); `curl -sfL --retry 3 --connect-timeout 10 --max-time 20` | On (release builds) | `[update] version_check = false` | `src/update.rs:25-26, 328-359, 2348-2420`; `src/app/mod.rs:585-597`; `src/config/model.rs:33-45` (VERIFIED-IN-SOURCE); `CHANGELOG.md:580` |
| Homebrew installs instead query `https://formulae.brew.sh/api/formula/herdr.json` | On when brew-managed | same key | `src/update.rs:27, 579-600, 2372-2380` (VERIFIED-IN-SOURCE) |
| Agent-detection manifest check: `https://herdr.dev/agent-detection/index.toml` plus per-agent files relative to it; `curl … --max-filesize 262144`; cache in `<state_dir>/agent-detection` | On (release builds) | `[update] manifest_check = false`; URL override env `HERDR_AGENT_DETECTION_MANIFEST_CATALOG_URL`; local override `<config_dir>/agent-detection/<agent>.toml` | `src/detect/manifest_update.rs:16-18, 497-556`; `src/detect/manifest.rs:1119-1125`; `src/app/mod.rs:599-605`; docs `agents.mdx:86-92` (VERIFIED-IN-SOURCE) |
| Update channel | `stable`; `preview` only for Windows preview builds | `[update] channel = "stable"` | `src/config/model.rs:14-57` (VERIFIED-IN-SOURCE) |
| Product announcements | Derived from the update manifest, no separate request | covered by `version_check` | `src/update.rs:378`, `src/product_announcements.rs:77-78` (VERIFIED-IN-SOURCE) |
| `herdr update` (manual): downloads the asset URL from the manifest, SHA-256 mandatory for stable assets | Off until invoked | n/a (do not run it) | `src/update.rs:400-420, 640-665` (VERIFIED-IN-SOURCE) |
| Remote install over SSH: fetches `latest.json`/`preview.json` and the asset locally when the host lacks a compatible Herdr | Only during interactive `--remote`/`machine add` after confirmation | set `HERDR_REMOTE_BINARY`, or pre-install on the host; background reconnects never install | `src/remote/attach.rs:33-34, 2446-2470, 2517-2560`; docs `persistence-remote.mdx:76, 97-102` (VERIFIED-IN-SOURCE / DOC-ONLY) |
| SSH to saved machines (background reconnects with backoff up to 2 min) | Only for profiles with `enabled: true` | `herdr machine disable <id>` / `remove <id>`; `remote.manage_ssh_config=false` removes managed config only | `src/client/endpoint/catalog.rs:18-26`; docs `connecting-machines.mdx:90` (VERIFIED-IN-SOURCE / DOC-ONLY) |
| Debug (`herdr-dev`) builds | Never auto-check | n/a | `src/app/mod.rs:181-182` (VERIFIED-IN-SOURCE) |

No other outbound network code was found in `src/` (the only URL constants are the five above plus test `example.com` strings). INFERRED from grep of `https://` in `src/update.rs`, `src/remote/attach.rs`, `src/detect/manifest_update.rs`.

## 8. Testing infrastructure and what runs without Rust

### 8.1 justfile recipes (`justfile`, VERIFIED-IN-SOURCE)

- `test` (7-12): `cargo nextest run --locked …` then `maintenance-test`, `ui-hot-path-architecture-test`, `integration-assets-test`, `docs-contract-test`.
- `maintenance-test` (15-17): `python -m unittest scripts.test_agent_detection_manifest_check scripts.test_changelog scripts.test_config_reference_check scripts.test_docs_translation_parity scripts.test_hermes_integration_asset scripts.test_package_windows_conpty scripts.test_preview scripts.test_release scripts.test_unix_installer scripts.test_vendor_libghostty_vt scripts.test_vendor_portable_pty scripts.test_windows_cross scripts.test_windows_input` + `bun test scripts/release-workflows.test.ts` (`python` on Windows, `python3` elsewhere, line 4).
- `test-one <filter>` (25-26); `ui-hot-path-architecture-test` (29-30, Python); `lint` (33-41: fmt + clippy, Windows via `scripts/windows_check.ps1 -Mode lint`); `ci` / `ci-tests` (44-52); `setup-windows-cross`, `windows-lint` (56-62, xwin cross-check from Unix); `check` (66-73: Unix = ci + windows-lint + docs-contract-test; Windows = `windows_check.ps1 -Mode check` = fmt, clippy, `just test`, `cargo build --locked`, `scripts/windows_check.ps1:32-47`).
- `build` (84-89; Windows uses `scripts/package_windows_conpty.py build-local`).
- Benches (92-119): `bench-render-scale`, `bench-terminal-targets`, `bench-process-inspection` (windows), `bench-bsp-layout`, `bench-retained-graphics`, `bench-api-fairness` — all `cargo test --release … -- --ignored`; `bench-release-smoke` builds release and runs `scripts/release_perf_smoke.sh` (downloads stable baseline unless `HERDR_PERF_BASELINE_BIN`).
- `docs-contract-test` (122-123, `bun test ./scripts/docs`); `integration-assets-test` (126-129, three Bun test files under `src/integration/assets`).
- Release: `release-docs-check` (140-175), `pre-release-check` (178-184), `preview` (187-195, pushes `preview-<date>-<sha>` tag), `release-prepare` / `release-publish` / `release` (198-258), `default-config` (261-262).

### 8.2 CI (`.github/workflows/ci.yml`, VERIFIED-IN-SOURCE)

- Toolchain pins: Rust 1.96.1 (13), Bun 1.3.14 (96), Zig 0.16.0 (104-111), `just` + `cargo-nextest` (88-91).
- Matrix (51-66): ubuntu `all()`, macOS `not binary(live_handoff)`, windows. Linux: `just lint` + `just ci-tests` + a scalar-libghostty nextest pass (171-188); macOS: `just ci`; Windows: `just check` (190-195) then `scripts/windows_smoke_conpty_path.ps1` against `target\debug\herdr.exe` (197-203).
- `windows-conpty-package` job (220-357): builds for `x86_64-pc-windows-msvc`, verifies a tampered app-local ConPTY bundle is rejected and `HERDR_WINDOWS_CONPTY=system` recovers, packages via `scripts/package_windows_conpty.ps1`, probes enhanced input, and tests the installer under Windows PowerShell 5.1.
- Other workflows exist (`pr-gate.yml`, `release.yml`, `preview.yml`, `distribution.yml`, `nix.yml`, `windows-arm64.yml`, `website-deploy.yml`) — not read.

### 8.3 Integration test harness

- `tests/cli.rs:1` is `#![cfg(all(unix, not(target_os = "macos")))]`; cfg gates: `api_ping`, `broken_pipe`, `client_mode`, `cross_area`, `detach_reattach`, `live_handoff`, `machine_setup`, `multi_client`, `remote_attach`, `server_headless`, `session_restore` = `unix`; `auto_detect`, `cli`, `machine_api` = `unix && !macos`; `host_shutdown` = `linux`; `windows_server_security` = `windows`; `session_delete` = no gate. VERIFIED-IN-SOURCE (first `#![cfg` line of each file).
- `tests/cli/harness.rs`: unique base `/tmp/hcli-<pid>-<nanos>` (15-21); `app_dir_name()` mirrors `herdr-dev`/`herdr` (147-153); named session socket `config_home/<app>/sessions/<name>/herdr.sock` (155-161); `spawn_named_server` writes `config.toml` = `onboarding = false`, runs `CARGO_BIN_EXE_herdr --session <name> server` with `XDG_CONFIG_HOME`, `XDG_RUNTIME_DIR` set and `HERDR_SOCKET_PATH`, `HERDR_CLIENT_SOCKET_PATH`, `HERDR_ENV`, `HERDR_STARTUP_CWD`, `HERDR_SESSION` removed (163-194); `spawn_herdr_with_config` spawns `herdr server` on a `portable_pty` PTY with `HERDR_SOCKET_PATH=<socket>` override and `SHELL=/bin/sh` (275-315); CLI calls set `HERDR_SOCKET_PATH` (317-322). VERIFIED-IN-SOURCE.
- `tests/support/mod.rs`: pid registry + watchdog cleanup of spawned servers (12-18), `CURRENT_PROTOCOL = 22`, `CURRENT_ENDPOINT_PROTOCOL_GENERATION = 1` (18-19), `isolate_herdr_test_process` strips `HERDR_STARTUP_CWD`/`HERDR_SESSION` (29-32), servers are stopped with SIGTERM because they ignore SIGHUP (44-55). VERIFIED-IN-SOURCE.
- Windows test `tests/windows_server_security.rs:137-162` shows the Windows-native pattern: `herdr --session <name> server`, `XDG_CONFIG_HOME`/`XDG_STATE_HOME` pointed at a temp dir, `CREATE_NO_WINDOW`, env scrubbed.

### 8.4 What runs without a Rust toolchain

- Python (`python -m unittest scripts.test_<name>` from the repo root; each module also has `if __name__ == "__main__"`), VERIFIED-IN-SOURCE (imports/`subprocess` greps):
  - Pure Python, no external tools: `test_agent_detection_manifest_check` (13 tests), `test_changelog` (33), `test_config_reference_check` (14), `test_docs_translation_parity` (4), `test_hermes_integration_asset` (3), `test_package_windows_conpty` (11, hashlib/zip only), `test_windows_cross` (5), `test_windows_input` (27, "portable tests of the gauntlet's oracle"), `test_ui_hot_path_architecture` (6, regex over `src/`).
  - Need `git`: `test_preview` (9; `git init` in temp), `test_release` (10; `git diff/apply`), `test_vendor_libghostty_vt` (9; mocks most, one `git apply --check`).
  - Need Unix `/bin/sh`: `test_unix_installer` (5; runs the installer script with a fake curl).
  - Needs `cargo metadata` (and git): `test_vendor_portable_pty` (7) — not Rust-free.
- Bun/Node (no Rust): `scripts/release-workflows.test.ts`, `scripts/docs/{versions,versions.integration,preview.integration}.test.ts`, `src/integration/assets/herdr-agent-state.test.ts`, `src/integration/assets/opencode/{herdr-agent-state,herdr-tui-session}.test.ts` (`justfile:17, 123, 127-129`; `scripts/docs` listing). `release-docs-check` also uses `node scripts/docs/versions.mjs check` and `preview.mjs check` (`justfile:143-144`). Bun is pinned to 1.3.14 in CI.
- PowerShell scripts (`scripts/windows_smoke_conpty_path.ps1`, `windows_conpty_enhanced_input_probe.ps1`, `windows_install_conpty_package_test.ps1`, `test_windows_input.ps1`) require a built `herdr.exe` (`ci.yml:197-203, 338-357`). Not Rust-free.

## 9. Recovery behavior

- Server crash / kill -9: last `session.json` (≤5 s stale, or newer if a checkpoint ran) is restored on next start; layout snapshots (`session-snapshots/`, 48 × ≥15 min) and failed-load backups (`session-backups/`, 3) are never auto-restored (`src/persist/writer.rs:78-124`; docs `session-state.mdx:41-53`). Agents are re-launched by typing their resume command (§2.4); non-agent panes get a fresh shell in the saved cwd. VERIFIED-IN-SOURCE / DOC-ONLY.
- Client disconnect: the server is a detached daemon; abrupt socket drop keeps it running and reachable (`tests/detach_reattach.rs:522-575`); explicit detach sends a clean message (`286-340`). SSH clients whose terminal vanishes detach rather than resize panes (changelog `distribution/latest.json:79`). VERIFIED-IN-SOURCE / DOC-ONLY.
- Host shutdown:
  - Linux: `org.freedesktop.login1.Manager.Inhibit("shutdown","Herdr","Save terminal workspace layout","delay")` is held; on `PrepareForShutdown(true)` the server sets `host_shutdown_requested`, saves, and keeps the delay lock until exit; reconnects with backoff if D-Bus is unavailable (`src/platform/linux/shutdown.rs:7-84`; test `tests/host_shutdown.rs:110`). VERIFIED-IN-SOURCE.
  - macOS: loginwindow monitor with a carried `HostShutdownIntent` (`src/platform/macos/shutdown.rs:57-117`, `src/platform/mod.rs:31-51`). VERIFIED-IN-SOURCE (not read in depth).
  - Windows: no monitor task (`src/platform/mod.rs:71-78`); each loop tick polls `GetSystemMetrics(SM_SHUTTINGDOWN)` (`src/platform/windows.rs:171-177`, `src/server/headless.rs:705-719`); pane exits with `STATUS_CONTROL_C_EXIT` are `Interrupted` and checkpoint the session first (`windows.rs:162-169`, `src/app/api.rs:270-279`). VERIFIED-IN-SOURCE.
  - Common: once requested, API requests are rejected as unavailable, scheduled tasks stop, `initiate_shutdown` notifies clients with `ServerShutdown`, and the session is saved after the loop exits (`src/server/headless.rs:445-450, 2915-2919, 2987-2990, 3276-3278, 696-699`; `src/server/headless/lifecycle.rs:304-332`). VERIFIED-IN-SOURCE.
- Agent restoration settings: `[session] resume_agents_on_restore` (true), `startup_per_agent_delay_ms` (100). Failure modes set a per-pane `restore_error` ("Saved directory is unavailable…", "Could not start the saved shell…") (`src/app/agent_resume.rs:255-262, 282-292`). VERIFIED-IN-SOURCE.
- Remote: saved-machine connections auto-reconnect with exponential backoff to 2 min, require a minute of health before fast retry, probe quiet SSH links, and show `! auth` / `! error` without prompting; background connections never install/restart/hand off (docs `connecting-machines.mdx:90-98`). DOC-ONLY (supervisor code in `src/client/endpoint/supervisor.rs` not read). Idle bridges close after ~1 min of silence when both sides support `--idle-timeout-v1`, leaving the server running (`src/remote/host.rs:7-14`; docs line 94).
- Update/handoff: plain `herdr update` leaves compatible servers running; `--handoff` transfers live PTYs; failure rolls back before commit (`src/server/headless/lifecycle.rs:60-68`). VERIFIED-IN-SOURCE.

## 10. Open questions

1. Windows ACL on saved-machine files: `create_private_state_file` on Windows is `create_new` without an explicit DACL (`src/platform/windows.rs:736-742`), relying on `%LOCALAPPDATA%` inheritance; whether that is the intended protection for `endpoints.json` is not stated. INFERRED.
2. Whether the headless server (not only the TUI client) is the process that runs the 30-minute update/manifest checks — `App::new` spawns them and the server owns an `App`, but I did not trace the client-only `AppPolicy` variants. INFERRED.
3. `tests/session_delete.rs` is the only session test without a cfg gate; I did not confirm whether `cargo nextest` on Windows actually exercises `tests/session_restore.rs`-style restore (it is `#![cfg(unix)]`), so Windows restore coverage appears to rest on unit tests inside `src/persist/*` and `src/app/mod.rs:3209-3344`. INFERRED.
4. Log rotation limits (`DEFAULT_MAX_LOG_BYTES`, `DEFAULT_RETAINED_LOG_FILES`, `src/logging.rs:12-18`) were not read; the test at `logging.rs:621` suggests 8 retained files but that is a test parameter.
5. macOS shutdown handling and `src/client/endpoint/supervisor.rs` reconnect policy were only partially read; details above for those are DOC-ONLY.
6. `pr-gate.yml`, `release.yml`, `preview.yml` and `distribution.yml` were not read; CI statements cover `ci.yml` only.
