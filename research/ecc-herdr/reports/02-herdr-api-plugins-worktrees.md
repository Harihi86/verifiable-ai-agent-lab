# Herdr extension surfaces: API, CLI, plugins, worktrees, config (v0.9.5 @ 2ecf19a9)

Source: `C:\Herdr-dev\herdr` (independent clone, HEAD `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`, `git describe` = `v0.9.5`, `Cargo.toml:3` = `0.9.5`). Static reading only; nothing was built or run.
All paths below are relative to that checkout. Tags: **VERIFIED-IN-SOURCE** (read in `.rs`/fixture/test), **DOC-ONLY** (only in `docs/`, `skills/`, `.agents/`), **INFERRED** (my reasoning from the above).

## 1. Summary (10 bullets)

1. **One control surface, three doors.** The headless server exposes a newline-delimited JSON API over a local socket (Unix socket / Windows named pipe); the `herdr` CLI is a thin wrapper that serializes the same `Method` enum; plugins are plain child processes that call back through that CLI/socket. There is no separate plugin SDK. VERIFIED-IN-SOURCE `src/api/schema.rs:35-252`, `src/cli/runtime.rs:9-14`, `src/app/api/plugins/runtime.rs:39-48`; DOC-ONLY `docs/next/website/src/content/docs/plugins.mdx:23-29`.
2. **102 API methods** in the `Method` enum, grouped as server(7), notification(1), announcements(2), command/client-shell(4), session(1), workspace(9), worktree(4), tab(7), agent(12), pane(34 incl. layout/popup), events(3), integration(3), plugin(11). Full catalog in section 2. VERIFIED-IN-SOURCE `src/api/schema.rs:47-252`.
3. **Connection model is one request per connection.** The server reads a single line (5 s timeout, 1 MiB cap), answers one line, and closes, except `events.subscribe`, `events.wait`, `agent.wait`, `agent.prompt` (with wait), `pane.wait_for_output`, and `server.ssh_agent.register`, which hold the connection. VERIFIED-IN-SOURCE `src/api/server.rs:30-34,341-377,428-519,914-994`.
4. **Discovery is path-based, no token auth.** Socket = `<config_dir>/herdr.sock` (default session) or `<config_dir>/sessions/<name>/herdr.sock`; precedence `--session` > `HERDR_SOCKET_PATH` > `HERDR_SESSION` > default. On Windows the same path string becomes the pipe name `\\.\pipe\<path>` and a marker file is written at the path; access is a per-user DACL plus a mandatory-integrity label (HI when the server is elevated unless `server.allow_unelevated_clients = true`). VERIFIED-IN-SOURCE `src/session.rs:163-183`, `src/ipc.rs:44-80`, `src/platform/windows.rs:36,45-80,127-131`.
5. **Event stream exists; webhooks do not.** `events.subscribe` streams 26 lifecycle kinds plus 3 sampled kinds from a 512-event in-memory ring (`events_lost` on overrun). The only exec-on-event mechanism is a plugin manifest `[[events]]` hook (23 whitelisted event names, high-volume kinds excluded). VERIFIED-IN-SOURCE `src/api/schema/events.rs:16-85,194-221,286-310`, `src/api/event_hub.rs:19`, `src/api/subscriptions.rs:326-340`, `src/app/api/plugins/runtime.rs:203-251`.
6. **Plugins = TOML manifest + argv commands, any language.** Required `id`, `name`, `version`, `min_herdr_version`; optional `description`, `platforms`, `[[build]]`, `[[startup]]`, `[[actions]]`, `[[events]]`, `[[panes]]`, `[[link_handlers]]`. Commands run as the user with cwd = plugin root, no shell, no sandbox, 64 KiB captured output, max 32 concurrent, 200 log entries. Node.js or Python programs qualify directly. VERIFIED-IN-SOURCE `src/app/api/plugins/manifest.rs:11-96,118-225`, `src/app/api/plugins/runtime.rs:11-13,103-129`; DOC-ONLY `plugins.mdx:6-11,165-167`.
7. **Plugin trust model is "review then confirm".** `herdr plugin install owner/repo[/subdir]` does a depth-1 git fetch, prints a preview of every command, requires an interactive `y` or `--yes`, runs `[[build]]` with Herdr runtime env scrubbed, refuses if the manifest changed during build, then registers in a user-global `plugins.json`. `plugin link <path>` registers a local dir without building. VERIFIED-IN-SOURCE `src/cli/plugin.rs:197-222,320-450,1069-1093,1695-1713`, `src/persist/plugin_registry.rs:11-13`.
8. **Worktree API is a thin, request-scoped wrapper over `git worktree`.** `trust_repository: true` only adds `-c safe.directory=<repo_root>` to that request's git invocations; nothing is persisted. Default checkout path is `worktrees.directory/<repo>/<branch-slug>`; branch defaults to a generated slug from `HEAD`. VERIFIED-IN-SOURCE `src/worktree.rs:154-173,239-322`, `src/app/api/worktrees/deferred.rs:100-225`.
9. **Isolated server recipe (all verified):** `XDG_CONFIG_HOME=<dir> XDG_STATE_HOME=<dir> HERDR_CONFIG_PATH=<file> herdr --session <name> server` with `HERDR_SOCKET_PATH`, `HERDR_CLIENT_SOCKET_PATH`, `HERDR_ENV`, `HERDR_SESSION`, `HERDR_STARTUP_CWD`, `HERDR_*_ID` unset; then address it with `HERDR_SESSION=<name>` or `--session <name>`. `XDG_CONFIG_HOME` is honored on Windows too. VERIFIED-IN-SOURCE `src/config/io.rs:30-42`, `tests/cli/harness.rs:163-194,222-245`, `src/main.rs:569-571`; DOC-ONLY `.agents/skills/herdr-throwaway-repro/SKILL.md:53-122`.
10. **Stability:** the JSON API and CLI are documented as the stable control surface (clients must ignore unknown fields; numeric `PROTOCOL_VERSION = 22` guards same-install operations); the plugin API is explicitly "an early interface"/v1; live handoff is "experimental and opt-in"; `[experimental]` config holds `allow_nested`/`pane_history`; `pane.graphics.*` methods were retired. DOC-ONLY `socket-api.mdx:451-456,942-958`; VERIFIED-IN-SOURCE `src/protocol/wire.rs:20`, `src/api/server.rs:271`.

## 2. API method catalog (table by area)

Request envelope: `{"id": "<string>", "method": "<name>", "params": {...}}` (`Request` flattens `Method`, tag `method`, content `params`). Success: `{"id","result":{"type": "<snake_case>", ...}}`; error: `{"id","error":{"code","message"}}`. VERIFIED-IN-SOURCE `src/api/schema.rs:35-47`, `src/api/schema/response.rs:24-44`. Request params are cited from the schema files; response `type` from `response.rs:44-281`.

