# Real-agent validation: Grok Build 1.0.67 under Herdr 0.9.5 (owner-authorized, 2026-10-24)

Authorization (owner, in chat): "run the memory plugin and dispatch plan against a real Grok Build process in an
isolated named research session with a throwaway repository, no production profiles."

Script: `prototypes/herdr-dispatch/integration/validate_real_grok.py`. Raw evidence per run:
`runtime/sessions/<session>/logs/{real-grok-validation.json, dispatch-plan.json, dispatch-cli.log, cli.log}` and copies
under `outputs/real-grok-validation/`.

## 1. Setup that was common to both runs

- Herdr: workspace release binary 0.9.5, fresh named session, isolated XDG roots, research config (no update or
  manifest network checks, no SSH config management, no agent restore). Memory plugin `research.agent-memory` linked
  into that session only. `herdr integration install grok` was **not** run; Grok's own `~/.grok` config was never edited
  by this project.
- Grok: `<USERPROFILE>\.grok\bin\1.0.67\grok.exe` (`grok 1.0.67 (2fe064390d07)`) resolved from PATH inside the
  scrubbed research environment; it ran as the user with its existing login (nothing copied). Flags passed by the plan
  after `--`: `--no-subagents --disable-web-search --max-turns 3`. Default model as shown by its UI: "Grok 4.7 (high)".
- Throwaway repository: created per run under `runtime/sessions/<session>/tmp/throwaway-repo` (README, one Python file,
  one commit). Role: a minimal read-only `grok-probe` packet. Task: summarize README.md in three bullets.
- Approval policy (automatic, logged): answer only a folder-trust prompt for the throwaway path or a read-only tool
  permission inside it, choosing an affirmative option that is not "always/yolo/all"; anything else aborts.

## 2. Run 1 — bundled Herdr manifests (session `realgrok-20261024-170910-8091d7`)

Result: 12/12 checks, but with a **detection gap** that the checks of that version did not cover.

| Event | Time from script start |
|---|---|
| `agent start grok-probe --kind grok …` issued | 1.9 s |
| Herdr `pane.agent_detected` (process `grok.exe`) | 3.0 s |
| Herdr `pane.agent_status_changed` → **idle** (and `agent start` returned idle, `interactive_ready: true`) | 6.5 s |
| `agent prompt … --wait` issued | 6.7 s |
| → working | 7.5 s |
| → idle (turn done, "Worked for 7.6s") | 15.0 s |

What the screen showed when Herdr said "idle": Grok Build 1.0.67's directory-trust dialog ("Do you trust the contents of
this directory?" … "Yes, proceed   y" / "No, quit   n"). The bundled `grok.toml` recognises option lists with a `┃ n (○)`
gutter and footer hints, not this layout, and the window title was the idle "grok", so `osc_title_idle` won. Consequence:
Herdr's `agent_blocked` safeguard never engaged, `agent prompt` typed the role prompt into the dialog, its leading **`Y`**
answered "Yes, proceed", and the remainder went into the input box (the echoed prompt starts with "ou are acting…").
Trust for the throwaway path was therefore granted by an accidental keystroke, not by the approval policy. A prompt
starting with `n` would have quit Grok. The agent then completed the task correctly (three bullets, "Nothing was changed").

Memory plugin on a real agent: the `working → idle` transition fired the hook; a 2,343-char document was written
(`source_agent: "grok"`), the pane showed `memory=1 notes`, recall returned it. Weakness found: the capture title was
taken from the footer line ("Shift+Tab:mode │ Ctrl+x:shortcuts") because the summarizer did not filter terminal chrome.

## 3. Fix prepared the way `AGENTS.md` prescribes (manifest hot-reload loop)

Captured screens were saved and classified offline with `herdr agent explain --file <screen> --agent grok --json`
(no server):

| Screen | bundled rules | patched manifest |
|---|---|---|
| trust dialog | `idle` (no rule matched; fallback) | **`blocked`** via new `trust_directory_dialog_blocked` (priority 1195) |
| post-turn prompt | no visible rule (file mode has no OSC title) | **`idle`** via `prompt_hints_idle` extended to `Ctrl+x:shortcuts` |

