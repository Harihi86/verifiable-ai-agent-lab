# ECC × Herdr integration research track

An engineering evaluation of whether capabilities from the open-source **ECC** agent-harness project
(`affaan-m/ECC`, `ecc-universal` 2.2.3, MIT) measurably improve **Herdr** (`herdrdev/herdr`, v0.9.5, Apache-2.0), a
Rust terminal workspace manager that starts and coordinates coding-agent CLIs (Claude Code, Codex, Cursor, Grok Build,
Gemini and others) in panes. The track was carried out in an independent research workspace with Herdr as the sole
orchestration, authorization and execution authority; ECC content entered only as reviewed data, never as a second
controller.

This material is imported from the research branch of an independent Herdr clone and is **not** part of the lab's
Python package. The lab keeps no dependency on Herdr; see [`LAB-INTEGRATION-POINTS.md`](LAB-INTEGRATION-POINTS.md) for
what the lab can reuse without one.

## Source and provenance

| Item | Value |
|---|---|
| Source repository / branch | independent Herdr clone, branch `research/ecc-integration`, based on upstream v0.9.5 commit `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01` |
| Source commits transferred | `89d920d2` (research, prototypes, handoff), `e7c1647b` (commit identity note), `5302348e` (**fix(detect)**: Grok 1.0.67 trust dialog + footer, bundled and published manifests), `496a564e` (Grok real-agent evidence and prototype updates), `022cbad3` (Codex real-agent evidence, generalized real-agent runner) — snapshot taken at `022cbad3` |
| ECC revision studied | `affaan-m/ECC` main @ `90606c8315ee09cafc303515c5f33024db6b9882` (2026-10-20), 915 commits past tag `v2.2.3` |
| Herdr binary used for backend tests | official v0.9.5 Windows release asset (sha256 `cd877c87…`), run only by absolute path with a scrubbed environment |
| Executor | Windows 11 (x64), Python 3.12, Node 24; **no Rust/Zig/MSVC toolchain**, so Herdr was never compiled here |
| Sanitization | see [`SANITIZATION-LOG.md`](SANITIZATION-LOG.md): user/host/e-mail identifiers, private deployment identifiers, owner-policy references and credential file names replaced by `<placeholders>`; raw isolation-audit JSON excluded; agent-home file lists reduced to counts |

Path mapping: the imported documents still use their original workspace-relative paths. `research/NN-*.md` →
[`reports/`](reports/), `outputs/ECC-Herdr-Final-Assessment.md` → [`FINAL-ASSESSMENT.md`](FINAL-ASSESSMENT.md),
`outputs/asset-gate/` and `outputs/real-grok-validation/` → [`evidence/`](evidence/), `prototypes/` →
[`prototypes/`](prototypes/). `C:\Herdr-dev\…` was the research workspace root; `C:\herdr` the protected, read-only
production checkout that was never modified.

## Status at a glance

