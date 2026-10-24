# Security assessment: ECC integration candidate

Scope: the Grok detection fix, the Windows GNU build path, and the three integration components on branch
`integration/ecc-candidate`. Herdr's own threat model is unchanged by this branch except where stated.

## 1. Trust boundaries that Herdr already has (and that this branch relies on)

| Boundary | Mechanism | Consequence for integrations |
|---|---|---|
| Who can talk to the server | Windows named pipe with an SDDL granting the user and SYSTEM; elevated servers reject unelevated clients by default; Unix sockets `0600` | Any process running as the same user can call every API method. There are no per-caller scopes. |
| Plugins | Manifest-declared argv commands run as detached processes with `HERDR_SOCKET_PATH`, `HERDR_BIN_PATH`, `HERDR_ENV=1` and plugin dirs injected; `[[startup]]` runs after every restore; `[[build]]` runs at GitHub install | A plugin has the full authority of the user and of the Herdr API. Herdr does not sandbox it. |
| Agent input | `agent prompt` refuses to type while Herdr believes the agent is `blocked` | This guard is only as good as the agent's detection manifest (see §3). |
| Approvals inside agents | Answered by whoever sends keys to the pane | Nothing in Herdr distinguishes an operator's keystroke from a script's. |

The integrations therefore restrict themselves in code; they cannot rely on Herdr to restrict them.

## 2. Component privilege boundaries (enforced and tested)

| Component | What it may do | What it can never do | Enforcement | Tests |
|---|---|---|---|---|
| `agent-memory` plugin | `herdr pane get/list/read`, `herdr agent get/read`; raw `pane.report_metadata` (display-only tokens); read/write only under `HERDR_PLUGIN_STATE_DIR` | prompt or start agents, send keys/text/input, run pane commands, change layout, link/install plugins or integrations, stop servers, spawn other programs, evaluate code | allowlist in `src/lib/herdr-client.js` (`ALLOWED_CLI`, `ALLOWED_RAW_METHODS`, `PrivilegeBoundaryError`); no other module imports `child_process` | `tests/boundary.test.js` (denied-verb matrix, raw-method denial, source scan for `child_process`/`eval`) |
| `agent-memory` content | store text with provenance; return text on explicit recall | be injected into an agent automatically; gain trust; be executed | `trust` enum has only `unreviewed`; recall is wrapped in a "HISTORICAL REFERENCE ONLY … not live instructions … do not execute" header; recall only via explicit action/CLI; secrets redacted before write and refused if still present | `boundary.test.js` (hostile body stored verbatim, recalled inside the guard, trust cannot be raised), `vault-format.test.js`, `vault-store.test.js` |
| `agent-memory` integrity | detect tampering, foreign documents and partial writes | silently trust a modified document | per-project append-only `manifest.jsonl` with SHA-256 per document; `verify`/`fsck` quarantine mismatches (moved, never deleted); stale temp files removed at startup | `governance.test.js` |
| `dispatch` executor | Herdr verbs `workspace create`, `worktree create`, `agent start/prompt/wait/read/get`; in `--simulate` only `pane run/wait-output/report-agent`, `agent rename`; external command only `node <…>/cli.js handoff` | answer dialogs (`agent send-keys`), raw pane input, close panes/workspaces, control the server, install plugins/integrations, run agent CLIs directly | `check_step_authority` in `herdr_dispatch/executor.py` checks every rendered step, including plans loaded from JSON | `tests/test_dispatch.py` (`AuthorityGuardTests`: allowed/denied matrix, simulate-only verbs, real plans pass, tampered plan refused, executor source names no agent executable) |
| `asset-gate` | read files under the reviewed path; on explicit approval call Herdr's own `plugin link` / `plugin install --ref <reviewed commit>` | execute reviewed content; install without an approval matching the exact report digest; install a `deny` result without a logged override reason; use a relative or PATH-resolved `herdr` | `asset_gate/review.py` (`install_after_approval`, `herdr_invocation`); the install command re-reviews and compares digests; every attempt appended to `approvals.jsonl` | `tests/test_gate.py` (`ReviewPluginTests`); `integration/test_gate_backend.py` against a real server (no approval, wrong digest and post-review modification refused before Herdr is called) |

Residual risk that the components cannot remove: they run as the user. A compromised Node or Python runtime, or a
malicious edit to the plugin directory, bypasses every in-code allowlist. The asset gate's `review-plugin` exists
to make that class of change visible before installation, and its content digest makes later changes detectable.
A linked plugin keeps running from its directory, so a change made after `plugin link` is not prevented; re-run
`review-plugin` and compare `content_sha256` with the approval record to detect it.

## 3. Detection drift is a security issue (fixed for Grok 1.0.67)

When a manifest misclassifies an approval or trust dialog as `idle`, `agent prompt` types into the dialog. Observed
live with Grok Build 1.0.67 on Herdr 0.9.5: the prompt's first letter answered "Yes, proceed". This branch bundles the
fix (`src/detect/manifests/grok.toml` 2026.10.24.1, kept identical in `distribution/agent-detection/`), adds
engine-level regression tests for the rule shapes (`src/detect/manifest/tests.rs`), and adds captured-screen fixtures
with a binary check (`integrations/detection-fixtures/test_fixtures.py`, kept outside Herdr's own test suite as
AGENTS.md requires), which fails on v0.9.5 and passes on the candidate. Codex 0.163's trust dialog is already handled by the bundled Codex manifest. Each new agent build can drift
again; the fixture check is the regression net and needs new fixtures per agent version.

## 4. Supply chain

| Item | Source | Verification |
|---|---|---|
| Rust 1.96.1 | rustup (installer SHA-256 matched the published `.sha256`) | rustup component hashes |
| Zig 0.16.0 | ziglang.org | SHA-256 from ziglang's index |
| cargo-zigbuild 0.24.0 | GitHub release | SHA-256 matched the release digest |
| arocc (Zig dependency of libghostty-vt) | GitHub tarball fetched with curl (Zig's own HTTP client failed on GitHub's headers) | Zig package hash matched `translate_c`'s manifest |
| crates | crates.io via `Cargo.lock` (`--locked`) | cargo checksums |

All tools live under a workspace toolchain directory; no global PATH, registry or security setting was changed.
cargo-zigbuild's wrapper cache is redirected there with `CARGO_ZIGBUILD_CACHE_DIR`.

## 5. Findings from running the upstream test suite on this host

- Herdr's unit tests mutate process-wide `XDG_*` variables under several different locks. They are correct only with
  one process per test (`cargo nextest`, as `just test` uses). Under plain `cargo test`, one failure poisons the locks
  and cascades.
- Several tests clear `XDG_*` to exercise platform defaults. A debug test run therefore writes `herdr-dev` directories
  into the real `%APPDATA%` and `%LOCALAPPDATA%`. The runner in `tools/run_isolated_tests.py` sandboxes those roots. One
  leftover override written by a test changed another test's outcome until the residue was removed.
- `NoDefaultCurrentDirectoryInExePath=1` in the parent environment (a cwd-hijacking mitigation) makes
  `windows_plugin_pane_commands_resolve_from_plugin_root_with_cwd_override` fail, because its fixture runs `cmd /c
  slot.cmd` from the current directory. The product behaviour is correct Windows semantics; the test assumes the
  default environment.
- A maintenance test read UTF-8 sources with the locale code page and failed on a zh-CN host; fixed on this branch.

## 6. Not assessed

Cross-machine (SSH) operation, multi-user hosts, and an MSVC build of the candidate were not exercised. The Windows
GNU build differs from the official MSVC artifact (CRT, unwinding); it is suitable for development and testing, not as
a release artifact.
