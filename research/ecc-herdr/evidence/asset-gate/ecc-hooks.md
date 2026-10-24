# agent-asset-gate report: `C:\Herdr-dev\ecc\hooks`

**Decision: REVIEW** — needs human review: EXEC-INLINEx32, GLOBAL-CONFIGx4, HOOK-INLINE-BLOBx28

Files scanned 9 (executable 2, instruction 2), skipped 0, 80,958 bytes, 81.6 ms.

| severity | count |
|---|---|
| critical | 0 |
| high | 0 |
| medium | 64 |
| low | 6 |
| info | 22 |

| rule | count |
|---|---|
| EXEC-INLINE | 32 |
| GLOBAL-CONFIG | 4 |
| HOOK-CAN-BLOCK | 19 |
| HOOK-INLINE-BLOB | 28 |
| HOOK-INVENTORY | 3 |
| HOOK-TIMEOUT-MISMATCH | 6 |

## Top findings (first 80 by severity)

| sev | rule | file:line | message | evidence |
|---|---|---|---|---|
| medium | EXEC-INLINE | `README.md:263` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `README.md:276` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `README.md:289` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `README.md:302` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `codex-hooks.json:10` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:9` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:18` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:28` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:37` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:46` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:57` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:67` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:77` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:86` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:96` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:107` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:119` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:130` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:139` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:150` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:160` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:173` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:182` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:193` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:203` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:212` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:222` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:231` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:242` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:253` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:264` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | EXEC-INLINE | `hooks.json:277` | inline code execution through a shell or interpreter flag | `node -e` |
| medium | GLOBAL-CONFIG | `README.md:29` | writes or targets user-global agent or system configuration | `~/.claude/settings.json` |
| medium | GLOBAL-CONFIG | `README.md:42` | writes or targets user-global agent or system configuration | `~/.claude/settings.json` |
| medium | GLOBAL-CONFIG | `README.md:92` | writes or targets user-global agent or system configuration | `~/.claude/settings.json` |
| medium | GLOBAL-CONFIG | `README.md:150` | writes or targets user-global agent or system configuration | `[Environment]::SetEnvironmentVariable` |
| medium | HOOK-INLINE-BLOB | `codex-hooks.json` | SessionStart hook command is 1512 chars of inline code; review what it loads | `node -e "if(!process.env.PLUGIN_ROOT)throw new Error('Missing Codex PLUGIN_ROOT'` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreToolUse hook command is 1380 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreToolUse hook command is 1465 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreToolUse hook command is 1452 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreToolUse hook command is 1455 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreToolUse hook command is 1435 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreToolUse hook command is 1450 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreToolUse hook command is 1448 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreToolUse hook command is 1446 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreToolUse hook command is 1465 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreToolUse hook command is 1452 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | UserPromptSubmit hook command is 1455 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PreCompact hook command is 1432 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | SessionStart hook command is 1384 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | SessionStart hook command is 1464 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PostToolUse hook command is 1350 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PostToolUse hook command is 1351 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PostToolUseFailure hook command is 1447 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | PostToolUseFailure hook command is 1443 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | Stop hook command is 1734 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | Stop hook command is 1742 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | Stop hook command is 1734 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | Stop hook command is 1730 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | Stop hook command is 1726 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | Stop hook command is 1736 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | Stop hook command is 1728 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | Stop hook command is 1724 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| medium | HOOK-INLINE-BLOB | `hooks.json` | SessionEnd hook command is 1735 chars of inline code; review what it loads | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| low | HOOK-TIMEOUT-MISMATCH | `hooks.json` | async PreToolUse hook with timeout 10s may be killed before it finishes | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| low | HOOK-TIMEOUT-MISMATCH | `hooks.json` | async Stop hook with timeout 10s may be killed before it finishes | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| low | HOOK-TIMEOUT-MISMATCH | `hooks.json` | async Stop hook with timeout 10s may be killed before it finishes | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| low | HOOK-TIMEOUT-MISMATCH | `hooks.json` | async Stop hook with timeout 10s may be killed before it finishes | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| low | HOOK-TIMEOUT-MISMATCH | `hooks.json` | async Stop hook with timeout 10s may be killed before it finishes | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| low | HOOK-TIMEOUT-MISMATCH | `hooks.json` | async SessionEnd hook with timeout 10s may be killed before it finishes | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| info | HOOK-CAN-BLOCK | `hooks.json` | PreToolUse command hook can block or alter agent actions | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| info | HOOK-CAN-BLOCK | `hooks.json` | PreToolUse command hook can block or alter agent actions | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| info | HOOK-CAN-BLOCK | `hooks.json` | PreToolUse command hook can block or alter agent actions | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| info | HOOK-CAN-BLOCK | `hooks.json` | PreToolUse command hook can block or alter agent actions | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| info | HOOK-CAN-BLOCK | `hooks.json` | PreToolUse command hook can block or alter agent actions | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| info | HOOK-CAN-BLOCK | `hooks.json` | PreToolUse command hook can block or alter agent actions | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| info | HOOK-CAN-BLOCK | `hooks.json` | PreToolUse command hook can block or alter agent actions | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| info | HOOK-CAN-BLOCK | `hooks.json` | PreToolUse command hook can block or alter agent actions | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| info | HOOK-CAN-BLOCK | `hooks.json` | PreToolUse command hook can block or alter agent actions | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
| info | HOOK-CAN-BLOCK | `hooks.json` | PreToolUse command hook can block or alter agent actions | `node -e "const p=require('path');const r=(function(){var p=require('path'),f=req` |
