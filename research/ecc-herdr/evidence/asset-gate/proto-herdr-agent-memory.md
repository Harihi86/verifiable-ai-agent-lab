# agent-asset-gate report: `C:\Herdr-dev\prototypes\herdr-agent-memory`

**Decision: ALLOW** — only informational or low findings

Files scanned 18 (executable 15, instruction 1), skipped 0, 75,052 bytes, 67.2 ms.

| severity | count |
|---|---|
| critical | 0 |
| high | 0 |
| medium | 0 |
| low | 8 |
| info | 2 |

| rule | count |
|---|---|
| MANIFEST-EVENT-CARDINALITY | 1 |
| MANIFEST-INVENTORY | 1 |
| NET-FETCH | 1 |
| SECRET-LITERAL | 7 |

## Top findings (first 60 by severity)

| sev | rule | file:line | message | evidence |
|---|---|---|---|---|
| low | NET-FETCH | `src/lib/herdr-client.js:68` | outbound network call | `net.connect(` |
| low | SECRET-LITERAL | `tests/capture.test.js:101` | possible provider API key literal | `sk-abcdefghi...` |
| low | SECRET-LITERAL | `tests/fixtures/fake-herdr.js:25` | possible GitHub token literal | `ghp_ABCDEFGH...` |
| low | SECRET-LITERAL | `tests/summarize.test.js:13` | possible GitHub token literal | `ghp_ABCDEFGH...` |
| low | SECRET-LITERAL | `tests/vault-format.test.js:61` | possible GitHub token literal | `ghp_ABCDEFGH...` |
| low | SECRET-LITERAL | `tests/vault-format.test.js:61` | possible AWS access key literal | `AKIAABCDEFGH...` |
| low | SECRET-LITERAL | `tests/vault-format.test.js:61` | possible private key literal | `-----BEGIN R...` |
| low | SECRET-LITERAL | `tests/vault-store.test.js:59` | possible provider API key literal | `sk-abcdefghi...` |
| info | MANIFEST-EVENT-CARDINALITY | `herdr-plugin.toml` | event hook on 'pane.agent_status_changed' spawns a process per event; budget it | `` |
| info | MANIFEST-INVENTORY | `herdr-plugin.toml` | plugin 'research.agent-memory' v0.1.0 min_herdr 0.9.5: build=0, startup=0, events=1, actions=3, panes=0 | `` |
