# Phase 1: Herdr and Harihi Works baseline (synthesis)

Detailed, line-cited evidence: `01-herdr-agent-integration-hooks.md`, `02-herdr-api-plugins-worktrees.md`,
`03-herdr-persistence-remote-security.md`. Provenance: `00-provenance.md`.

## 1. Authoritative development baseline

- Protected source `C:\herdr`: upstream Herdr **v0.9.5**, commit `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01`, local branch
  `dev/architecture` (identical content to the tag; no local source changes), clean tree. Verified by tree hash
  `8aa25836…` against the independent clone. No handoff archive existed; the clone was taken directly (`--no-local`).
- Release identity on this machine: `herdr 0.9.5`, Windows x86_64 release binary, byte-identical to the official GitHub
  asset (`00-provenance.md`). Protocol 22, endpoint generation 1, API schema version 1 (identical to the committed
  `docs/next/api/herdr-api.schema.json`).
- Build toolchain: absent (no Rust, Zig 0.16, `just`, MSVC/SDK). Only Python 3.12, Node 24, Git, gh are available.
  Consequence: Rust unit/integration tests and any from-source change cannot be compiled or run here (blocked, see §7).

## 2. Layers: upstream Herdr vs the Harihi Works deployment

| Layer | What is verifiable from this workspace | Status |
|---|---|---|
| Upstream Herdr source (v0.9.5) | fully, read-only + independent clone | **verified** |
| Herdr runtime on this machine | `C:\herdr\.local\<private>` (hash matches official release); three migrated profiles `default`, `triad`, `pilot` under `C:\herdr\.local\<private>` with their own config/state/sessions; `.local\<private>` launchers; migration records | **observed by name only**; not copied, not opened, not run |
| Harihi Works orchestration / governance | installed owner-edition `herdr` skill (SSH amendment `<owner-ssh-amendment>`), `<owner-entry-skill>` skill and desktop entry binding (fixed-principal bridge, policy commit `<policy-commit>`), `.local\<private>` directories | **not derivable from upstream source**; file names only. No sanitized modules were supplied, so no claim is made about working Harihi Works features |
| cross-machine link | paused by the owner (`.local\<private-migration-note>`); the remote machine's recovery service runs `--local-only` | **untouched**, as required |

What this research therefore evaluates: upstream Herdr's actual capabilities as the orchestration substrate, plus the
*constraints* the Harihi Works governance layer imposes (Herdr must stay the authority; `HERDR_ENV` is never fabricated;
SSH scope is owner-bounded; learned content must not gain authority). Harihi Works-specific adapters and roles were not
available in sanitized form and are listed as a request in the final assessment.

## 3. Active components and what works (verified in source; `01`, `02`, `03`)

- **Agent dispatch**: `agent start <name> --kind <kind> --pane <pane> [-- args]` types the kind's executable into an
  existing shell pane and polls detection until the expected kind is idle/done and interactive-ready (30 s default).
  Kinds include `claude`, `codex`, `gemini`, `cursor`, `grok` (alias `grok-build`), `agy`. `agent prompt --wait`,
  `agent wait`, `agent read` (incl. alternate-screen history for idle agents), `agent send-keys`, `agent explain`.
  Windows wraps launches in PowerShell `Get-Command`/`Start-Process`; Codex gets a paste boundary before Enter.
- **Detection**: bundled TOML manifests per agent with OSC title/progress, spinner, dialog and prompt-hint rules; hot
  reload from `<config_dir>/agent-detection/`; remote catalog check every 30 min unless `update.manifest_check=false`.
  Grok: full rule set (evidence from Grok Build 0.2.101 and 1.0.34). Gemini: 2 rules, "state only, less tested".
- **Native integrations** (`herdr integration install`): 17 targets; claude/codex/cursor/grok/antigravity each get **one**
  `SessionStart`-type hook that only reports the native session id for resume. No Stop/PreToolUse hooks. Lifecycle for
  these five comes from screen detection; `herdr:*` state reports are coerced to session-only. Gemini has no integration.
- **Hook merge semantics (Claude)**: CST-preserving edit of `~/.claude/settings.json`, strict JSON (comments, trailing
  commas, duplicate keys abort), idempotent, removal by exact command match; foreign hooks preserved. Gap: status reads
  only the script marker, so a third party deleting Herdr's entry is not detected.
