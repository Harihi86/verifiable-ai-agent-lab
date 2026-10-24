# Evidence and reproducibility index

Every row names the claim, the artifact that supports it in this track, the command that produced it (as run in the
research workspace on 2026-10-24), the observed result, and the verification class from [`../README.md`](../README.md).
Full command transcripts with exit codes are in [`reports/07-test-runs.md`](reports/07-test-runs.md) (R1–R17).

## Baselines and provenance

| Claim | Artifact | Command / method | Observed | Class |
|---|---|---|---|---|
| Herdr baseline is v0.9.5 @ `2ecf19a9`, clone identical to protected source | `reports/00-provenance.md` | `git rev-parse HEAD^{tree}` on both | tree `8aa25836…` on both; worktrees/alternates none | research finding |
| ECC pinned at `90606c83` (`ecc-universal` 2.2.3 + 915 commits), MIT, no redirect | `reports/00-provenance.md`, `reports/11 §1` | `gh api repos/affaan-m/ECC`, `git log -1` | as stated | research finding |
| Test binary is the official v0.9.5 release | `reports/00-provenance.md` § Binary verification | `gh release view v0.9.5`, `sha256sum` | zip `d2c6c9c9…` matches release digest; exe `cd877c87…` | research finding |
| Binary's API schema equals the committed schema | `reports/07 R3` | `herdr api schema --output` vs `docs/next/api/herdr-api.schema.json` | sha256 prefix `9e2af207` on both | offline verification |

## Herdr and ECC analysis

| Claim | Artifact | Method | Class |
|---|---|---|---|
| Herdr's five in-scope integrations register only a session-identity hook; lifecycle comes from screen manifests; Gemini is detection-only | `reports/01` (path:line cited) | source reading of `src/integration/*`, `src/detect/*` | research finding |
| Herdr exposes 102 API methods, 23 plugin-hookable event kinds, plugins run as detached child processes with `HERDR_BIN_PATH`; no per-caller scopes | `reports/02` | source reading | research finding |
| Herdr has no memory/knowledge feature and no MCP | `reports/03 §3,5` | exhaustive grep + reading | research finding |
| ECC hook graph: 27 entries, inline `node -e` resolvers, per-call git/python spawns, `claude -p` summaries, fail-closed blockers | `reports/04 §2,8` | source reading | research finding |
| ECC Memory Vault is create-only Markdown with JSON frontmatter, secret refusal, explicit recall | `reports/04 §4B` | source reading | research finding |
| ECC has no Grok/Cursor dispatch; Codex only via a tmux shell driver; cross-harness conversion is one generated path | `reports/05 §2-3`, `reports/06 §8` | source reading | research finding |
| Component classification and adoption strategy | `reports/12`, `reports/13`, `COMPONENT-INTEGRATION-ASSESSMENT.md` | synthesis of the above | research finding |

## Prototype tests (unit, contract, disposable backend)

| Claim | Artifact | Command | Observed | Class |
|---|---|---|---|---|
| Isolation harness strips `HERDR_*`/`XDG_*`, removes production PATH entries, confines every root | `prototypes/common/tests/test_herdr_isolated.py` | `python -m unittest tests.test_herdr_isolated` | 6/6 | tested prototype |
| A disposable Herdr backend runs fully isolated; no production or user Herdr root changes | `reports/07 R3` | `python prototypes/common/smoke_backend.py` | exit 0; outside roots unchanged | tested prototype |
| Baseline latency/memory | `reports/07 R4` | `python prototypes/common/measure_baseline.py --runs 20` | start→ready 438 ms; `workspace list` median 43.0 ms; ~18.5 MiB | measurement |
| Named-pipe API client, event subscription shapes, custom agent state reporting | `reports/07 R5` | `live_api_probe.py`, `debug_ws_events.py` | pane subscriptions need `pane_id`; lifecycle events use underscore names | tested prototype |
| Memory plugin (A) format/store/summarizer/transitions/capture/CLI | `prototypes/herdr-agent-memory/tests/*.test.js` | `node --test "tests/**/*.test.js"` | 22/22 (21/21 before the chrome filter) | tested prototype |
| Memory plugin links into Herdr, captures on a simulated `working→idle`, reports a pane token, recall action works | `reports/07 R7`, `prototypes/herdr-agent-memory/integration/test_plugin_backend.py` | `python integration/test_plugin_backend.py` | 18/18; capture 652 ms after settle; `workspace list` 42.5 ms vs 43.0 ms baseline | tested prototype |
| Asset gate (B) rules, structural checks, coexistence, CLI exit codes, fixture capping | `prototypes/agent-asset-gate/tests/test_gate.py` | `python -m unittest tests.test_gate` | 15/15 | tested prototype |
| Asset gate triage of ECC: hooks/scripts/agents/skills "review", `.mcp.json` "allow" | `evidence/asset-gate/ecc-*.md`, `reports/07 R8` | `python -I asset-gate.py scan <ecc dir> --md …` | counts per rule; 599 skill files in 4.6 s | tested prototype (corpus run) |
| Dispatch (C) role parsing, plan invariants (Grok via Herdr, no Codex, every step `authority: herdr`), dry run | `prototypes/herdr-dispatch/tests/test_dispatch.py` | `python -m unittest tests.test_dispatch` | 8/8 | tested prototype |
| Dispatch plan executes against a disposable backend with a simulated agent, handoff lands in the vault | `reports/07 R9`, `integration/test_dispatch_backend.py` | `python integration/test_dispatch_backend.py` | 9/9; ≈1.5 s | tested prototype |