Patched manifest: `prototypes/herdr-dispatch/manifests/grok.toml` (version `2026.10.24.1`): adds the trust-dialog rule,
and lets `esc_cancel_hints_working` / `prompt_hints_idle` accept 1.0.67's `Ctrl+x:shortcuts` footer alongside the older
`Ctrl+.:shortcuts`. The same change is staged in the research clone in both `src/detect/manifests/grok.toml` and
`distribution/agent-detection/grok.toml` (kept aligned as `AGENTS.md` requires); `python scripts/agent_detection_manifest_check.py`
reports `agent detection manifests ok` and `scripts.test_agent_detection_manifest_check` passes 13/13. It is a
**proposed upstream change**: data-only, validated by the upstream checker and by the live run below, not compiled into a
binary here. In the research session it was installed only as a local override under the isolated
`XDG_CONFIG_HOME/herdr/agent-detection/grok.toml`.

The summarizer gained a chrome filter (footer key hints, box borders, telemetry banner lines); 22/22 unit tests.

## 4. Run 2 — patched manifest as local override (session `realgrok-20261024-172705-b30c8d`)

Result: **13/13 checks**, including the new check that `agent start` must report the trust prompt.

| Event | Time from script start |
|---|---|
| `agent start` issued | 2.3 s |
| `pane_agent_detected` | 3.5 s |
| → **blocked** (trust dialog recognised); `agent start` returned `agent_not_ready` ("blocked during startup") | 7.0 s |
| policy: send key `y` for option "Yes, proceed" (trust dialog for the throwaway path) | 7.4 s |
| → idle | 7.6 s |
| `agent prompt --wait` issued | 9.5 s |
| → working | 10.2 s |
| → idle ("Worked for 8.9s") | 19.0 s |

The full prompt was delivered intact (echo begins "> You are acting as the role described below…"). Answer: the same
three correct bullets. `agent read` 1,643 chars; memory capture 1,661 chars (13 lines after chrome filtering) with
`source_agent: "grok"`; handoff written; recall for "README" returned 2 memories (3,035 chars, i.e. larger than the raw read
for a one-turn session; the benefit is the fixed 8,000-char ceiling across many turns, not savings on a single short turn).

## 5. Side effects on Grok's own state (not Herdr's, not the research runtime)

Grok wrote to `~/.grok` as any interactive start does — reported, not touched by this project:
- run 1: 977 files added (952 of them a shallow Git clone of the xAI plugin marketplace into `marketplace-cache/`, i.e.
  Grok's own network activity at startup; `official_marketplace_auto_installed = true` in its config), a session directory
  for the throwaway cwd, `memtrace/*.jsonl`, `CHANGELOG.*`, `active_sessions.json`; 8 modified (`<credential-file>` token refresh,
  `logs/unified.jsonl`, caches, `trusted_folders.toml`, `worktrees.db`).
- run 2: 26 added, 21 modified (same classes; marketplace caches refreshed).
- `~/.grok/trusted_folders.toml` now contains two entries for the two throwaway paths
  (`C:\Herdr-dev\runtime\sessions\realgrok-…\tmp\throwaway-repo`). They are harmless but stale once the runtime directory is
  deleted; removing them is the owner's call (this project does not edit Grok's config).
- The pre-installed Herdr hook in `~/.grok/hooks/herdr.json` did not produce a `pane.report_agent_session` on the research
  server during either run (no log line); Herdr's grok detection worked without it, as `research/01 §4` predicted.

## 6. Conclusions

1. Herdr 0.9.5 starts and drives Grok Build 1.0.67 directly: detection in ~3 s, prompt submission, lifecycle waits and
   reads all work, with no other agent involved. The dispatch prototype's plan executed end to end twice.
2. The bundled Grok manifest has drifted against 1.0.67 in two places (trust dialog, shortcuts footer). The first is a
   safety issue: an orchestrator relying on `agent_blocked` can type a prompt into a trust prompt. The patched manifest
   closes both and is validated offline and live.
3. The memory plugin captures a real agent's settle with no model call; the chrome filter was needed for useful titles.
4. Costs: two one-turn Grok sessions (context shown by Grok: ~15K of 256K each), no file changes by the agent.