- **API/CLI**: 102 methods, NDJSON over Unix socket or Windows named pipe `\\.\pipe\<path>`, one request per
  connection except subscriptions/waits; 26 lifecycle + 3 sampled event kinds; `pane.report_agent` /
  `pane.report_metadata` let external processes feed state and display tokens; `notification.show`.
- **Plugins (v1)**: `herdr-plugin.toml` with `[[build]]`, `[[startup]]`, `[[actions]]`, `[[events]]` (23 event kinds),
  `[[panes]]`, `[[link_handlers]]`; commands are argv arrays run as detached processes with `HERDR_BIN_PATH`,
  `HERDR_SOCKET_PATH`, plugin dirs and context JSON injected; registry is user-global `plugins.json`; no sandbox.
- **Worktrees**: `worktree.{list,create,open,remove}` over `git worktree`, workspace groups, restore gating, per-request
  `safe.directory` trust.
- **Persistence/recovery**: `session.json` v3 (tmp+fsync+rename, debounced, snapshots/backups), native resume by typed
  command (`claude --resume`, `codex resume`, `grok --resume` …), shutdown hooks on all three OSes.
- **Remote**: saved SSH machines (`endpoints.json`), strict host-key checking, private generated SSH config
  (`remote.manage_ssh_config`), API forwarding over an SSH bridge, experimental live handoff (Unix only).
- **Security**: socket/pipe ACLs (SDDL with integrity label on Windows; elevated servers reject unelevated clients by
  default), no API tokens or per-caller scopes, no audit log beyond tracing.
- **Memory / MCP**: none. Herdr has no cross-agent memory, notes, or learning feature and neither consumes nor exposes MCP.

## 4. Prototypes vs planned vs working (upstream)

| Item | State |
|---|---|
| Live handoff (`--handoff`) | experimental, Unix only |
| `[experimental]` config: `allow_nested`, `pane_history`, CJK IME options | experimental |
| Letta integration | experimental, kept out of the frozen enum pending an "agent registry" that does not exist yet |
| Gemini CLI | detection only, stale manifest (2026-06-10) |
| `pane.graphics.*` socket API | removed |
| Plugin API | documented as "an early interface" (v1) |
| Everything in §3 not listed above | released, tested in CI (Rust tests mostly Unix-only; Windows CI runs `just check` + ConPTY smoke) |

## 5. Governance requirements that bind this research

- Upstream `AGENTS.md`: lowercase conventional commits, no AI co-author lines, no `unwrap()` in production Rust, platform
  code isolated, frozen endpoint contracts, no edits to published docs/changelog in feature work, maintainer-only
  release/PR workflow (this workspace is neither a maintainer checkout nor a fork intended for PRs).
- Installed owner edition of the `herdr` skill: pane/session control only with genuine `HERDR_ENV=1`; never fabricate
  it; SSH transport maintenance per the owner amendment only; do not resume paused work.
- `<owner-entry-skill>` / <owner-entry-binding>: project tasks route through the fixed-principal bridge; this research deliberately did **not**
  submit through it, because the prompt forbids invoking production agents or live sessions and designates
  `C:\Herdr-dev` as the authorized location. That decision is recorded in the final assessment for the owner's review.

## 6. Windows and macOS communication (relevant facts)

Named pipe vs Unix socket transport; `.ps1` hook assets (UTF-8 stdin, `-ExecutionPolicy Bypass -File`) vs `.sh` assets
that embed Python and need `python3`; PATHEXT shim resolution for plugin commands; `HERDR_PANE_RUNTIME_ID` marker for
Git-Bash attribution; no `HERDR_AGENT` env hint on Windows; macOS adopts the user launchd context. Cross-machine calls
use `herdr --machine <label> …` relayed to `herdr --session <s> remote-api-bridge` over SSH with `BatchMode=yes`.

## 7. Blocked in this environment

Rust compilation and `cargo nextest`; Bun test suites; `just` recipes; live handoff tests; any native-agent or
cross-machine execution (not authorized). The Python maintenance suites ran (150 tests, 2 toolchain errors, 5 skips;
`research/07 §R1`).