## Real-agent verification (Grok Build 1.0.67 only)

| Claim | Artifact | Command | Observed | Class |
|---|---|---|---|---|
| Herdr starts, detects, prompts and reads Grok Build with no other agent involved | `evidence/real-agent/realgrok-20261024-170910-8091d7.json`, `reports/14 §2` | `python integration/validate_real_grok.py --max-turns 3` | 12/12 checks; detected ≈1.1 s after start; turn 7.5 s; correct answer | real-agent verification |
| Bundled manifest reports `idle` on the 1.0.67 trust dialog; prompt's first key answered it | same JSON, screen `00-after-agent-start`; fixture `evidence/real-agent/fixtures/grok-1.0.67-trust-dialog-screen.txt` | timeline + screen capture | `idle` at 6.5 s while dialog shown; echoed prompt missing its first letter | real-agent verification |
| Patched manifest classifies the trust screen as `blocked` and the post-turn screen as `idle` | `reports/14 §3`, fixtures above, `prototypes/herdr-dispatch/manifests/grok.toml` | `herdr agent explain --file <fixture> --agent grok --json` with the manifest as `XDG_CONFIG_HOME/herdr/agent-detection/grok.toml` | bundled: `idle`/no rule; patched: `blocked` (`trust_directory_dialog_blocked`), `idle` (`prompt_hints_idle`) | offline verification |
| Patched manifest passes Herdr's own validator | `reports/14 §3`, `reports/07 R13` | `python scripts/agent_detection_manifest_check.py` (bundled + published copies) | "agent detection manifests ok"; 13/13 checker unit tests | offline verification |
| With the patch, `agent start` reports the trust prompt, the approval policy answers it explicitly, the prompt arrives intact, memory capture and handoff follow | `evidence/real-agent/realgrok-20261024-172705-b30c8d.json`, `reports/14 §4` | `… --manifest-override <patched grok.toml>` | 13/13; `agent_not_ready` → `blocked` → key `y` → `idle` 0.2 s later; turn 8.9 s | real-agent verification |
| Memory plugin captures a real agent's settle | both JSON files (`memory_doc_head`), `reports/14` | event hook | 2,343 / 1,661-char documents with `source_agent: "grok"` | real-agent verification |

## Real-agent verification (Codex CLI 0.163.0-alpha.11.2, one configuration)