| Area | Method | Params (one line) | Result `type` |
| --- | --- | --- | --- |
| server | `ping` | `{}` | `pong {version, protocol, capabilities?}` (`response.rs:45-50`) |
| server | `server.stop` | `{}` | `ok` (handled before App: `server.rs:582-592`) |
| server | `server.live_handoff` | `{import_exe?, expected_protocol?, expected_version?}` (`schema/server.rs:7-14`) | varies (handoff; experimental) |
| server | `server.reload_config` | `{}` | `config_reload {status, diagnostics}` |
| server | `server.ssh_agent.register` | `{socket_path}` Unix only, lease lasts for the connection (`schema/server.rs:16-20`, `server.rs:385-427`) | `ok` |
| server | `server.agent_manifests` | `{}` | `agent_manifest_status {last_check_unix?, last_result?, manifests[]}` |
| server | `server.reload_agent_manifests` | `{}` | `agent_manifest_reload {manifests[]}` |
| notification | `notification.show` | `{title, body?, position?, sound?}` (`common.rs:103-112`) | `notification_show {shown, reason}` |
| announcements | `product_announcement.dismiss` / `release_notes.dismiss` | `{version, id}` / `{version}` (`common.rs:38-47`) | `ok` |
| client | `client.window_title.set` / `.clear` | `{title}` / `{}` | `client_window_title {changed, reason}` |
| client-shell | `client_shell.surface.set` | `{active}`; rejected on the JSON socket with `connection_local_only` (`server.rs:574-580`) | `client_shell_surface_set` |
| client-shell | `command.invoke` | `{command_id, workspace_id?, tab_id?, pane_id?, selection?}` (`commands.rs:3-16`) | varies |
| session | `session.snapshot` | `{}` | `session_snapshot {snapshot{version, protocol, focused_*_id, workspaces, tabs, panes, layouts, agents}}` (`session.rs:8-23`) |
| workspace | `workspace.create` | `{source_workspace_id?, cwd?, focus, label?, env{}}` (`workspaces.rs:7-20`) | `workspace_created {workspace, tab, root_pane}` |
| workspace | `workspace.list` / `.get` / `.focus` | `{}` / `{workspace_id}` | `workspace_list` / `workspace_info` |
| workspace | `workspace.rename` / `.move` / `.move_block` | `{workspace_id, label}` / `{workspace_id, insert_index}` / `{workspace_ids[], before_workspace_id?}` | `workspace_info` / `ok` |
| workspace | `workspace.report_metadata` | `{workspace_id, source, tokens{name: string\|null}, seq?, ttl_ms? (1..86_400_000)}` (`workspaces.rs:48-59`) | `ok` |
| workspace | `workspace.close` | `{workspace_id, close_group=false}`; `workspace_group_close_required` if linked worktrees open (`workspaces.rs:22-27`; DOC `socket-api.mdx:368`) | `ok` |
| worktree | `worktree.list` | `{workspace_id?, cwd?, trust_repository=false}` (`worktrees.rs:3-11`) | `worktree_list {source, worktrees[]}` |
| worktree | `worktree.create` | `{workspace_id?, cwd?, branch?, base?, path?, label?, focus, trust_repository}` (`worktrees.rs:13-31`) | `worktree_created {workspace, tab, root_pane, worktree}` |
| worktree | `worktree.open` | `{workspace_id?, cwd?, path? \| branch?, label?, focus, trust_repository}` (`worktrees.rs:33-49`) | `worktree_opened {..., already_open}` |
| worktree | `worktree.remove` | `{workspace_id, force=false, trust_repository}` (`worktrees.rs:51-58`) | `worktree_removed {workspace_id, path, forced}` |
| tab | `tab.create` | `{workspace_id?, cwd?, focus, label?, env{}}` (`tabs.rs:7-19`) | `tab_created {tab, root_pane}` |
| tab | `tab.list` / `.get` / `.focus` / `.close` | `{workspace_id?}` / `{tab_id}` | `tab_list` / `tab_info` / `ok` |
| tab | `tab.rename` / `.move` | `{tab_id, label}` / `{tab_id, insert_index}` | `tab_info` / `ok` |
| agent | `agent.list` / `.get` / `.focus` / `.explain` | `{}` / `{target}` (name or pane id) | `agent_list` / `agent_info` / `agent_explain {explain: json}` |
| agent | `agent.read` | `{target, source, lines?, format, strip_ansi}` (`agents.rs:8-17`) | `pane_read {read}` |
| agent | `agent.send_keys` | `{target, keys[]}` | `ok` |
| agent | `agent.rename` | `{target, name?}` | `agent_info` |
| agent | `agent.start` | `{name, kind, pane_id, args[], timeout_ms?}` (`agents.rs:167-176`) | `agent_started {agent, argv}` |
| agent | `agent.prompt` | `{target, text, wait?{until[], timeout_ms?}}` (`agents.rs:35-44,179-184`) | `agent_prompted {agent}` or `wait_matched` |
| agent | `agent.wait` | `{target, until[], timeout_ms?}` (`agents.rs:26-32`) | `wait_matched {event}` |
| agent | `agent.view.set` / `.clear` | `{source, label?, filter?, sort[]}` / `{source?}` (`agents.rs:53-66`) | `agent_view {active, source?, label?}` |
| pane | `pane.list` / `.current` / `.get` / `.focus` / `.close` | `{workspace_id?}` / `{caller_pane_id?}` / `{pane_id}` | `pane_list` / `pane_current` / `pane_info` / `ok` |
| pane | `pane.split` | `{workspace_id?, target_pane_id?, direction, ratio?, cwd?, focus, right_click, env{}}` (`panes.rs:19-37`) | `pane_info {pane}` |
| pane | `pane.swap` / `.move` / `.zoom` | directional or explicit (`panes.rs:64-126`) | `pane_swap` / `pane_move` / `pane_zoom` |
| pane | `pane.layout` / `.neighbor` / `.edges` / `.focus_direction` / `.resize` / `.scroll` | `{pane_id?...}` (`panes.rs:128-243`) | `pane_layout` / `pane_neighbor` / `pane_edges` / `pane_focus_direction` / `pane_resize` / `ok` |
| pane | `pane.process_info` | `{pane_id?}` | `pane_process_info {shell_pid, foreground_process_group_id, tty, foreground_processes[]}` (`panes.rs:494-520`) |
| pane | `pane.clear` / `.edit_scrollback` / `.rename` / `.input.set` | `{pane_id}` / `{pane_id, label}` / `{pane_id, right_click}` | `ok` / `pane_info` |
| pane | `pane.send_text` / `.send_keys` / `.send_input` | `{pane_id, text}` / `{pane_id, keys[]}` / `{pane_id, text?, keys[]}` (`panes.rs:326-345`) | `ok` |
| pane | `pane.read` | `{pane_id, source(visible\|recent\|recent_unwrapped\|detection), lines?, format(text\|ansi), strip_ansi}` (`panes.rs:347-360`, `common.rs:78-101`) | `pane_read {read}` |
| pane | `pane.selection.read` / `.copy_motion` / `.copy_search` | selection coordinates + `content_revision` (`panes.rs:250-305`) | `pane_selection` / `pane_copy_motion` / `pane_copy_search` |
| pane | `pane.link.resolve` / `.activate` | `{pane_id, ...}` (`panes.rs:44-54`) | `pane_link_resolved {regions[]}` / `pane_link_activated {url?, handled}` |
| pane | `pane.report_agent` / `.report_agent_session` / `.report_metadata` | `{pane_id, source, agent, state\|agent_session_id\|title/display_agent/state_labels/tokens, seq?, ttl_ms?, resume_argv?}` (`panes.rs:362-430`; DOC `socket-api.mdx:656-771`) | `ok` |
| pane | `pane.clear_agent_authority` / `.release_agent` | `{pane_id, ...}` (`panes.rs:431-447`) | `ok` |
| pane | `pane.wait_for_output` | `{pane_id, source, lines?, match{type: substring\|regex, value}, timeout_ms?, strip_ansi}` (`events.rs:94-112`) | `output_matched {pane_id, revision, matched_line?, read}` |
| layout | `layout.export` / `.apply` / `.set_split_ratio` | `{tab_id?\|pane_id?}` / declarative BSP tree / `{tab_id, path[], ratio}` (`panes.rs:140-207`) | `layout_export` / `layout_apply` / `layout_split_ratio_set` |
| popup | `popup.close` | `{}` | `ok` / `popup_not_open` |
| events | `events.subscribe` | `{subscriptions:[{type, ...}]}` (`events.rs:11-85`) | `subscription_started {}` then pushed `{event, data}` lines |
| events | `events.wait` | `{match_event{event, ...ids}, timeout_ms?}` (`events.rs:87-92,114-190`) | `wait_matched {event}` |
| integration | `integration.list` / `.install` / `.uninstall` | `{}` / `{target}` from 17 targets (`integrations.rs:30-71`) | `integration_list` / `integration_install {target, details{messages[]}}` |
| plugin | `plugin.link` | `{path, enabled=true, source?{kind: local\|github, owner, repo, subdir, requested_ref, resolved_commit, managed_path, installed_unix_ms}}` (`plugins.rs:11-18,70-88`) | `plugin_linked {plugin}` |
| plugin | `plugin.list` / `.unlink` / `.enable` / `.disable` | `{plugin_id?}` / `{plugin_id}` | `plugin_list` / `plugin_unlinked {plugin_id, removed}` / `plugin_enabled` / `plugin_disabled` |
| plugin | `plugin.action.list` / `.invoke` | `{plugin_id?}` / `{action_id, plugin_id?, context?}` (`plugins.rs:291-312`) | `plugin_action_list` / `plugin_action_invoked {action, context, log}` |
| plugin | `plugin.log.list` | `{plugin_id?, limit?}` | `plugin_log_list {logs[]}` (log shape `plugins.rs:314-335`) |
| plugin | `plugin.pane.open` / `.focus` / `.close` | `{plugin_id, entrypoint, placement?, width?, height?, workspace_id?, target_pane_id?, direction?, cwd?, focus, env{}}` / `{pane_id}` (`plugins.rs:417-462`) | `plugin_pane_opened {plugin_pane}` / `ok` |

