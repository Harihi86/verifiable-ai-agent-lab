# agent-asset-gate report: `C:\Herdr-dev\ecc\scripts\hooks`

**Decision: REVIEW** — needs human review: CRED-PATHx1, GLOBAL-CONFIGx2

Files scanned 61 (executable 61, instruction 0), skipped 0, 580,669 bytes, 517.1 ms.

| severity | count |
|---|---|
| critical | 0 |
| high | 1 |
| medium | 2 |
| low | 1 |
| info | 12 |

| rule | count |
|---|---|
| AGENT-SPAWN | 1 |
| CRED-PATH | 1 |
| DESTRUCTIVE | 1 |
| EXEC-INLINE | 4 |
| GLOBAL-CONFIG | 5 |
| NET-FETCH | 1 |
| NET-URL | 3 |

## Top findings (first 80 by severity)

| sev | rule | file:line | message | evidence |
|---|---|---|---|---|
| high | CRED-PATH | `governance-capture.js:65` | references a credential or SSH/key store path | `id_rsa` |
| medium | GLOBAL-CONFIG | `block-no-verify.js:30` | writes or targets user-global agent or system configuration | `core.hookspath` |
| medium | GLOBAL-CONFIG | `block-no-verify.js:271` | writes or targets user-global agent or system configuration | `core.hooksPath` |
| low | NET-FETCH | `plan-canvas-pending.js:121` | outbound network call | `http.request(` |
| info | AGENT-SPAWN | `session-end.js:210` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| info | DESTRUCTIVE | `gateguard-fact-force.js:249` | destructive or guard-bypassing command | `rm -rf ` |
| info | EXEC-INLINE | `gateguard-fact-force.js:911` | inline code execution through a shell or interpreter flag | `sh -c` |
| info | EXEC-INLINE | `gateguard-fact-force.js:1401` | inline code execution through a shell or interpreter flag | `bash -c` |
| info | EXEC-INLINE | `plugin-hook-bootstrap.js:319` | inline code execution through a shell or interpreter flag | `node -e` |
| info | EXEC-INLINE | `session-start-bootstrap.js:10` | inline code execution through a shell or interpreter flag | `node -e` |
| info | GLOBAL-CONFIG | `block-no-verify.js:5` | writes or targets user-global agent or system configuration | `core.hooksPath` |
| info | GLOBAL-CONFIG | `block-no-verify.js:24` | writes or targets user-global agent or system configuration | `core.hooksPath` |
| info | GLOBAL-CONFIG | `mcp-health-check.js:564` | writes or targets user-global agent or system configuration | `~/.claude/settings.json` |
| info | NET-URL | `block-no-verify.js:26` | URL literal | `https://git-scm.com/docs/git-config` |
| info | NET-URL | `cost-tracker.js:80` | URL literal | `https://platform.claude.com/docs/en/about-claude/pricing` |
| info | NET-URL | `cursor-session-env.js:6` | URL literal | `https://cursor.com/docs/hooks` |