| Claim | Artifact | Command | Observed | Class |
|---|---|---|---|---|
| No standalone Codex CLI is installed; the desktop app ships two CLI builds; the 0.159 alpha exits without `--no-daemon` and cannot read files with it | `reports/15 §1`, `evidence/real-agent/realcodex-20261024-174232-616d36.json`, `…-174616-9494c9.json` | `python integration/validate_real_grok.py --kind codex --pane-path-prepend <app bin dir>` | run 1 aborted (process exited, `unknown`); run 2 13/13 script checks but the agent reported its tool host unavailable | real-agent verification (negative result) |
| Herdr's bundled Codex manifest reports the folder-trust prompt as `blocked`; `agent start` returns `agent_not_ready`; the policy answers `1` "Trust and continue" then `enter` | `evidence/real-agent/realcodex-20261024-174838-7413cb.json`, fixture `evidence/real-agent/fixtures/codex-0.163-trust-dialog-screen.txt`, `reports/07 R17` | same script, complete package dir, flags `--sandbox read-only --no-daemon` | blocked 3.5 s after start; idle 2.9 s after approval; no manifest change needed | real-agent verification |
| The complete package completes the task through Herdr; memory captured; handoff recorded | same JSON, `reports/15 §2,5` | same | 13/13; `Called Read README.md`, three correct bullets, no files changed; capture 2,105 chars `source_agent: "codex"`; recall 1 memory / 1,653 chars vs raw 1,590 | real-agent verification |
| Executor timeout race and preflight PATH resolution fixed during the runs | `prototypes/herdr-dispatch/herdr_dispatch/executor.py`, `validate_real_grok.py`, `reports/07 R15` | `python -m unittest tests.test_dispatch` | 8/8 | tested prototype |
| Summarizer filters Codex footer chrome | `prototypes/herdr-agent-memory/tests/summarize.test.js` | `node --test "tests/**/*.test.js"` | 23/23 | tested prototype |

Not verified for Codex: default daemon mode (the app's shared app-server), npm/standalone-installer distributions.

## Integration candidate (built Herdr branch)

Artifacts are under [`integration-candidate/`](integration-candidate/); its `SANITIZATION-LOG.md` lists every exported
file. Commands are in `INTEGRATION-CANDIDATE.md` §3.

| Claim | Artifact | Command | Observed | Class |
|---|---|---|---|---|
| The candidate builds on Windows without MSVC | `evidence/build/build-gnu-release-*.log` | `cargo zigbuild --release --target x86_64-pc-windows-gnu --locked` | exit 0; final binary sha256 `c7710ce4…` | offline verification |
| fmt and clippy pass | `evidence/build/lint-gnu.log` | `cargo fmt --check`; `cargo-zigbuild clippy --all-targets --locked -- -D warnings` | both exit 0 | offline verification |
| Herdr's Rust suite passes on the candidate sources | `evidence/rust-tests/test-isolated-final.json`, `env-dependent-test-with-variable-unset.txt` | `run_isolated_tests.py` (one process per test, sandboxed profile) | 3448/3449; the remaining test passes with `NoDefaultCurrentDirectoryInExePath` unset | offline verification |
| Maintenance tests pass | `evidence/rust-tests/maintenance-tests-final.log` | `just test` Python modules | 150 run, 5 skipped, OK | offline verification |
| Two agent dialogs that v0.9.5 calls idle are blockers on the candidate | `evidence/detection-fixtures/` | `test_fixtures.py` with `agent explain --file` | v0.9.5: Grok trust dialog and Codex model picker idle; candidate: all 5 as expected | offline verification |
| Backend suites (plugin, plugin lifecycle, dispatch, asset gate) | `evidence/backend/{v0.9.5,candidate}/` | `integration/test_*_backend.py` | 19/19, 23/23, 9/9, 12/12 on both binaries | tested integration candidate |
| Install, upgrade, kill and restart, rollback, uninstall | `evidence/lifecycle/candidate-lifecycle.json` | `tools/test_candidate_lifecycle.py` | 22/22 | tested integration candidate |
| Real agents under Herdr on the candidate | `evidence/real-agent/*.json` | `validate_real_grok.py --kind grok/codex/claude` | Grok 14/14, Codex `--no-daemon` 14/14 (picker blocked live), Claude Code 14/14; Codex default daemon mode not usable | real-agent verification |

## Isolation

| Claim | Artifact | Command | Observed | Class |
|---|---|---|---|---|
| Protected source, its Git metadata and user Herdr roots were not modified by research code; no research server left running | `reports/07 R10, R14` (narrative; raw JSON excluded) | `python prototypes/common/isolation_audit.py` | HEAD/tree/index unchanged; 16 session records all under the runtime root; other `herdr.exe` processes and a production service file changed by processes outside the project (reported, untouched) | offline verification |

## Reproduce

Commands above assume the research workspace layout described in `prototypes/README.md` (an isolated copy of the
official Herdr 0.9.5 release binary, Python 3.12, Node 24). Real-agent runs additionally need the agent CLI
installed and authenticated by the operator, spend that operator's tokens, and must be authorized explicitly; the
script's approval policy is documented in `prototypes/herdr-dispatch/integration/validate_real_grok.py`.