| Item | Class | Where |
|---|---|---|
| Six sourced reports on Herdr (integration/hooks, API/plugins/worktrees, persistence/remote/security) and ECC (hooks/learning/memory, adapters/orchestration/security/eval, skills/agents inventory) | research finding | `reports/01`–`06` |
| Component comparison, classification (already implemented / worth adopting / worth improving / incompatible / unnecessary), adoption strategy | research finding | `reports/12`, `reports/13`, [`COMPONENT-INTEGRATION-ASSESSMENT.md`](COMPONENT-INTEGRATION-ASSESSMENT.md) |
| Prototype A — `research.agent-memory` Herdr plugin (cross-agent, per-project memory vault; event-driven capture; explicit non-executable recall) | tested prototype (23 unit tests; 18/18 disposable-backend checks) + real-agent verification with Grok Build and Codex | `prototypes/herdr-agent-memory/` |
| Prototype B — `agent-asset-gate` static pre-install reviewer for hooks/skills/agents/MCP configs/Herdr plugin manifests, plus Herdr hook-coexistence check | tested prototype (15 unit tests; corpus runs over ECC) | `prototypes/agent-asset-gate/`, `evidence/asset-gate/` |
| Prototype C — `herdr-dispatch`: ECC-format role packet → plan of Herdr-only steps → executor (now parameterized by agent kind) | tested prototype (8 unit tests; 9/9 simulated-backend checks) + real-agent verification with Grok Build and Codex | `prototypes/herdr-dispatch/` |
| Real-agent validation: Grok Build 1.0.67 started, prompted and read by Herdr; memory captured; handoff recorded | **real-agent verification** — two supervised runs | `reports/14`, `evidence/real-agent/` |
| Real-agent validation: Codex CLI 0.163.0-alpha.11.2 (desktop-app package, `--sandbox read-only --no-daemon`); Herdr's bundled Codex manifest reported the folder-trust prompt as `blocked`, approval was explicit, task completed | **real-agent verification in that one configuration** — three supervised runs, the third verified; the 0.159 alpha build could not do real work and Codex's default daemon mode was not used | `reports/15`, `evidence/real-agent/` |
| Detection vulnerability: Herdr 0.9.5 reports `idle` while Grok 1.0.67 shows its directory-trust dialog, so a prompt is typed into the dialog | research finding confirmed by real-agent run | [`SECURITY-FINDINGS.md`](SECURITY-FINDINGS.md) |
| Manifest compatibility fix (`trust_directory_dialog_blocked`, `Ctrl+x:shortcuts` footer) | offline verification (`agent explain --file`, upstream validator) + real-agent verification; **proposed integration** upstream (commit `5302348e` on the source branch) | `prototypes/herdr-dispatch/manifests/grok.toml`, `reports/14 §3` |
| Memory-capture title fix (terminal chrome filter, Grok and Codex footers), pipe-client shutdown fix, executor timeout derived from the step's own `--timeout` | tested prototype updates | `prototypes/herdr-agent-memory/src/lib/summarize.js`, `prototypes/common/herdr_socket.py`, `prototypes/herdr-dispatch/herdr_dispatch/executor.py` |
| Proposed Herdr core change: `integration status` should re-validate the Claude `settings.json` hook entry | proposed integration | `reports/13 §3` |
| Codex default daemon mode and npm/standalone distributions; Claude Code, Cursor, Gemini under the same validation | **not verified** | — |
| Production-ready functionality | **none** | — |

Nothing in this track was merged into Herdr, published as a release, installed globally, or run against a production
Herdr profile.

## Reading order

1. [`FINAL-ASSESSMENT.md`](FINAL-ASSESSMENT.md) — the handoff document: baselines, comparison summary, prototypes,
   test results and limits, security, measurements, rejected/deferred items, roadmap, reproduction, isolation audit, rollback.
2. [`reports/14-real-grok-validation.md`](reports/14-real-grok-validation.md) — the Grok live runs and the detection gap;
   [`reports/15-real-codex-validation.md`](reports/15-real-codex-validation.md) — the Codex live runs and packaging findings.
3. [`reports/07-test-runs.md`](reports/07-test-runs.md) — every command, exit code and observed output, R1–R17.
4. [`EVIDENCE-INDEX.md`](EVIDENCE-INDEX.md) — claim → artifact → command → class.
5. [`SECURITY-FINDINGS.md`](SECURITY-FINDINGS.md) and [`LAB-INTEGRATION-POINTS.md`](LAB-INTEGRATION-POINTS.md).
6. [`ROADMAP.md`](ROADMAP.md) — remaining validation and integration work.

## Licensing and attribution

Owner-authored documents and prototype code in this track are released under the repository's MIT license.
`prototypes/herdr-agent-memory` adapts ECC code (MIT): notice and modification list in its `THIRD-PARTY-NOTICES.md`.
`prototypes/herdr-dispatch/manifests/grok.toml` is a modified copy of a Herdr manifest (Apache-2.0): license text and
`NOTICE.md` sit beside it. ECC's CC-BY-SA skill was deliberately not reused.

## Excluded from this import

Private Herdr configuration and profiles, authentication material, the raw isolation-audit JSON (contains details of
unrelated processes and user directories), file-name lists from the agent's home directory, the owner's governance
bindings and SSH policy text, the Herdr and ECC source trees themselves (referenced by commit), and all disposable
runtime session directories.
