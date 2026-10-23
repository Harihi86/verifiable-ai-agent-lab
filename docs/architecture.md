# Architecture and evidence contract

`Task` describes an owner objective, checks, dependency IDs and bounded resource
policy. Its serialized digest is immutable within a task ID. The SQLite state
store reserves an attempt as `RUNNING`, then records `FINISHED`; explicit recovery
changes an interrupted attempt to `INTERRUPTED` with an `INCONCLUSIVE` outcome.

`DevelopmentAdapter` supplies a mapping of relative filenames to text. The bundled
adapter reads a local directory; external agents can implement the same Python
protocol. Staging rejects path traversal, hidden paths, symlinks, more than 200
files and submissions larger than 2 MB. This controls staging behavior, not code
execution privileges.

`StaticReviewer` reads the staged source and produces file/line findings with
confirmed or potential dispositions. It identifies its method as static review.
It is deliberately independent of any submission's claim that tests passed.
A custom reviewer may implement `review(workspace)` and return the same report
contract; no commercial provider integration ships in this release.

`execute` invokes owner-defined argument vectors with `shell=False`, a deadline,
a combined stdout/stderr log and a byte cap. Startup failure is `BLOCKED`, a
nonzero exit is `FAIL`, and exhausted execution/output budgets are `INCONCLUSIVE`.
The timeout is per check; no CPU, memory, network or filesystem sandbox is provided.

`Lab` archives submitted source and declared owner files, collects review and raw
check output, compares the source digest before and after execution, and sends
those observations to a pure policy gate. Reports contain task/attempt IDs,
timestamps, source and specification hashes, command vectors and measured results.
Hashes bind content for inspection; they are not signed attestations.

The demo's acceptance file is outside the submission workspace. It is a different
artifact from both proposed implementations, with explicit empty-input behavior
from the owner task. It was authored for this release and is not evidence of a
separate human or model reviewing the development process.

No retry runs automatically: each new `run` is an explicit submission, subject to
the persisted attempt budget. Uncertain completion therefore does not cause
silent replay. Recovery is an explicit local administrative operation, not a
claim that external side effects were rolled back.