Methods flagged as UI-changing (for logging only) are listed in `src/api/mod.rs:22-81`. The `pane.graphics.*` family is retired and answers `unknown_method` without upgrade (`src/api/server.rs:271`; DOC `socket-api.mdx:185-188`). VERIFIED-IN-SOURCE.

## 3. Connection, discovery, security, events

**Transport and framing.** NDJSON over `interprocess` local sockets. Per connection: set 5 s write timeout, read exactly one line (5 s initial timeout, 1 MiB max, invalid UTF-8 closes), parse `Request`; parse failures echo the `id` only when it is an unambiguous top-level string. Non-streaming methods are dispatched to the App via an mpsc channel with a 5 s `APP_RESPONSE_TIMEOUT` and the response is written as one line. VERIFIED-IN-SOURCE `src/api/server.rs:29-35,337-377,488-519,551-602,727-790`.

**Handshake / version.** There is no handshake; `ping` is the capability probe: `{type:"pong", version, protocol: 22, capabilities{live_handoff, detached_server_daemon, endpoint_protocol_generation?, surface_interest, health_check, ssh_agent_registration}}`. The CLI pings before every request and refuses on protocol mismatch (`cli.rs:769-801`, `cli/protocol_guard.rs:18-21`). VERIFIED-IN-SOURCE `src/api/server.rs:70-79,559-572`, `src/api/schema/server.rs:22-39`, `src/protocol/wire.rs:20`. Bundled schema: `docs/next/api/herdr-api.schema.json` (272,578 bytes; `"protocol": 22`, `"schema_version": 1`), embedded via `include_str!` and printed by `herdr api schema --json` (`src/cli/api.rs:1,25-54`). VERIFIED-IN-SOURCE.

**Socket path discovery.**
- `api::socket_path()` -> `session::active_api_socket_path()`: if `--session` was given this run -> `<data_dir>/herdr.sock`; else if `HERDR_SOCKET_PATH` set -> that path; else `<data_dir>/herdr.sock` where `data_dir = config_dir` (default session) or `config_dir/sessions/<name>` (`HERDR_SESSION`). VERIFIED-IN-SOURCE `src/api/mod.rs:20,91-93`, `src/session.rs:98-103,159-187`.
- `config_dir`: `$XDG_CONFIG_HOME/herdr` (any OS) else Windows `%APPDATA%\herdr` else `~/.config/herdr`. `state_dir`: `$XDG_STATE_HOME/herdr` else `%LOCALAPPDATA%\herdr` else `~/.local/state/herdr`. Debug builds use `herdr-dev`. VERIFIED-IN-SOURCE `src/config/io.rs:22-94`.
- Client (terminal) socket is `<stem>-client.sock` next to the API socket; legacy `HERDR_CLIENT_SOCKET_PATH` override. VERIFIED-IN-SOURCE `src/server/socket_paths.rs:9-58`.
- `--session` is stripped from argv before clap/dispatch and exported as `HERDR_SESSION`, setting an "explicit session" flag that beats `HERDR_SOCKET_PATH`; `--session default` maps to the default dir. Names: 1-64 bytes, `[A-Za-z0-9._-]`, not `.`/`..`. VERIFIED-IN-SOURCE `src/session.rs:31-96,461-501`.

**Windows specifics.** `connect_local_stream`/`bind_local_listener` convert the full path string with `to_ns_name::<GenericNamespaced>()`; `probe_local_server` shows the resulting name is `\\.\pipe\<path>`. After binding, a marker file `"<pid>:<nanos>"` is written at the path so stale detection and ownership checks work. VERIFIED-IN-SOURCE `src/ipc.rs:44-80,282-328`, `src/platform/windows.rs:30-43`.

