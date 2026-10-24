# Herdr integrations (ECC evaluation candidate)

Optional components derived from the ECC × Herdr evaluation. None of them is compiled into the `herdr` binary, and none
of them is a second controller: every agent, pane and session operation goes through Herdr's own CLI/API, and Herdr's
detection, lifecycle, authorization and session persistence stay authoritative.

| Directory | What it is | Runtime | How it enters Herdr |
|---|---|---|---|
| `agent-memory/` | Cross-agent, per-project memory vault: captures a summary when Herdr reports a completed turn, explicit non-executable recall, operator review (reject / supersede / restore), retention, provenance verification with quarantine, crash recovery | Node ≥ 18, node-core only | Herdr plugin (`herdr-plugin.toml`): `[[startup]]`, `[[events]] on = "pane.agent_status_changed"`, actions |
| `asset-gate/` | Static, read-only pre-install review of plugins, skills, agent definitions, hooks and MCP configs; `review-plugin` binds an explicit operator approval to the exact reviewed content before calling Herdr's own `plugin link`/`plugin install` | Python ≥ 3.11, stdlib only | Operator CLI run before installation |
| `dispatch/` | Role packet (agent-definition Markdown) → plan of Herdr CLI steps → executor; plans are limited to an allowlist of Herdr verbs | Python ≥ 3.11, stdlib only | Operator or orchestrator CLI; inside a Herdr pane it uses the injected `HERDR_BIN_PATH` and session |
| `common/` | Test harness: isolated Herdr runtime (scrubbed `HERDR_*`/`XDG_*`, fresh config/state roots, absolute binary), named-pipe client, probes, isolation audit | Python | Tests only |
| `tools/run_isolated_tests.py` | Runs Rust test binaries one process per test (nextest's model) with sandboxed profile roots | Python | Tests only |
| `tools/candidate_install.py` | Installs, verifies (SHA-256 manifest), activates, rolls back and uninstalls Herdr builds inside a dedicated integration environment; never touches PATH, the registry or a user profile | Python | Operator CLI |
| `tools/test_candidate_lifecycle.py` | One session served by the release, then the candidate, then the release again: install, upgrade, abnormal termination, rollback, clean uninstall | Python | Tests only |
| `detection-fixtures/` | Captured agent screens with expected states, classified through a built binary (`agent explain --file`); the drift net for specific agent builds, kept outside Herdr's own test suite as AGENTS.md requires | Python | Tests only |

Verification status is recorded in `INTEGRATION-CANDIDATE.md`. Nothing here is production-ready: the components are
tested prototypes and a proposed integration.

## Tests

```bash
cd integrations/agent-memory && node --test "tests/**/*.test.js"
cd integrations/asset-gate && python -m unittest tests.test_gate
cd integrations/dispatch && python -m unittest tests.test_dispatch
cd integrations/common && python -m unittest tests.test_herdr_isolated
cd integrations/tools && python -m unittest tests.test_candidate_install
HERDR_TEST_BINARY=<abs herdr.exe> python -m unittest discover -s integrations/detection-fixtures -p 'test_*.py'
```

Backend tests start a disposable Herdr server in fresh config/state roots. They use `HERDR_RESEARCH_BINARY`
(absolute path of the binary under test) and `HERDR_RESEARCH_RUNTIME_ROOT` (where sessions and logs go):

```bash
python integrations/agent-memory/integration/test_plugin_backend.py
python integrations/agent-memory/integration/test_lifecycle_backend.py
python integrations/dispatch/integration/test_dispatch_backend.py
python integrations/asset-gate/integration/test_gate_backend.py
```

Simulated agents in these tests are held by a short-lived Node occupant process in the pane. Herdr clears a
self-reported agent once its pane's shell has no child process again, so a report made after a plain `echo` races
that check.

`dispatch/integration/validate_real_grok.py --kind grok|codex|claude` drives a real agent CLI under Herdr in a throwaway
repository with a logged approval policy. It spends the operator's agent tokens and changes the agent's own state
directory, so run it only when that is intended.

## Licensing

Herdr's license (Apache-2.0) applies to this directory. `agent-memory` adapts code from the ECC project (MIT); the
notice and modification list are in `agent-memory/THIRD-PARTY-NOTICES.md`. `dispatch/tests/fixtures/ecc-code-reviewer.md`
is an ECC agent definition used only as parser input (see the `NOTICE.md` beside it).
