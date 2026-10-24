# Phase 2: ECC assessment (synthesis)

Source: `C:\Herdr-dev\ecc` = `affaan-m/ECC` main @ `90606c8315ee09cafc303515c5f33024db6b9882` (2026-10-20), package
`ecc-universal` 2.2.3 (915 commits past the `v2.2.3` tag), MIT. Repository resolved via the GitHub API (no redirect,
not a fork). Static reading only; nothing was executed. Detailed evidence: `04`, `05`, `06`.

## 1. What ECC actually is

A Claude Code plugin bundle (also packaged for Codex, OpenCode, Cursor, Gemini, Pi, Kiro, Kimi, Qwen, Hermes, Zed,
Trae, Qoder) consisting of instruction assets (71 agents, 311 skills, 122 rule files, 97 legacy commands), a 27-entry
Claude hook graph, Node scripts (~99k lines under `scripts/`), an installer, a memory vault CLI/MCP server, docker-based
evaluation harnesses, and a Rust alpha (`ecc2/`, excluded from the package). Counts in its own docs disagree with
each other (`06 §7`).

## 2. Implementation maturity per focus area

| Area | Verified implementation | Maturity | Windows | Notes |
|---|---|---|---|---|
| Hooks | 27 entries, two dispatchers fan out to 6 Bash pre-hooks and 12 PostToolUse hooks; each entry embeds a 1.4 KB `node -e` resolver that scans `~/.claude/plugins/cache/**` when `CLAUDE_PLUGIN_ROOT` is unset (`04 §2`) | high churn (200 hook commits / 90 d); `js-yaml` dependency breaks marketplace installs (`04 §10`) | mostly OK; desktop-notify no-op; observer dead | per tool call: git ×3, bash+python ×4-5, formatters/`tsc` at Stop |
| Continuous learning (instincts/homunculus) | observation capture on by default to `~/.local/share/ecc-homunculus`; analysis via `claude --model haiku --print --allowedTools Read,Write` **disabled by default**; confidence math is prompt text, not code (`04 §3`) | design > implementation | native Windows: non-functional | learned instincts injected every SessionStart (≤6), `/learn` writes real skills |
| Memory | session summaries (Markdown, markers, 30-day prune, 8000-char reinjection); **Memory Vault** 2.3k lines: create-only Markdown with JSON frontmatter, 8 kinds, `trust: unreviewed` only, secret regexes, bounded lexical search, explicit recall, harness-scoped MCP (`04 §4`) | vault: solid, small, node-core; summaries: coupled to `utils.js` and optional `claude -p` | OK | vault is never auto-injected — the design matches the prompt's authority limits |
| Context optimization | `suggest-compact`, context monitor; profiles preview with `utf8 bytes / 4` ("not a tokenizer", `nativeTokens: null`) (`04 §5`) | heuristic | OK | no real measurement |
| Cross-harness adapters | one generated path (Claude → Pi via `ecc.agent-ir.v1`); everything else hand-maintained copies; Gemini/Qwen in-place `tools:` rewrites; no Grok, no Herdr/zellij; tmux only (`05 §2`) | low fidelity | n/a | the IR/frontmatter is reusable; the conversion scripts are not |
| Orchestration | prompt-level delegation; `gan-harness.sh` loops `claude -p`; `tmux-worktree-orchestrator.js` + `orchestrate-codex-worker.sh` spawn `codex exec` per worktree pane (`05 §3`) | shell-script level | Unix/tmux | a competing controller relative to Herdr |
| Worktrees | `git worktree add -b`, seed overlays, rollback, `git merge-tree` lifecycle classifier (`05 §4`) | fair | Unix-leaning | Herdr already has an API-level equivalent |
| Security scanning | `scan-supply-chain-iocs.js`: zero-dep IOC matcher (~150 bad package versions, ~80 indicators, AI-tool persistence paths, FP guards), CI cron every 6 h; validators check format/host-portability; `.gitleaksignore` without a gitleaks step (`05 §5`) | the most mature area | OK | pattern worth adopting; validates packages, not malice |
| Evaluation | tamper-evident journaling/receipts; `gate run` refuses execution by design; scoring only in prompts/GAN loop (`05 §6`) | incomplete | OK | nothing harness-neutral to adopt yet |
| Installer | `npm install --ignore-scripts` + `install-apply.js`; ID-tracked `settings.json` merges; `--enable-hooks` consent; `install-state.json` for exact uninstall; legacy Codex sync sets `git config --global core.hooksPath` (`05 §7`) | good | handled | not needed for Herdr |

## 3. Dependencies and network

Runtime deps `ajv`, `js-yaml`, `sql.js`, `@iarna/toml`; Node ≥ 18; Python 3.12 for observations/instinct CLI; bash for
observe hooks. No telemetry SDKs. Network from hook paths: `claude` CLI (model provider), HTTP(S) to the user's own
MCP URLs, loopback Plan Canvas, SSRF-guarded instinct import (`04 §6`).

## 4. Security risk register (condensed from `04 §8`, `05 §5`)

| Risk | Severity | Status in ECC |
|---|---|---|
| Haiku observer with unconfined Write fed by tool outputs (prompt injection → file writes) | high when enabled | off by default; dead on Windows |
| Transcript excerpts sent to the model provider by hooks (`claude -p`) | medium | on (PreCompact always; Stop by thresholds) |
| MCP health probe executes configured server commands on every `mcp__*` call | medium | on |
| Plaintext persistence of prompts, tool I/O, diffs under home dir | medium | on (observations in standard/strict profiles) |
| Learned/derived content gains authority (instinct injection, `/learn` skills, hookify block rules) | medium | on |
| Fail-closed blockers (exit 2 on any exception, GateGuard first-edit deny) | medium (availability) | on in std/strict |
| Inline resolver `require()`s code from the plugin cache | low-medium | on |
| Per-call process fan-out (perf, worse on Windows) | medium | on |
| `~/.ssh`/credential access | none found | — |

## 5. Licensing and attribution

Root MIT (Copyright (c) 2026 Affaan Mustafa). Exceptions: `skills/osint-investigation` CC-BY-SA-4.0 (excluded from any
reuse), `scripts/hooks/insaits-security-monitor.py` Apache-2.0 header, 8 supply-chain skills Apache-2.0, ~20 skills
credit third parties. No NOTICE file. Reuse of MIT material requires carrying the copyright and permission notice
(done in `prototypes/herdr-agent-memory/THIRD-PARTY-NOTICES.md`).

## 6. Relevance to Herdr and Harihi Works

Relevant core (`06 §2`): ~89 skills (orchestration 23, harness/loop 12, memory 8, evaluation 20, security 14,
context/cost 12); the reviewer/evaluator agents; the agent frontmatter schema; the vault format; the IOC scanner
pattern. Irrelevant: 78 domain skills (marketing, media, networking, crypto, healthcare …), 86 language stacks except
as dispatchable role content, Claude-only hook blockers, the tmux orchestrator.

Dispatch-target reality (`06 §8`): Codex is ECC's only non-Claude worker; Gemini appears only as a reviewer backend;
Cursor only as an install/hook target; Grok only as a conversation-export data source. ECC provides nothing for
"Grok Build under orchestration"; Herdr already does.

## 7. Maintenance cost

1,642 commits / 183 authors in 90 days; hooks reimplemented for 8 harnesses; 428 JS test files + 26 pytest files and a
13-lane CI with 80 % coverage gates (so quality controls exist), but the surface area and churn make wholesale adoption a
standing maintenance liability. Adopting *formats and patterns* instead of the runtime caps that cost at the size of
the adapted code (≈1,100 lines across the three prototypes here).