**Security.**
- Unix: socket file chmod `0600` (`src/api/server.rs:29,304-306`, `src/server/socket_paths.rs:11-12,72-75`). VERIFIED-IN-SOURCE.
- Windows API pipe SDDL: `D:P(A;;GA;;;SY)(A;;GRGW;;;<current user SID>)S:(ML;;NRNW;;;HI|ME)`; label is `HI` when the server token is elevated and `allow_unelevated_clients` is not set, otherwise `ME`. The private client-protocol pipe uses `D:P(A;;GA;;;SY)(A;;GA;;;OW)`. VERIFIED-IN-SOURCE `src/platform/windows.rs:24-28,45-80,82-132`, `src/ipc.rs:136-164`.
- `allow_unelevated_clients` comes from `[server]` config at server start or `herdr server --allow-unelevated-clients`; requires restart. VERIFIED-IN-SOURCE `src/server/headless/bootstrap.rs:30-34`, `src/cli/server.rs:4-8`, `src/cli/spec.rs:178-182`; DOC `src/main.rs:227-230`.
- No bearer tokens, no per-method authorization: anyone who can open the socket has the full API. INFERRED from the absence of any auth field in `Request` (`src/api/schema.rs:35-40`) and the connection handler (`src/api/server.rs:328-520`).
- Server startup: `herdr server` runs headless; the TUI spawns `herdr server` detached, inheriting `XDG_CONFIG_HOME`/`HERDR_SESSION` and clearing socket overrides when `--session` was explicit. VERIFIED-IN-SOURCE `src/main.rs:569-571`, `src/server/autodetect.rs:196-251`.

**Event stream.** `events.subscribe` validates every entry (any invalid pane rejects the whole request), writes `subscription_started`, then loops at 100 ms draining batches per subscription from the `EventHub` (512 retained envelopes; falling behind yields `error.code = "events_lost"` and the connection closes). VERIFIED-IN-SOURCE `src/api/server.rs:30,914-994`, `src/api/event_hub.rs:18-75`, `src/api/subscriptions.rs:282-340`.
- Subscribable lifecycle types (`Subscription` enum): `workspace.{created,updated,metadata_updated,renamed,moved,reordered,closed,focused}`, `worktree.{created,opened,removed}`, `tab.{created,closed,focused,renamed,moved}`, `pane.{created,closed,updated,focused,moved,exited,agent_detected}`, `layout.updated`; sampled/filtered types: `pane.output_matched {pane_id, source, lines?, match, strip_ansi}`, `pane.agent_status_changed {pane_id, agent_status?}`, `pane.scroll_changed {pane_id}`. VERIFIED-IN-SOURCE `src/api/schema/events.rs:16-85,368-376`.
- Emitted `EventKind` (26): the above plus `pane.output_changed` (available to `events.wait` via `EventMatch::PaneOutputChanged{pane_id, min_revision?}` but **not** a `Subscription` variant). VERIFIED-IN-SOURCE `src/api/schema/events.rs:114-190,194-221`. Event payload shapes: `EventData` (`events.rs:421-556`).
- Plugin hook whitelist (`PLUGIN_HOOK_EVENT_KINDS`, 23): all lifecycle kinds except `pane.output_changed`, `layout.updated`, `workspace.metadata_updated`, `pane.updated`. VERIFIED-IN-SOURCE `src/api/schema/events.rs:286-358`.

**Webhooks / exec-on-event.** No HTTP webhooks exist (no outbound URL config anywhere in `src/api` or `src/config/model.rs`; INFERRED). Exec-on-event is only: (a) plugin `[[events]]` and `[[startup]]` hooks spawned by the server (`src/app/api/plugins/runtime.rs:161-251`); (b) `[[keys.command]] type = "plugin_action"` keybindings (`src/app/api/plugins/mod.rs:225-231`; DOC `plugins.mdx:345-355`); (c) `[[link_handlers]]` on modified link clicks (`mod.rs:329-407`). VERIFIED-IN-SOURCE.

## 4. Plugin system (manifest spec, lifecycle, environment, trust) + minimal example

**Manifest file** `herdr-plugin.toml` at the plugin root (or passed directly). Parsed by `RawPluginManifest`. VERIFIED-IN-SOURCE `src/app/api/plugins/manifest.rs:11-96,118-225`.

| Field | Type / rule | Evidence |
| --- | --- | --- |
| `id` | required; 1-120 chars of `[A-Za-z0-9:._-]` | `manifest.rs:8,142-143,591-607` |
| `name`, `version` | required, non-empty after trim | `manifest.rs:144-149` |
| `min_herdr_version` | **required** semver; link fails with `plugin_requires_newer_herdr` if newer than the running binary | `manifest.rs:227-256` |
| `description` | optional | `manifest.rs:151-154` |
| `platforms` | optional `["linux"\|"macos"\|"windows"]`; empty array rejected; omission adds a warning | `manifest.rs:98-116,155,201-204,502-514` |
| `[[build]]` | `{platforms?, command[]}`; run only by `plugin install`, never by `plugin link` | `manifest.rs:36-41,258-264`; `cli/plugin.rs:386-391`; DOC `plugins.mdx:232-245` |
| `[[startup]]` | `{platforms?, command[]}`; one-shot after restore when API ready; also after live handoff | `manifest.rs:43-48`; `runtime.rs:161-201`; DOC `plugins.mdx:247-263` |
| `[[actions]]` | `{id, title, description?, contexts[global\|workspace\|tab\|pane\|selection], platforms?, command[]}`; ids 1-120 chars `[A-Za-z0-9:_-]` (no dots), unique | `manifest.rs:50-61,320-333,390-414,595-617`; `schema/plugins.rs:353-361` |
| `[[events]]` | `{on, platforms?, command[]}`; unknown `on` is a warning, not an error | `manifest.rs:63-69,335-342,452-463` |
| `[[panes]]` | `{id, title, description?, platforms?, placement=overlay\|popup\|split\|tab\|zoomed, width?, height?, command[]}`; size only with `popup` | `manifest.rs:71-86,416-450`; `schema/plugins.rs:441-452` |
| `[[link_handlers]]` | `{id, title, pattern (Rust regex), action (must name a declared action), platforms?}` | `manifest.rs:88-96,357-388,465-500` |
| `command` (all) | argv array, every element non-empty; no shell | `manifest.rs:568-576`; DOC `plugins.mdx:119-121` |

**Minimal valid manifest (fixture, verbatim).** VERIFIED-IN-SOURCE `tests/fixtures/plugin-smoke/herdr-plugin.toml:1-22`; an even smaller offline variant with only the four required keys plus `platforms` links successfully in `tests/cli/plugins.rs:122-154`.

```toml
id = "example.smoke"
name = "Smoke Plugin"
version = "0.1.0"
min_herdr_version = "0.6.10"
description = "Portable plugin smoke fixture"
platforms = ["linux", "macos", "windows"]

[[actions]]
id = "workspace-list"
title = "List workspaces"
contexts = ["workspace"]
command = ["herdr", "workspace", "list"]

[[events]]
on = "worktree.created"
command = ["herdr", "plugin", "log", "list", "--plugin", "example.smoke"]

[[panes]]
id = "board"
title = "Board"
placement = "overlay"
command = ["herdr", "workspace", "list"]
```

