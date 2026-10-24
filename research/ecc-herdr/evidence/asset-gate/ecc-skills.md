# agent-asset-gate report: `C:\Herdr-dev\ecc\skills`

**Decision: REVIEW** — needs human review: AGENT-SPAWNx57, CRED-PATHx8, DESTRUCTIVEx24, EXEC-INLINEx24, GLOBAL-CONFIGx25, OBFUSCATIONx2, PIPE-SHELLx2, PROMPT-WIDENx5

Files scanned 599 (executable 131, instruction 444), skipped 14, 4,932,985 bytes, 4605.7 ms.

| severity | count |
|---|---|
| critical | 0 |
| high | 32 |
| medium | 115 |
| low | 140 |
| info | 636 |

| rule | count |
|---|---|
| AGENT-SPAWN | 64 |
| ASSET-INVENTORY | 344 |
| ASSET-MODEL-PIN | 5 |
| ASSET-NO-PROVENANCE | 27 |
| ASSET-TOOLS | 12 |
| CRED-PATH | 8 |
| DESTRUCTIVE | 25 |
| EXEC-INLINE | 24 |
| GLOBAL-CONFIG | 27 |
| NET-FETCH | 111 |
| NET-URL | 267 |
| OBFUSCATION | 2 |
| PIPE-SHELL | 2 |
| PROMPT-WIDEN | 5 |

## Top findings (first 80 by severity)

| sev | rule | file:line | message | evidence |
|---|---|---|---|---|
| high | CRED-PATH | `docker-patterns/SKILL.md:447` | references a credential or SSH/key store path | `.codex/<credential-file>` |
| high | CRED-PATH | `flutter-dart-code-review/SKILL.md:268` | references a credential or SSH/key store path | `Keychain` |
| high | CRED-PATH | `gateguard/SKILL.md:292` | references a credential or SSH/key store path | `.netrc` |
| high | CRED-PATH | `gateguard/SKILL.md:293` | references a credential or SSH/key store path | `id_rsa` |
| high | CRED-PATH | `gateguard/SKILL.md:294` | references a credential or SSH/key store path | `id_ecdsa` |
| high | CRED-PATH | `ito-compute/SKILL.md:40` | references a credential or SSH/key store path | `Keychain` |
| high | CRED-PATH | `ito-compute/SKILL.md:45` | references a credential or SSH/key store path | `Keychain` |
| high | CRED-PATH | `react-native-patterns/SKILL.md:184` | references a credential or SSH/key store path | `Keychain` |
| high | DESTRUCTIVE | `continuous-learning-v2/agents/session-guardian.sh:78` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `continuous-learning-v2/agents/session-guardian.sh:87` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `continuous-learning-v2/agents/session-guardian.sh:99` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `frontend-slides/scripts/export-pdf.sh:378` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `frontend-slides/scripts/export-pdf.sh:386` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `frontend-slides/scripts/export-pdf.sh:406` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `frontend-slides/scripts/export-pdf.sh:412` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `gateguard/SKILL.md:193` | destructive or guard-bypassing command | `git reset --hard` |
| high | DESTRUCTIVE | `gateguard/SKILL.md:596` | destructive or guard-bypassing command | `git reset --hard` |
| high | DESTRUCTIVE | `generating-python-installer/SKILL.md:349` | destructive or guard-bypassing command | `Remove-Item -Path $dir.FullName -Recurse -Force` |
| high | DESTRUCTIVE | `generating-python-installer/SKILL.md:364` | destructive or guard-bypassing command | `Remove-Item -Path $dir.FullName -Recurse -Force` |
| high | DESTRUCTIVE | `generating-python-installer/SKILL.md:379` | destructive or guard-bypassing command | `Remove-Item -Path $dir.FullName -Recurse -Force` |
| high | DESTRUCTIVE | `git-workflow/SKILL.md:205` | destructive or guard-bypassing command | `git push --force` |
| high | DESTRUCTIVE | `git-workflow/SKILL.md:605` | destructive or guard-bypassing command | `git reset --hard` |
| high | DESTRUCTIVE | `git-workflow/SKILL.md:684` | destructive or guard-bypassing command | `git push --force` |
| high | DESTRUCTIVE | `hookify-rules/SKILL.md:100` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `perl-security/SKILL.md:179` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `repo-scan/SKILL.md:39` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `rules-distill/scripts/scan-skills.sh:61` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `safety-guard/SKILL.md:3` | destructive or guard-bypassing command | `git push --force` |
| high | DESTRUCTIVE | `safety-guard/SKILL.md:27` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `safety-guard/SKILL.md:28` | destructive or guard-bypassing command | `git push --force` |
| high | DESTRUCTIVE | `safety-guard/SKILL.md:29` | destructive or guard-bypassing command | `git reset --hard` |
| high | DESTRUCTIVE | `skill-stocktake/scripts/scan.sh:101` | destructive or guard-bypassing command | `rm -rf ` |
| medium | AGENT-SPAWN | `autonomous-agent-harness/SKILL.md:100` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-agent-harness/SKILL.md:123` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-agent-harness/SKILL.md:129` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-agent-harness/SKILL.md:217` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-agent-harness/SKILL.md:223` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:15` | drives another coding-agent CLI directly (competing controller / token spend) | `Claude Code autonomously in loops. Covers everything from simple `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:43` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:49` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:58` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:61` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:64` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:67` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:72` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:82` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:85` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:88` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:95` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:102` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:105` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:112` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:125` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:223` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:224` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:228` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:280` | drives another coding-agent CLI directly (competing controller / token spend) | `Claude reads this file at iteration start and updates it at iteration end. This ` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:286` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:343` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:346` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:361` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:364` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:367` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:370` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:577` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:580` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `autonomous-loops/SKILL.md:591` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `continuous-learning-v2/agents/observer-loop.sh:399` | drives another coding-agent CLI directly (competing controller / token spend) | `claude --model "${ECC_OBSERVER_MODEL:-haiku}" --max-turns "$max_turns" --print` |
| medium | AGENT-SPAWN | `dmux-workflows/SKILL.md:154` | drives another coding-agent CLI directly (competing controller / token spend) | `codex exec` |
| medium | AGENT-SPAWN | `gan-style-harness/SKILL.md:31` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `gan-style-harness/SKILL.md:182` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `gan-style-harness/SKILL.md:185` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `gan-style-harness/SKILL.md:188` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `gan-style-harness/SKILL.md:191` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `plankton-code-quality/SKILL.md:37` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `skill-comply/SKILL.md:14` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `skill-comply/prompts/scenario_generator.md:17` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `skill-comply/scripts/classifier.py:51` | drives another coding-agent CLI directly (competing controller / token spend) | `claude", "-p` |
| medium | AGENT-SPAWN | `skill-comply/scripts/runner.py:1` | drives another coding-agent CLI directly (competing controller / token spend) | `claude -p` |
| medium | AGENT-SPAWN | `skill-comply/scripts/runner.py:53` | drives another coding-agent CLI directly (competing controller / token spend) | `claude", "-p` |
