# ECC × Herdr research prototypes — review guide

Everything here runs **only** against a disposable Herdr backend started from the verified workspace binary
`C:\Herdr-dev\runtime\bin\herdr-0.9.5\herdr.exe` (sha256 `cd877c87…`, identical to the official v0.9.5 release and to
the production binary, which is never invoked). No command below touches `C:\herdr`, the user's `%APPDATA%\herdr`,
`%LOCALAPPDATA%\herdr`, `~/.claude`, or any live session. Nothing requires `HERDR_ENV`.

Prerequisites on this machine: Python 3.12 (`python`), Node 24 (`node`). No installs are needed.

## Layout

| Path | Purpose |
|---|---|
| `common/herdr_isolated.py` | isolation harness: scrubs `HERDR_*`/`XDG_*`, strips production PATH entries, sets `XDG_CONFIG_HOME`/`XDG_STATE_HOME`/`HERDR_CONFIG_PATH`/`HOME`/`TMP` under `runtime/sessions/<name>/`, writes the research config (updates, manifest checks, SSH config management, agent restore all off), records `logs/resolution.json` before any run |
| `common/herdr_socket.py` | raw NDJSON client for the Windows named pipe (`\\.\pipe\<socket path>`) |
| `common/smoke_backend.py`, `live_api_probe.py`, `debug_ws_events.py`, `measure_baseline.py` | backend smoke, event/agent-state probe, lifecycle-event check, latency/memory baseline |
| `herdr-agent-memory/` | **Prototype A** — Herdr plugin (`herdr-plugin.toml`, Node): cross-agent per-project memory vault |
| `agent-asset-gate/` | **Prototype B** — Python static gate for agent assets + Herdr hook coexistence check |
| `herdr-dispatch/` | **Prototype C** — role packet → Herdr-native dispatch plan → executor (Grok and others started by Herdr itself) |

## Reproduce (absolute paths; each command is independent)

```bash
cd C:\Herdr-dev\prototypes\common && python -m unittest -v tests.test_herdr_isolated
```

```bash
python C:\Herdr-dev\prototypes\common\smoke_backend.py
```

```bash
python C:\Herdr-dev\prototypes\common\measure_baseline.py --runs 20 --label baseline
```

```bash
cd C:\Herdr-dev\prototypes\herdr-agent-memory && node --test "tests/**/*.test.js"
```

```bash
python C:\Herdr-dev\prototypes\herdr-agent-memory\integration\test_plugin_backend.py
```

```bash
cd C:\Herdr-dev\prototypes\agent-asset-gate && python -m unittest -v tests.test_gate
```

```bash
python -I C:\Herdr-dev\prototypes\agent-asset-gate\asset-gate.py scan C:\Herdr-dev\ecc\hooks --md C:\Herdr-dev\outputs\asset-gate\ecc-hooks.md
```

```bash
cd C:\Herdr-dev\prototypes\herdr-dispatch && python -m unittest -v tests.test_dispatch
```

```bash
python C:\Herdr-dev\prototypes\herdr-dispatch\integration\test_dispatch_backend.py
```

Real-agent validation (spends the owner's Grok tokens; run only with authorization; Grok's own `~/.grok` state will change):

```bash
cd C:\Herdr-dev\prototypes\herdr-dispatch && python -X utf8 integration/validate_real_grok.py --max-turns 3 --manifest-override C:/Herdr-dev/prototypes/herdr-dispatch/manifests/grok.toml
```
Without `--manifest-override`, Herdr 0.9.5's bundled Grok rules misread the 1.0.67 trust dialog as idle (see
`research/14-real-grok-validation.md`). Offline classification of a captured screen needs no agent at all:
`herdr.exe --session <research> agent explain --file <screen.txt> --agent grok --json` with the patched manifest copied to
`<XDG_CONFIG_HOME>\herdr\agent-detection\grok.toml` of that research session.

Each backend run creates `C:\Herdr-dev\runtime\sessions\<prefix>-<timestamp>-<hex>\` containing `herdr-research.toml`,
`xdg-config\herdr\sessions\<session>\{herdr.sock marker, herdr-server.log, session.json}`, `xdg-state\herdr\…`, and `logs\`
(resolution record, CLI transcript, result JSON). Delete the directory to remove every trace of that run.

## Using the plugin in a research session by hand

```bash
python - <<'PY'
import sys; sys.path.insert(0, r"C:\Herdr-dev\prototypes\common"); import herdr_isolated as hi
rt = hi.IsolatedRuntime(session_name=hi.unique_session_name("manual")); rt.prepare(); print(rt.write_resolution_record()); print(" ".join(rt.command("server")))
PY
```
Start that `herdr.exe --session <name> server` command in a terminal with the environment from `rt.env()`, then from the
same environment: `herdr.exe --session <name> plugin link C:\Herdr-dev\prototypes\herdr-agent-memory`, create a
workspace, let a (real or simulated) agent settle, and `herdr.exe --session <name> plugin action invoke research.agent-memory.recall`.
Direct recall for orchestrators: `node C:\Herdr-dev\prototypes\herdr-agent-memory\src\cli.js recall <query> --project <repo> --json`
with `HERDR_PLUGIN_STATE_DIR` set to the plugin's state directory.

## Rollback

All research components live under `C:\Herdr-dev`. Removing them is `Remove-Item -Recurse C:\Herdr-dev\prototypes,
C:\Herdr-dev\runtime` (and optionally `research`, `outputs`, the `herdr` clone, and `ecc`). Nothing was linked into the
user's Herdr (`%APPDATA%\herdr\plugins.json`), no agent config was edited, no service or PATH change was made.