**Install paths and registry.** VERIFIED-IN-SOURCE.
- Registry: `<config_dir>/plugins.json`, user-global, shared by all sessions (`src/persist/plugin_registry.rs:11-13`; test `tests/cli/plugins.rs:115-170`; DOC `socket-api.mdx:458-465`). Written by the server on `plugin.link/unlink/enable/disable` and by the CLI offline (`src/cli/plugin.rs:85,134,1139-1160`).
- GitHub install: `herdr plugin install <owner>/<repo>[/subdir] [--ref REF] [--yes|-y]`. Flow: temp `git init` + `remote add origin https://github.com/<owner>/<repo>.git` + `fetch --depth 1 origin <ref|HEAD>` + `checkout --detach FETCH_HEAD`; load manifest; take a per-plugin lock file `<config_dir>/plugins/.locks/.<slug-hash>.lock`; refuse to replace a locally linked plugin; print preview (id, version, source, commit, every build/startup/action/event/pane command, warnings); prompt `[y/N]` unless `--yes` (non-interactive stdin without `--yes` exits 2); create `<config_dir>/plugins/github-installations/<slug-hash>/<pid>-<gen>/checkout`; run build commands with `HERDR_BIN_PATH/HERDR_ENV/HERDR_*_ID/HERDR_PLUGIN_*` scrubbed; abort if the manifest changed after build; persist with `source.kind = "github"`. Old installations are leased and cleaned up later. `src/cli/plugin.rs:197-222,320-450,1069-1093,1392-1458,1695-1713,1761-1773`; `src/plugin_paths.rs:5-42`; `src/plugin_installations.rs:12-57,224-250`; `src/app/api/plugins/manifest.rs:274-318` (server re-validates `managed_path`).
- Local link: `herdr plugin link <abs path> [--disabled|--enabled]` (`src/cli/spec.rs:821-827`); `plugin unlink` only unregisters. `plugin update [PLUGIN...] [--yes]` re-fetches recorded refs and skips unchanged commits (`cli/plugin.rs:224-318,349-357`).
- Per-plugin dirs: `HERDR_PLUGIN_CONFIG_DIR = <config_dir>/plugins/config/<encoded id>`, `HERDR_PLUGIN_STATE_DIR = <state_dir>/plugins/<encoded id>`; created on every command start. `src/plugin_paths.rs:44-60`; `src/app/api/plugins/env.rs:3-30`.

**How plugins run.** Actions, event hooks and startup hooks are spawned as detached child processes (not panes) from a server thread: `program = command[0]`, cwd = plugin root, stdout/stderr piped and capped at 64 KiB each, max 32 in flight, 200 retained log entries; completion is reported as `PluginCommandFinished` and visible via `plugin.log.list`. Windows resolves bare program names through `PATH`+`PATHEXT` and wraps `.bat/.cmd` in `cmd /d /c`. VERIFIED-IN-SOURCE `src/app/api/plugins/runtime.rs:11-159,264-364`, `src/plugin_command.rs:5-111`. Panes (`[[panes]]`/`plugin.pane.open`) run the argv inside a real PTY pane with placement overlay/popup/split/tab/zoomed; split/tab/zoomed/overlay panes are ordinary panes afterwards; popup has no pane id. `src/app/api/plugins/panes.rs:11-170`; DOC `socket-api.mdx:590-606`.

