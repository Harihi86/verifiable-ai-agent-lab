import pytest

from verifiable_agent_lab.adapters import FixtureAdapter
from verifiable_agent_lab.cli import demo
from verifiable_agent_lab.models import Check, Outcome, Task, decide
from verifiable_agent_lab.runner import Lab


def submission(source="answer = 42\n"):
    return FixtureAdapter({"answer.py": source})


def check_task(name="example", command=("{python}", "-c", "print('ok')"), **kw):
    return Task(name, "A testable behavior", (Check("acceptance", command),), **kw)


def test_demo_rejects_bug_then_accepts_fix(tmp_path):
    assert demo(tmp_path)["outcomes"] == ["FAIL", "PASS"]
    reports = list(tmp_path.glob("*/report.json"))
    assert len(reports) == 2
    assert all((p.parent / "review.json").exists() for p in reports)
    assert all((p.parent / "check-0.log").stat().st_size > 0 for p in reports)


@pytest.mark.parametrize(
    "checks,expected",
    [
        ([], Outcome.NOT_RUN),
        ([{"mandatory": False, "outcome": Outcome.PASS}], Outcome.NOT_RUN),
        ([{"mandatory": True, "outcome": Outcome.FAIL}], Outcome.FAIL),
        ([{"mandatory": True, "outcome": Outcome.BLOCKED}], Outcome.BLOCKED),
        ([{"mandatory": True, "outcome": Outcome.INCONCLUSIVE}], Outcome.INCONCLUSIVE),
    ],
)
def test_gate_preserves_missing_and_failed_evidence(checks, expected):
    review = {"outcome": "PASS", "findings": []}
    assert decide(checks, review, True)[0] == expected


def test_review_uncertainty_and_owner_acceptance_are_not_pass():
    checks = [{"mandatory": True, "outcome": "PASS"}]
    review = {"outcome": "PASS", "findings": [{"disposition": "potential"}]}
    assert decide(checks, review, True)[0] == Outcome.INCONCLUSIVE
    assert decide(checks, {"outcome": "PASS", "findings": []}, True, True)[0] == Outcome.BLOCKED


def test_deadline_and_output_budget(tmp_path):
    lab = Lab(tmp_path)
    slow = lab.run(
        check_task("slow", ("{python}", "-c", "import time; time.sleep(2)"), timeout_seconds=0.1),
        submission(),
    )
    assert slow["outcome"] == Outcome.INCONCLUSIVE
    loud = lab.run(
        check_task("loud", ("{python}", "-c", "print('x'*20000)"), max_output_bytes=128),
        submission(),
    )
    assert loud["outcome"] == Outcome.INCONCLUSIVE
    assert (tmp_path / loud["attempt_id"] / "check-0.log").stat().st_size <= 128


def test_missing_executable_and_dependencies(tmp_path):
    lab = Lab(tmp_path)
    assert (
        lab.run(check_task(command=("does-not-exist-vaal",)), submission())["outcome"] == "BLOCKED"
    )
    dep = lab.run(check_task("dependent", dependencies=("absent",)), submission())
    assert dep["outcome"] == "BLOCKED"


def test_source_tampering_invalidates_pass(tmp_path):
    cmd = ("{python}", "-c", "from pathlib import Path; Path('answer.py').write_text('x=1')")
    assert Lab(tmp_path).run(check_task(command=cmd), submission())["outcome"] == "INCONCLUSIVE"


def test_owner_oracle_tampering_invalidates_pass(tmp_path):
    oracle = tmp_path / "oracle.txt"
    oracle.write_text("original")
    command = (
        "{python}",
        "-c",
        "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('changed')",
        str(oracle),
    )
    task = Task(
        "oracle",
        "Do not change owner acceptance inputs",
        (Check("owner", command, input_files=(str(oracle),)),),
    )
    assert Lab(tmp_path / "run").run(task, submission())["outcome"] == "INCONCLUSIVE"


def test_spec_immutable_and_attempt_budget(tmp_path):
    lab = Lab(tmp_path)
    lab.run(check_task(max_attempts=1), submission())
    with pytest.raises(ValueError, match="budget"):
        lab.run(check_task(max_attempts=1), submission())
    with pytest.raises(ValueError, match="specification changed"):
        lab.run(check_task(max_attempts=2), submission())


def test_recovery_marks_uncertain_without_replay(tmp_path):
    lab = Lab(tmp_path)
    report = lab.run(check_task(), submission())
    with lab.connect() as db:
        db.execute("UPDATE attempts SET state='RUNNING'")
    with pytest.raises(ValueError, match="already active"):
        lab.run(check_task(), submission())
    assert lab.recover("example") == [report["attempt_id"]]
    with lab.connect() as db:
        assert db.execute("SELECT outcome FROM attempts").fetchone()[0] == "INCONCLUSIVE"


def test_path_escape_rejected(tmp_path):
    report = Lab(tmp_path).run(check_task(), FixtureAdapter({"../escape.py": "x=1"}))
    assert report["outcome"] == "INCONCLUSIVE"
    assert not (tmp_path / "escape.py").exists()


def test_no_tests_is_not_success(tmp_path):
    assert Lab(tmp_path).run(Task("empty", "No oracle", ()), submission())["outcome"] == "NOT_RUN"


def test_syntax_review_fails_even_with_passing_command(tmp_path):
    assert Lab(tmp_path).run(check_task(), submission("def broken(:"))["outcome"] == "FAIL"


def test_dependency_can_be_satisfied(tmp_path):
    lab = Lab(tmp_path)
    assert lab.run(check_task("first"), submission())["outcome"] == "PASS"
    assert lab.run(check_task("second", dependencies=("first",)), submission())["outcome"] == "PASS"
