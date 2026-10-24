# Research tracks

This directory holds research material that informs the lab but is **not part of the `verifiable_agent_lab`
package**: nothing here is installed, imported by `src/`, exercised by the CI workflow, or required to run `vaal`.
Each track states its own provenance, verification status and limits, and keeps the lab's standalone identity:
the lab has no dependency on any orchestration system studied in a track.

| Track | Subject | Status |
|---|---|---|
| [`ecc-herdr/`](ecc-herdr/README.md) | Evaluation of the ECC agent-harness project against the Herdr terminal agent runtime: component comparison, three tested prototypes, real-agent validations (Grok Build 1.0.67; Codex CLI 0.163 in one configuration), a detection vulnerability and its validated fix | research track, 2026-10-24; proposals only, nothing production-ready |

Verification classes used by every track (a document or artifact says which one applies):

| Class | Meaning |
|---|---|
| research finding | derived from reading source or documentation, with file and line citations |
| tested prototype | code with unit tests and, where stated, tests against a disposable local backend |
| offline verification | deterministic check of a captured artifact (for example a screen text classified against a manifest) without running the live system |
| real-agent verification | a supervised run of the real agent CLI under the orchestrator, with timings, screens and policy actions recorded |
| proposed integration | a change or design that has not been merged, compiled, or deployed |
| production-ready | reserved; no track artifact currently carries this status |

Publication rules from [`docs/publication.md`](../docs/publication.md) apply: tracks contain sanitized material only
(user, host and e-mail identifiers, private deployment identifiers, credential file names and owner-policy references
are replaced by placeholders, and each track records what was excluded).