**Environment given to plugin processes.** VERIFIED-IN-SOURCE `src/app/api/plugins/runtime.rs:39-81`, `panes.rs:246-280,356-367`, `env.rs:15-30`:
`HERDR_SOCKET_PATH`, `HERDR_ENV=1`, `HERDR_BIN_PATH` (absolute path of the running binary), `HERDR_PLUGIN_ID`, `HERDR_PLUGIN_ROOT`, `HERDR_PLUGIN_CONFIG_DIR`, `HERDR_PLUGIN_STATE_DIR`, `HERDR_PLUGIN_CONTEXT_JSON` (`PluginInvocationContext`: workspace/tab/focused pane ids+labels+cwd, worktree provenance, focused agent/status, selected_text, invocation_source, correlation_id, clicked_url, link_handler_id -- `schema/plugins.rs:363-395`), plus when present `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, `HERDR_PANE_ID`; actions add `HERDR_PLUGIN_ACTION_ID`; hooks add `HERDR_PLUGIN_EVENT` (`startup` or event name) and `HERDR_PLUGIN_EVENT_JSON` (the `EventEnvelope`); link handlers add `HERDR_PLUGIN_CLICKED_URL`, `HERDR_PLUGIN_LINK_HANDLER_ID`; panes add `HERDR_PLUGIN_ENTRYPOINT_ID`. Caller `env{}` on `plugin.pane.open` cannot override the protected `HERDR_*` keys (`panes.rs:260,356-367`).

**Permissions / trust.** No sandbox, no capability list, no signature: plugin code runs as the user with the full CLI/socket (DOC `plugins.mdx:35-52`). Server-side gates: `enabled` flag (`plugin_disabled` error, `mod.rs:3545`), platform match (`platform_unsupported`, `manifest.rs:541-558`), manifest availability warnings (`mod.rs:770-774`), `min_herdr_version`, link-handler action must be declared by the same plugin. `agent.view.set` with `source = "plugin:<id>"` is rejected if that plugin is missing/disabled (DOC `socket-api.mdx:431-437`). VERIFIED-IN-SOURCE except where marked DOC.

**Can a Node.js or Python program be a Herdr plugin?** Yes: `command` is any argv (`["node","index.js"]`, `["python","-I","main.py"]`); the docs' first example is Node and explicitly list Python; the only requirements are that the interpreter is on `PATH` (or referenced relatively to the plugin root) and that the program talks back through `HERDR_BIN_PATH` or the socket. DOC-ONLY `plugins.mdx:123-167`; VERIFIED-IN-SOURCE mechanism `src/plugin_command.rs:5-27`, `src/app/api/plugins/runtime.rs:25-31`. Long-running services are not supervised: startup hooks are one-shot and processes outliving the server are not protected from installation cleanup (DOC `plugins.mdx:219-222,256-257`).

**Limits recap.** 32 concurrent commands, 64 KiB stdout/stderr each, 200 log entries, ids <= 120 chars, no runtime action registration, no plugin storage API, popup is a singleton. VERIFIED-IN-SOURCE `runtime.rs:11-13`; DOC `socket-api.mdx:451-456,580-582`.

## 5. Worktree management

- **Methods/CLI.** `worktree list|create|open|remove` map 1:1 to `worktree.*`; output is always JSON (`--json` is a hidden no-op). CLI expands relative `--cwd/--path` locally; with `--machine` they must be absolute or `~`-prefixed. VERIFIED-IN-SOURCE `src/cli/worktree.rs:5,28-73,75-172,174-267,269-343`, `src/cli/runtime.rs:73-87`, `src/cli/spec.rs:232-274`.
- **Create flow** (`start_api_worktree_create`): branch = `params.branch` or a generated slug from a microsecond seed; base = `params.base` or `HEAD`; source resolved from `workspace_id`, `cwd`, or the active workspace; checkout path = `params.path` (must be absolute) or `default_checkout_path(worktrees.directory, repo_name, branch_slug)`; duplicate in-flight operations on the same checkout return `worktree_operation_in_progress`; a named thread creates the parent dir and runs `git -C <source> worktree add` (existing local branch -> checkout it; else `-b <branch> <base>`); completion opens a workspace, marks membership, emits `workspace.created`, `tab.created`, `pane.created`, `worktree.created`. VERIFIED-IN-SOURCE `src/app/api/worktrees/deferred.rs:100-225,406-519`, `src/worktree.rs:171-173,239-322`; DOC `socket-api.mdx:344-366`.
- **Open** reuses an already-open checkout (`already_open: true`), requires exactly one of `path`/`branch`, re-checks source identity when deferred. VERIFIED-IN-SOURCE `src/app/api/worktrees.rs:69-166`, `deferred.rs` tests `1606-1832`; `cli/worktree.rs:251-256`.
- **Remove** runs `git worktree remove [--force] <path>` against a linked child workspace; dirty checkouts need `force`; the branch is never deleted; shutdown panes are restored if git fails. VERIFIED-IN-SOURCE `src/worktree.rs:175-213,346-375`, `deferred.rs:245-404,520-700`; DOC `socket-api.mdx:344`.
- **Workspace groups.** A primary workspace plus its linked worktree workspaces form a group keyed by `repo_key`; `workspace.close` on the primary returns `workspace_group_close_required` unless `close_group: true`; `WorkspaceInfo.worktree` carries `{repo_key, repo_name, repo_root, checkout_path, is_linked_worktree}`. VERIFIED-IN-SOURCE `src/api/schema/workspaces.rs:22-27,78-85`, `src/app/api/worktrees.rs:293-389`.
- **Git trust model.** `trust_repository` is request-scoped: when true, every git invocation for that request is prefixed with `-c safe.directory=<repo_root>`; nothing is written to git config and no trust is remembered. The SKILL instructs agents to use it only after the user verified the repository. VERIFIED-IN-SOURCE `src/worktree.rs:154-169,610-617`, `src/app/api/worktrees/reads.rs:21-24,137-199,300-340`; DOC `skills/herdr/SKILL.md:210`.
- **Restore behaviour.** After a server restart, worktree workspaces are reattached asynchronously; worktree operations on a workspace whose membership is still pending are rejected via `require_restored_worktree_ready` / `pending_restored_worktree_spaces`, and group close waits for the same readiness. `worktrees.directory` is read from config into `state.worktree_directory`. VERIFIED-IN-SOURCE `src/app/api/worktrees.rs:227-306`, `deferred.rs:140-145`; CHANGELOG 0.9.4 note on slow/missing Git data during restore `CHANGELOG.md:36` (DOC).

## 6. CLI conventions and isolation-relevant flags/env

- **Dispatch.** `cli::maybe_run` is a hand-rolled matcher over `server|api|status|completion|config|channel|machine|workspace|worktree|tab|notification|agent|terminal|pane|plugin|integration|session`; `--help` text and shell completions come from a parallel clap `Command` spec (`spec::command()`), so `herdr <group> --help` is clap-rendered while parsing is manual. VERIFIED-IN-SOURCE `src/cli.rs:101-137`, `src/cli/spec.rs:8-114,1392-1400`, `Cargo.toml:32-33`.
- **Global flags (clap spec):** `--session NAME`, `--machine LABEL-OR-ID`, `--remote TARGET`, `--remote-keybindings local|server`, `--handoff`, `--default-config`, `--skill`, `-V/--version`, `-h/--help`. VERIFIED-IN-SOURCE `src/cli/spec.rs:14-31`, `src/main.rs:704-718`.
- **JSON conventions.** Success response JSON on stdout, exit 0; server error JSON on stderr, exit 1; usage errors exit 2; `--json` exists only on commands that otherwise print human text (`status`, `session`, `machine`, `plugin list`, `server agent-manifests`, `api schema`), worktree/workspace/pane/agent responses are JSON always. Request ids are `cli:<group>:<verb>`. VERIFIED-IN-SOURCE `src/cli.rs:81-95,745-767`, `src/cli/runtime.rs:9-14`, `src/cli/worktree.rs:5`, `src/cli/spec.rs:122-136,974-976`; DOC `skills/herdr/SKILL.md:214`.
- **Server-not-running** -> `{"error":{"code":"server_not_running", ...}}` with an attach hint; protocol mismatch -> JSON on stderr, exit 1. VERIFIED-IN-SOURCE `src/cli/server_not_running.rs:26-53`, `src/cli.rs:784-801`, `src/main.rs:496-498`.
- **`--machine`.** Parsed as a prefix, loads `state_dir/client/endpoints.json`, starts a `SavedSshApiBridge` and points `ApiClient` at the bridge socket; `--current` and inherited local ids are disabled under it; local config/session/install commands are not forwarded. VERIFIED-IN-SOURCE `src/cli/target.rs:27-100,203-210`, `src/client/endpoint/catalog.rs:373-383`; DOC `cli-reference.mdx:70-85`.
- **`--current`.** Means "use `HERDR_PANE_ID`" (error when absent); `pane current` defaults to it. VERIFIED-IN-SOURCE `src/cli/pane.rs:101-138`, `src/cli/target.rs:203-210`.
- **Session commands.** `herdr session list|attach <name>|stop <name>|delete <name> [--json]`; `herdr server stop|reload-config|agent-manifests|update-agent-manifests|reload-agent-manifests`; bare `herdr server` runs the headless server for the selected session. VERIFIED-IN-SOURCE `src/cli/spec.rs:159-184,747-768`, `src/cli/server.rs:13-30`, `src/main.rs:569-571`, `src/session.rs:241-330`.
- **Exact isolated-server launch (as used by the repo's own CLI tests):** VERIFIED-IN-SOURCE `tests/cli/harness.rs:163-194,222-245`.
  ```
  env XDG_CONFIG_HOME=<cfg> XDG_RUNTIME_DIR=<rt> \
      -u HERDR_SOCKET_PATH -u HERDR_CLIENT_SOCKET_PATH -u HERDR_ENV -u HERDR_STARTUP_CWD -u HERDR_SESSION \
      herdr --session <name> server
  # address it:
  env XDG_CONFIG_HOME=<cfg> -u HERDR_SOCKET_PATH -u HERDR_CLIENT_SOCKET_PATH -u HERDR_ENV \
      herdr --session <name> pane list          # or HERDR_SESSION=<name>
  # socket/pipe = <cfg>/herdr/sessions/<name>/herdr.sock   (tests/cli/harness.rs:155-161)
  ```
  Add `HERDR_CONFIG_PATH=<file>` to select a config file independent of `config_dir` (`src/config/io.rs:195-200`), and `XDG_STATE_HOME=<dir>` to isolate `client/endpoints.json` and plugin state (`src/client/endpoint/catalog.rs:373-383`, `src/plugin_paths.rs:50-54`). Note: `plugins.json` lives in `config_dir`, so `HERDR_CONFIG_PATH` alone does not isolate the plugin registry (`src/persist/plugin_registry.rs:11-13`). INFERRED consequence; both paths VERIFIED.
- **Other env (CLI reference table):** `HERDR_CONFIG_PATH`, `HERDR_SESSION`, `HERDR_SOCKET_PATH`, `HERDR_PROCESS_DETECTION`, `HERDR_ENV`, `HERDR_PANE_ID`, `HERDR_TAB_ID`, `HERDR_WORKSPACE_ID`, `HERDR_LOG`, `HERDR_DISABLE_SOUND`. DOC-ONLY `cli-reference.mdx:561-574`. Also VERIFIED-IN-SOURCE: `HERDR_CLIENT_SOCKET_PATH` (`socket_paths.rs:9`), `HERDR_INSTALL_DIR` (`update.rs:789`), `HERDR_AGENT_DETECTION_MANIFEST_CATALOG_URL` (`detect/manifest_update.rs:17`), `HERDR_FAKE_UPDATE_VERSION` (`update.rs:33`).
- **Nesting guard.** With `HERDR_ENV=1` inherited, launching the TUI/client is refused unless `[experimental] allow_nested = true`; CLI commands are unaffected. VERIFIED-IN-SOURCE `src/main.rs:3-5,453-457,574-577`.

## 7. Config keys needed for an isolated research profile

Top-level sections accepted: `advanced, experimental, keys, onboarding, remote, server, session, terminal, theme, ui, update, worktrees` (`src/config/io.rs:7-20`). There is **no `[plugins]` or `[machines]` section**: plugins live in `plugins.json`, machines in `state_dir/client/endpoints.json`. VERIFIED-IN-SOURCE.

| TOML key | Default | Isolation value recommended | Evidence |
| --- | --- | --- | --- |
| `onboarding` | unset (show onboarding) | `false` | `src/config/model.rs:313-314`; harness writes it `tests/cli/harness.rs:171-175` |
| `update.channel` | `"stable"` (`"preview"` only on Windows preview builds) | `"stable"` | `src/config/model.rs:14-59`; template `src/main.rs:123-127` |
| `update.version_check` | `true` -- background check **only notifies** (`UpdateReady`), never installs; disabled in debug builds | `false` | `src/config/model.rs:33-47`; `src/app/mod.rs:181-187,585-598`; `src/update.rs:2394-2423` |
| `update.manifest_check` | `true` -- fetches `https://herdr.dev/agent-detection/index.toml` | `false` (or set `HERDR_AGENT_DETECTION_MANIFEST_CATALOG_URL`) | `src/config/model.rs:36`; `src/app/mod.rs:599-606`; `src/detect/manifest_update.rs:16-17` |
| `remote.manage_ssh_config` | `true` (generated ssh config with keepalives + control socket for `--remote`) | `false` if SSH must be untouched; irrelevant without `--remote`/machines | `src/config/model.rs:1059-1073`; template `src/main.rs:404-413` |
| saved machines | file `state_dir/client/endpoints.json`, selection `endpoint-selection.json` | isolate via `XDG_STATE_HOME` | `src/client/endpoint/catalog.rs:373-383` |
| `session.resume_agents_on_restore` | `true` | `false` for deterministic restores | `src/config/model.rs:265-282`; `src/persist/restore.rs:66-87` |
| `session.startup_per_agent_delay_ms` | `100` | keep | `src/config/model.rs:271-279` |
| `server.allow_unelevated_clients` | `false` (Windows only; requires restart) | `false` (run server and clients at the same elevation) | `src/config/model.rs:1041-1049,1314-1322`; `src/server/headless/bootstrap.rs:30-34` |
| `server.headless_cols` / `headless_rows` | `120` / `40` | keep | `src/config/model.rs:1045-1048`; `src/config.rs:79-80` |
| `experimental.allow_nested` | `false` | `true` only when the research server is launched from inside a Herdr pane | `src/config/model.rs:1077-1079`; `src/main.rs:453-457`; DOC `herdr-throwaway-repro/SKILL.md:53-73` |
| `experimental.pane_history` | `false` | `false` | `src/config/model.rs:1082-1083`; template `src/main.rs:418-419` |
| `worktrees.directory` | `"~/.herdr/worktrees"` | point at a research-only directory | `src/config/model.rs:870-873,1190-1196` |
| `ui.toast.delivery` | `"off"` (`herdr`\|`terminal`\|`system`) | `"herdr"` if you want `notification.show` to render; `"off"` returns `disabled` | `src/config/model.rs:63-69,199-204,1249-1258` |
| `ui.toast.delay_seconds` / `ui.toast.herdr.position` | `1` / `"bottom-right"` | keep | `src/config/model.rs:1249-1266` |
| `advanced.scrollback_limit_bytes` | `10_000_000` | keep or lower | `src/config/model.rs:1053-1057`; `src/config.rs:76` |
| `terminal.default_shell` / `shell_mode` / `new_cwd` | `""` (SHELL/`/bin/sh`), see enums | keep | `src/config/model.rs:254-263` |
| plugin registry | `<config_dir>/plugins.json` + `<config_dir>/plugins/**` | isolate via `XDG_CONFIG_HOME` | `src/persist/plugin_registry.rs:11-13`; `src/plugin_paths.rs:5-54` |
| session state | `<data_dir>/session.json`, `session-history.json`, `session-snapshots/` | automatic per `--session` | `src/persist/io.rs:11-16`; `src/persist/writer.rs:54-118` |

