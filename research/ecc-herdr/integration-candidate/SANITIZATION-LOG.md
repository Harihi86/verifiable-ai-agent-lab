# Sanitization log (integration candidate)

32 files exported with the rules and deny-list of `sanitize.py`.

## Replacement counts
| rule | replacements |
|---|---|
| agent-usage-quota | 8 |
| codex-package-id | 9 |
| evidence-json-home-lists | 8 |
| user-profile-path | 29 |

## Residual deny-listed tokens: 0

## Files
- `COMPONENTS.md`
- `INTEGRATION-CANDIDATE.md`
- `SECURITY.md`
- `evidence/backend/candidate/dispatch-backend.json`
- `evidence/backend/candidate/gate-backend.json`
- `evidence/backend/candidate/lifecycle-backend.json`
- `evidence/backend/candidate/plugin-backend.json`
- `evidence/backend/v0.9.5/dispatch-backend.json`
- `evidence/backend/v0.9.5/gate-backend.json`
- `evidence/backend/v0.9.5/lifecycle-backend.json`
- `evidence/backend/v0.9.5/plugin-backend.json`
- `evidence/build/build-gnu-release-1.log`
- `evidence/build/build-gnu-release-2.log`
- `evidence/build/lint-gnu.log`
- `evidence/detection-fixtures/codex-0.163-idle-after-turn.txt`
- `evidence/detection-fixtures/codex-0.163-ratelimit-model-picker.txt`
- `evidence/detection-fixtures/codex-0.163-trust-dialog.txt`
- `evidence/detection-fixtures/expectations.json`
- `evidence/detection-fixtures/grok-1.0.67-idle-after-turn.txt`
- `evidence/detection-fixtures/grok-1.0.67-trust-dialog.txt`
- `evidence/lifecycle/candidate-lifecycle.json`
- `evidence/real-agent/claude-2.1.286-build1-run1-cursor-list-unparsed.json`
- `evidence/real-agent/claude-2.1.286-build1-run2-pass.json`
- `evidence/real-agent/codex-0.163-build1-no-daemon-pass-picker-found.json`
- `evidence/real-agent/codex-0.163-build2-default-daemon-mode.json`
- `evidence/real-agent/codex-0.163-build2-no-daemon-pass-picker-blocked.json`
- `evidence/real-agent/grok-1.0.67-build1-run1-prompt-refused-while-blocked.json`
- `evidence/real-agent/grok-1.0.67-build1-run2-prompt-stalled.json`
- `evidence/real-agent/grok-1.0.67-build1-run3-pass.json`
- `evidence/rust-tests/env-dependent-test-with-variable-unset.txt`
- `evidence/rust-tests/maintenance-tests-final.log`
- `evidence/rust-tests/test-isolated-final.json`
