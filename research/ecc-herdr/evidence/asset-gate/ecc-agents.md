# agent-asset-gate report: `C:\Herdr-dev\ecc\agents`

**Decision: REVIEW** — needs human review: CRED-PATHx3, DESTRUCTIVEx4, EXEC-INLINEx10, PIPE-SHELLx1

Files scanned 71 (executable 0, instruction 71), skipped 0, 476,384 bytes, 460.9 ms.

| severity | count |
|---|---|
| critical | 0 |
| high | 7 |
| medium | 11 |
| low | 74 |
| info | 211 |

| rule | count |
|---|---|
| ASSET-INVENTORY | 71 |
| ASSET-MODEL-PIN | 71 |
| ASSET-NO-PROVENANCE | 71 |
| ASSET-TOOLS | 57 |
| CRED-PATH | 3 |
| DESTRUCTIVE | 4 |
| EXEC-INLINE | 10 |
| NET-FETCH | 3 |
| NET-URL | 12 |
| PIPE-SHELL | 1 |

## Top findings (first 80 by severity)

| sev | rule | file:line | message | evidence |
|---|---|---|---|---|
| high | CRED-PATH | `flutter-reviewer.md:208` | references a credential or SSH/key store path | `Keychain` |
| high | CRED-PATH | `swift-reviewer.md:33` | references a credential or SSH/key store path | `Keychain` |
| high | CRED-PATH | `swift-reviewer.md:34` | references a credential or SSH/key store path | `Keychain` |
| high | DESTRUCTIVE | `build-error-resolver.md:96` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `build-error-resolver.md:99` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `java-build-resolver.md:152` | destructive or guard-bypassing command | `rm -rf ` |
| high | DESTRUCTIVE | `kotlin-build-resolver.md:75` | destructive or guard-bypassing command | `rm -rf ` |
| medium | EXEC-INLINE | `django-build-resolver.md:138` | inline code execution through a shell or interpreter flag | `python -c` |
| medium | EXEC-INLINE | `django-build-resolver.md:151` | inline code execution through a shell or interpreter flag | `python -c` |
| medium | EXEC-INLINE | `django-build-resolver.md:157` | inline code execution through a shell or interpreter flag | `python -c` |
| medium | EXEC-INLINE | `django-build-resolver.md:190` | inline code execution through a shell or interpreter flag | `python -c` |
| medium | EXEC-INLINE | `opensource-sanitizer.md:184` | inline code execution through a shell or interpreter flag | `bash -c` |
| medium | EXEC-INLINE | `opensource-sanitizer.md:249` | inline code execution through a shell or interpreter flag | `bash -c` |
| medium | EXEC-INLINE | `pytorch-build-resolver.md:35` | inline code execution through a shell or interpreter flag | `python -c` |
| medium | EXEC-INLINE | `pytorch-build-resolver.md:36` | inline code execution through a shell or interpreter flag | `python -c` |
| medium | EXEC-INLINE | `pytorch-build-resolver.md:39` | inline code execution through a shell or interpreter flag | `python -c` |
| medium | EXEC-INLINE | `pytorch-build-resolver.md:85` | inline code execution through a shell or interpreter flag | `python -c` |
| medium | PIPE-SHELL | `agent-evaluator.md:34` | remote content piped straight into a shell | `curl … \| sh` |
| low | ASSET-NO-PROVENANCE | `a11y-architect.md` | 'a11y-architect' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `agent-evaluator.md` | 'agent-evaluator' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `architect.md` | 'architect' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `bengali-reviewer.md` | 'bengali-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `build-error-resolver.md` | 'build-error-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `chief-of-staff.md` | 'chief-of-staff' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `code-architect.md` | 'code-architect' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `code-explorer.md` | 'code-explorer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `code-reviewer.md` | 'code-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `code-simplifier.md` | 'code-simplifier' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `comment-analyzer.md` | 'comment-analyzer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `commit-reviewer.md` | 'commit-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `conversation-analyzer.md` | 'conversation-analyzer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `cpp-build-resolver.md` | 'cpp-build-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `cpp-reviewer.md` | 'cpp-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `csharp-reviewer.md` | 'csharp-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `dart-build-resolver.md` | 'dart-build-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `database-reviewer.md` | 'database-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `django-build-resolver.md` | 'django-build-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `django-reviewer.md` | 'django-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `doc-updater.md` | 'doc-updater' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `docs-lookup.md` | 'docs-lookup' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `e2e-runner.md` | 'e2e-runner' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `fastapi-reviewer.md` | 'fastapi-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `flutter-reviewer.md` | 'flutter-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `fsharp-reviewer.md` | 'fsharp-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `gan-evaluator.md` | 'gan-evaluator' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `gan-generator.md` | 'gan-generator' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `gan-planner.md` | 'gan-planner' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `go-build-resolver.md` | 'go-build-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `go-reviewer.md` | 'go-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `harmonyos-app-resolver.md` | 'harmonyos-app-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `harness-optimizer.md` | 'harness-optimizer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `healthcare-reviewer.md` | 'healthcare-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `homelab-architect.md` | 'homelab-architect' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `java-build-resolver.md` | 'java-build-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `java-reviewer.md` | 'java-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `kotlin-build-resolver.md` | 'kotlin-build-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `kotlin-reviewer.md` | 'kotlin-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `loop-operator.md` | 'loop-operator' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `marketing-agent.md` | 'marketing-agent' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `mle-reviewer.md` | 'mle-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `network-architect.md` | 'network-architect' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `network-config-reviewer.md` | 'network-config-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `network-troubleshooter.md` | 'network-troubleshooter' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `opensource-forker.md` | 'opensource-forker' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `opensource-packager.md` | 'opensource-packager' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `opensource-sanitizer.md` | 'opensource-sanitizer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `performance-optimizer.md` | 'performance-optimizer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `php-reviewer.md` | 'php-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `planner.md` | 'planner' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `pr-test-analyzer.md` | 'pr-test-analyzer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `python-reviewer.md` | 'python-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `pytorch-build-resolver.md` | 'pytorch-build-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `rag-pipeline-reviewer.md` | 'rag-pipeline-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `react-build-resolver.md` | 'react-build-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `react-reviewer.md` | 'react-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `refactor-cleaner.md` | 'refactor-cleaner' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `ruby-reviewer.md` | 'ruby-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `rust-build-resolver.md` | 'rust-build-resolver' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `rust-reviewer.md` | 'rust-reviewer' has no license/origin metadata in frontmatter | `` |
| low | ASSET-NO-PROVENANCE | `security-reviewer.md` | 'security-reviewer' has no license/origin metadata in frontmatter | `` |