Config file load: `HERDR_CONFIG_PATH` else `<config_dir>/config.toml`; parse errors fall back to defaults with diagnostics; `herdr config check` validates. VERIFIED-IN-SOURCE `src/config/io.rs:130-200`, `src/cli.rs:120,312`. A complete commented template is `herdr --default-config` (`src/main.rs:67-443,731-733`).

## 8. Skills and project-local skills content summary

- **`skills/herdr/SKILL.md`** (shipped with the binary, printed by `herdr --skill`; `Cargo.toml:16`, `src/main.rs:450,737`). Instructs an agent to: verify `HERDR_ENV=1` before any control command and stop otherwise (l.10-16); learn syntax from `herdr --help` and group help, never bare `herdr` (l.20-45); distinguish pane vs agent surfaces and lifecycle states `idle/working/blocked/done/unknown` (l.47-59); use opaque ids `w1`, `w1:t1`, `w1:p1`, `--current`, and `HERDR_*_ID` (l.61-105); `--machine` semantics (l.91-105); start agents via `pane split --current ... --no-focus` then `agent start <name> --kind <kind> --pane <id> [-- args]`, prompt with `agent prompt ... --wait`, read with `agent read` (l.107-171); run ordinary commands with `pane run` / `pane wait-output` / `pane read` (l.173-202); safety rules: `--no-focus`, never close others' resources, `--trust-repository` only after user verification, never `herdr server stop` or kill the main process, **"Use named test sessions for experiments that need an isolated server"**, exit codes 1/2 (l.204-214). DOC-ONLY. AGENTS.md says this file tracks the latest stable release (`AGENTS.md:219`).
- **`.agents/skills/herdr-throwaway-repro/SKILL.md`** -- the isolated-testing recipe. Key instructions: never use the default session, never stop/kill the main server, unique session name `repro-<topic>-<timestamp>`, read ids from output (l.12-22); create an outer pane; write a test config with `[experimental] allow_nested = true` and pass it as `HERDR_CONFIG_PATH` (it selects only the config file; add `XDG_CONFIG_HOME`/`XDG_STATE_HOME` when machines or other global state matter) (l.49-78); launch with `env -u HERDR_SOCKET_PATH -u HERDR_CLIENT_SOCKET_PATH -u HERDR_SESSION -u HERDR_WORKSPACE_ID -u HERDR_TAB_ID -u HERDR_PANE_ID HERDR_CONFIG_PATH=<abs> herdr --session <name>` (l.80-99); address it with the same `env -u ...` prefix plus `HERDR_SESSION=<name>` on every command (l.103-122); named sessions isolate runtime/sockets/persistence but share global config and manifest overrides (l.122); cleanup = `session stop` then `session delete`, close only the outer pane (l.174-186). DOC-ONLY; every env/flag it names is VERIFIED above.
- **`.agents/skills/herdr-pre-release-audit/SKILL.md`** -- repo-only release audit: compare commits since base tag with `docs/next/CHANGELOG.md`, staged website docs, check `skills/herdr/SKILL.md` against shipped CLI, run `just pre-release-check` / `just bench-render-scale`, no edits unless asked (l.1-22; workflow in `references/pre-release-audit.md`). DOC-ONLY.
- **`.agents/skills/triage/SKILL.md`** -- GitHub issue triage into a light/recommendation table using GitHub MCP or `gh` (l.1-28). DOC-ONLY.

