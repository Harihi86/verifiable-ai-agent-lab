# Evidence and reproducibility index

Every row names the claim, the artifact that supports it in this track, the command that produced it (as run in the
research workspace on 2026-10-24), the observed result, and the verification class from [`../README.md`](../README.md).
Full command transcripts with exit codes are in [`reports/07-test-runs.md`](reports/07-test-runs.md) (R1–R14).

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

## Isolation

| Claim | Artifact | Command | Observed | Class |
|---|---|---|---|---|
| Protected source, its Git metadata and user Herdr roots were not modified by research code; no research server left running | `reports/07 R10, R14` (narrative; raw JSON excluded) | `python prototypes/common/isolation_audit.py` | HEAD/tree/index unchanged; 16 session records all under the runtime root; other `herdr.exe` processes and a production service file changed by processes outside the project (reported, untouched) | offline verification |

## Reproduce

Commands above assume the research workspace layout described in `prototypes/README.md` (an isolated copy of the
official Herdr 0.9.5 release binary, Python 3.12, Node 24). Real-agent runs additionally need the agent CLI
installed and authenticated by the operator, spend that operator's tokens, and must be authorized explicitly; the
script's approval policy is documented in `prototypes/herdr-dispatch/integration/validate_real_grok.py`.
