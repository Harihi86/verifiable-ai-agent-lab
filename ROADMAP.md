# Development roadmap

| Priority / status | Objective and expected behavior | Dependencies | Acceptance criteria / verification |
|---|---|---|---|
| P0 / Implemented | Preserve mandatory failures and execution uncertainty | Local runner | Gate, deadline, overflow, missing-oracle and recovery regression tests |
| P0 / Planned | Harden evidence and execution for adversarial submissions | External sandbox and threat model | Tests cannot modify owner oracles, access host credentials or leave descendants; adversarial integration suite |
| P1 / Implemented | Independent owner checks, source review and durable attempt reports | Python and SQLite | Broken and corrected fixtures evaluated with the same archived acceptance file |
| P1 / Planned | Add a live provider-neutral development/review adapter | Stable submission/reviewer contracts | Real invocation transcripts, source-bound review, fake-provider contract tests, no required paid API |
| P1 / Planned | Add snapshot-specific dependency acceptance and recovery leases | Durable state store | Dependency changes cannot reuse stale acceptance; crashed worker recovery tested without duplicate dispatch |
| P2 / Planned | Reviewer disagreement, rubric calibration and verifier reliability | Reviewed reference tasks | Measure false accept/reject rates on adjudicated held-out tasks; preserve disagreement |
| P2 / Planned | Cost per verified task and recovery metrics | Real provider traces and declared accounting | Recompute reported costs, success fractions and uncertainty from raw traces |
| P3 / Research | Contamination-controlled repository, terminal and computer-use evaluations | Dataset rights and isolated runners | Public task provenance, held-out split and documented benchmark protocol; never claim official results from internal tasks |
| P3 / Research | LLM judges, synthetic task generation and selective formal methods | Calibrated rubrics and task semantics | Judge agreement checked against human/reference outcomes; generated tasks validated independently |

Next milestone: isolate execution and owner acceptance artifacts before accepting
untrusted submissions. Multi-host orchestration is deferred until this boundary
and explicit retry semantics have been tested.
