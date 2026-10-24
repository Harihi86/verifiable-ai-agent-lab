# What the lab can reuse from this track (without depending on Herdr)

The lab's contract is: owner-defined acceptance checks, independent static review, durable attempt records, evidence
bound by hashes, explicit uncertainty. The research produced several techniques that fit that contract. Each item below
states what it is, how it would enter the lab, and what it must **not** bring with it. None of them requires Herdr; where
Herdr was the source of evidence, the lab would consume a captured artifact, not a live socket.

## 1. Static review of agent assets as a `StaticReviewer`-shaped reviewer (strong fit)

`prototypes/agent-asset-gate` is pure Python 3.11+ stdlib. Its findings already have the shape the lab's review
contract uses (file, line, severity, message, evidence, tags) and a decision (allow / review / deny) that maps to the
lab's PASS / INCONCLUSIVE / FAIL semantics:

| gate | lab outcome | reason |
|---|---|---|
| deny (critical: secret literal, remote content piped to a shell) | FAIL | confirmed defect in the submission |
| review (high/medium) | INCONCLUSIVE with findings | unresolved review concern, human reads the lines |
| allow | review passed | only informational/low findings |

Integration sketch: an optional reviewer module (`verifiable_agent_lab/reviewers/asset_gate.py`) that imports the
rules and structural checks, runs them over the staged workspace, and emits the lab's review report; off by default,
selected per task. Value: submissions that *contain* agent assets (hooks, skills, MCP configs, plugin manifests) get a
deterministic, dependency-free review today, which the lab's current syntax/bare-`except`/`shell=True` reviewer does
not cover. Keep: the test-fixture severity cap and `--strict`. Leave out: the Herdr `coexist` check (Herdr-specific),
unless the task declares it.

## 2. Screen-fixture classification as a deterministic grader (medium fit, artifact-based)

The detection-drift finding was proven with a captured terminal screen and an offline classifier (`herdr agent explain
--file`). The lab's roadmap item "live provider-neutral development/review adapter" needs exactly this kind of grader:
a text fixture plus an expected state, checked by a command vector under the lab's deadline and output caps. The lab
can host the fixtures (`evidence/real-agent/fixtures/`) and the expected outcomes as owner acceptance files; the
classifier executable is whatever the task declares (here a Herdr binary by absolute path), so the lab itself gains no
Herdr dependency. This is the pattern for "agent UI regression tests keyed by agent version".

## 3. Supervised real-agent run record as an evidence schema (medium fit)

`evidence/real-agent/*.json` records, per run: resolved executable and version, the plan step argv, per-step exit codes
and output tails, a timeline of orchestrator events with millisecond offsets, every policy action taken on a dialog,
screen captures at decision points, and before/after counts of changes to the agent's home directory. That is a
candidate schema for the lab's planned "real invocation transcripts": explicit, replayable, with policy actions
separated from agent output. Suggested additions if adopted: SHA-256 of each screen capture and of the plan, and the
lab's attempt/task ids.

## 4. Approval policy as owner-acceptance tests (medium fit)

The run script's policy (answer only a trust prompt for the dispatched path or a read-only permission inside it; never
choose "always/yolo/all"; abort on anything else) is small and testable. The lab could ship it as a reference
acceptance test for live adapters: feed the captured dialog fixtures to the option parser and assert the chosen key or
the abort. Value: makes "the agent's approval boundary held" an observable check instead of a claim.

## 5. Isolation audit as an adversarial-hardening check (strong fit with roadmap P0)

`prototypes/common/isolation_audit.py` snapshots protected and user roots before/after and asserts no writes outside
the run root and no surviving processes. The lab's P0 item ("tests cannot modify owner oracles, access host credentials
or leave descendants") can reuse the shape: parameterize protected roots (owner acceptance files, state database),
record newest-mtime and entry counts before and after each attempt, and mark the attempt INCONCLUSIVE when the
snapshot changed. No Herdr involvement.

## 6. Bounded, non-executable context documents (weak fit, design only)

The memory vault format (JSON-valued Markdown frontmatter, create-only, `trust: unreviewed`, secret refusal, hard size
caps, guard header on recall) is a reasonable template for any artifact the lab lets an agent read back later (for
example a handoff note between attempts). The lab has no such artifact today; record the pattern, do not add code.

## Explicitly not recommended for the lab

- Any live Herdr socket or plugin dependency, the dispatch executor, or the memory plugin as runtime components.
- ECC hooks, instincts or orchestrator scripts (see `SECURITY-FINDINGS.md §2`).
- Treating the simulated-agent backend tests as evidence about real agents; the lab's own docs make the same distinction
  for its deterministic fixtures.
