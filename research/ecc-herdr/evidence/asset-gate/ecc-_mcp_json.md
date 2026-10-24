# agent-asset-gate report: `C:\Herdr-dev\ecc\.mcp.json`

**Decision: ALLOW** — only informational or low findings

Files scanned 1 (executable 0, instruction 0), skipped 0, 132 bytes, 0.7 ms.

| severity | count |
|---|---|
| critical | 0 |
| high | 0 |
| medium | 0 |
| low | 0 |
| info | 2 |

| rule | count |
|---|---|
| MCP-INVENTORY | 1 |
| MCP-NPX | 1 |

## Top findings (first 80 by severity)

| sev | rule | file:line | message | evidence |
|---|---|---|---|---|
| info | MCP-INVENTORY | `.mcp.json` | MCP server 'chrome-devtools': npx -y chrome-devtools-mcp@1.10.1 | `` |
| info | MCP-NPX | `.mcp.json` | MCP server 'chrome-devtools' runs via npx (version pinned) | `npx -y chrome-devtools-mcp@1.10.1` |
