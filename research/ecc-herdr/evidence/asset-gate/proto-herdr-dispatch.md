# agent-asset-gate report: `C:\Herdr-dev\prototypes\herdr-dispatch`

**Decision: REVIEW** — needs human review: AGENT-SPAWNx4

Files scanned 8 (executable 8, instruction 0), skipped 0, 35,245 bytes, 34.1 ms.

| severity | count |
|---|---|
| critical | 0 |
| high | 0 |
| medium | 4 |
| low | 0 |
| info | 0 |

| rule | count |
|---|---|
| AGENT-SPAWN | 4 |

## Top findings (first 60 by severity)

| sev | rule | file:line | message | evidence |
|---|---|---|---|---|
| medium | AGENT-SPAWN | `herdr_dispatch/kinds.py:44` | drives another coding-agent CLI directly (competing controller / token spend) | `codex", exec` |
| medium | AGENT-SPAWN | `herdr_dispatch/kinds.py:49` | drives another coding-agent CLI directly (competing controller / token spend) | `cursor-agent` |
| medium | AGENT-SPAWN | `herdr_dispatch/kinds.py:51` | drives another coding-agent CLI directly (competing controller / token spend) | `cursor-agent` |
| medium | AGENT-SPAWN | `herdr_dispatch/kinds.py:54` | drives another coding-agent CLI directly (competing controller / token spend) | `grok", "--resume` |