## 9. Stability classification

| Surface | Classification | Evidence |
| --- | --- | --- |
| JSON socket API + CLI wrappers | Stable control surface; clients must ignore unknown fields and treat unsupported methods as errors; numeric `PROTOCOL_VERSION = 22` guards same-install attach/handoff and is enforced by the CLI pre-flight ping | DOC `socket-api.mdx:93-112,942-958`; VERIFIED `src/protocol/wire.rs:20`, `src/cli.rs:769-801` |
| Client endpoint protocol | "stable endpoint generation"; capabilities `surface_interest`, `health_check` advertised | DOC `socket-api.mdx:944-953`, `AGENTS.md:83-93`; VERIFIED `src/api/schema/server.rs:22-39` |
| Plugin API | "an early interface" / "plugin v1"; manifest-only actions/panes, no runtime registration, no storage API | DOC `socket-api.mdx:451-456,580-582`, `plugins.mdx:31-33` |
| `plugin update` | New in 0.9.4 | DOC `CHANGELOG.md:17-20` |
| Live handoff (`--handoff`, `server.live_handoff`) | "experimental and opt-in" | DOC `cli-reference.mdx:28`, `session-state.mdx:127`, `connecting-machines.mdx:128` |
| `[experimental]` config (`allow_nested`, `pane_history`, IME keys) | Experimental by section name | VERIFIED `src/config/model.rs:1075-1118`; DOC `configuration.mdx:524` |
| Update channels | `stable` default; `preview` opt-in prereleases | VERIFIED `src/config/model.rs:14-59`; DOC `install.mdx:138`, `AGENTS.md:266-280` |
| Windows | Docs page is named "windows-beta" but stable-channel Windows binaries ship; elevated-server DACL default changed in 0.9.4 | DOC `install.mdx:158`, `windows-beta.mdx`, `CHANGELOG.md:24` |
| `pane.graphics.*` | Retired, no replacement | DOC `socket-api.mdx:185-188`; VERIFIED `src/api/server.rs:271-293` |
| Letta integration | "experimental and CLI-only", absent from `IntegrationTarget` | DOC `integrations.mdx:262`; VERIFIED `src/api/schema/integrations.rs:30-71` |
| `server.ssh_agent.register` | Unix only; capability-gated | VERIFIED `src/api/server.rs:95-118,385-427` |
| Agent-detection manifests | Remotely updated catalog with local overrides in `<config_dir>/agent-detection/` | VERIFIED `src/detect/manifest_update.rs:16-17`; DOC `socket-api.mdx:890-914` |

## 10. Open questions

1. **Windows pipe naming with isolated `XDG_CONFIG_HOME`.** The pipe name embeds the full path (`\\.\pipe\C:\...\herdr\sessions\<name>\herdr.sock`); the CLI test harness sets `XDG_CONFIG_HOME` on all platforms and `tests/windows_server_security.rs` exists, so this very likely works, but I did not run it. INFERRED from `src/ipc.rs:44-80`, `src/platform/windows.rs:36`, `tests/cli/harness.rs:180`.
2. **`pane.output_changed` via `events.subscribe`.** The `EventKind` exists and `events.wait` can match it, but there is no `Subscription` variant for it; subscribers get `pane.output_matched` (pattern-filtered) instead. Whether this is intentional throttling or an omission is undocumented. VERIFIED `src/api/schema/events.rs:16-85,173-178,216`.
3. **Plugin registry scope vs isolated profiles.** Because `plugins.json` and GitHub checkouts sit under `config_dir` (not `HERDR_CONFIG_PATH`), a research profile that only overrides `HERDR_CONFIG_PATH` will see and run the user's global plugins (including their `[[startup]]` hooks) inside the research server. Use `XDG_CONFIG_HOME` to avoid that. INFERRED from `src/persist/plugin_registry.rs:11-13`, `src/app/api/plugins/runtime.rs:161-201`.
4. **Long-lived plugin services.** No supervised daemon model: startup hooks are one-shot, action/event processes are fire-and-forget, and surviving processes are not protected from installation cleanup. A third-party capability needing a resident process should probably be an external API client (own supervisor) or a plugin pane, not a startup hook. DOC `plugins.mdx:219-222,256-257`; VERIFIED `runtime.rs:161-201`.
5. **Authorization boundary for third parties.** The API has no per-caller identity or scopes; a plugin or socket client can do anything the user can. The modular, non-replacing integration points are therefore: (a) plugin manifests (actions/events/panes/link handlers) calling back through `HERDR_BIN_PATH`; (b) an external NDJSON client using `events.subscribe` + authoritative reads; (c) state/metadata reporters (`pane.report_agent`, `pane.report_metadata`, `workspace.report_metadata`) which feed Herdr's own rollups without owning lifecycle; (d) `notification.show` for user-facing signals (rate-limited to 1/s, 80/240-char caps, delivered only when a client shell is attached or in-app toast is on); (e) `worktree.*` with request-scoped trust. VERIFIED `src/api/server.rs:328-520`, `src/server/headless/notifications.rs:222-275`, `src/app/api.rs:19,1271-1323`; DOC `socket-api.mdx:656-771`.
6. **`herdr --session <name> server` and `HERDR_CONFIG_PATH` propagation.** The headless server reads `Config::load()` once at start (`bootstrap.rs:30`) and `server.reload_config` re-reads the same path; whether the TUI-spawned daemon inherits `HERDR_CONFIG_PATH` is implied by env inheritance in `autodetect.rs:196-201` but not asserted by a test I found. INFERRED.
7. **Named-session sharing of agent-manifest overrides and `plugins.json`** is stated in the throwaway skill (`SKILL.md:122`) and confirmed for plugins by `tests/cli/plugins.rs:4,115-170`; the manifest-override directory path was only seen in docs (`socket-api.mdx:903`). DOC-ONLY for the latter.
