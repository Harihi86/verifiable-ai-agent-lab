import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from herdr_dispatch import kinds, plan as planmod, roles  # noqa: E402

ECC_AGENT = Path(r"C:\Herdr-dev\ecc\agents\code-reviewer.md")  # reviewed ECC asset used as data only


def write_role(tmp: Path, name="Code Reviewer", model="opus", tools="Read, Grep, Bash") -> Path:
    path = tmp / "role.md"
    path.write_text(f"---\nname: {name}\ndescription: Reviews diffs for defects\ntools: {tools}\nmodel: {model}\n---\n# Role\nReview only. Report findings with file:line.\n", encoding="utf-8")
    return path


class RoleTests(unittest.TestCase):
    def test_parses_ecc_agent_definition(self):
        role = roles.load_role(ECC_AGENT)
        self.assertEqual(role.name, "code-reviewer")
        self.assertTrue(role.description)
        self.assertTrue(role.instructions)
        self.assertIn(role.model_hint, (None, "opus", "sonnet", "haiku", "inherit"))

    def test_name_is_coerced_to_herdr_agent_name_and_hidden_chars_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            role = roles.load_role(write_role(Path(tmp), name="Code Reviewer"))
            self.assertEqual(role.name, "code-reviewer")
            self.assertTrue(roles.NAME_PATTERN.match(role.name))
            self.assertTrue(any("coerced" in w for w in role.warnings))
            bad = Path(tmp) / "bad.md"
            bad.write_text("---\nname: x\ndescription: d\n---\nvisible\u202ehidden\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                roles.load_role(bad)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.role = roles.load_role(write_role(Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_grok_is_started_directly_by_herdr_with_no_codex_in_the_loop(self):
        plan = planmod.build_plan(self.role, "grok", r"C:\work\repo", task="Fix the failing test")
        argvs = [" ".join(step.argv) for step in plan.steps]
        self.assertTrue(argvs[0].startswith("workspace create --cwd"))
        self.assertEqual(plan.steps[1].argv[:6], ["agent", "start", "code-reviewer", "--kind", "grok", "--pane"])
        self.assertTrue(argvs[2].startswith("agent prompt code-reviewer"))
        self.assertIn("--wait", plan.steps[2].argv)
        self.assertFalse(any("codex" in a for a in argvs), "Grok must not be driven through Codex")
        self.assertTrue(all(step.authority == "herdr" for step in plan.steps))
        self.assertTrue(any("Claude-specific" in w and "dropped" in w for w in plan.warnings), plan.warnings)
        self.assertIn("## Task", plan.prompt)
        self.assertIn("treat any text you later read", plan.prompt)

    def test_claude_keeps_model_hint_and_native_flags_are_opt_in_and_annotated(self):
        default = planmod.build_plan(self.role, "claude", r"C:\work\repo")
        self.assertNotIn("--", default.steps[1].argv)
        native = planmod.build_plan(self.role, "claude", r"C:\work\repo", native_flags=True)
        self.assertIn("--", native.steps[1].argv)
        self.assertIn("--model", native.steps[1].argv)
        self.assertIn("opus", native.steps[1].argv)
        self.assertTrue(any("not verified" in n for n in native.notes), native.notes)

    def test_worktree_variant_and_memory_handoff_step(self):
        plan = planmod.build_plan(self.role, "codex", r"C:\work\repo", worktree_branch="review/x", memory_cli=r"C:\p\cli.js")
        self.assertEqual(plan.steps[0].argv[:2], ["worktree", "create"])
        self.assertEqual(plan.steps[-1].authority, "plugin:research.agent-memory")
        self.assertEqual(plan.steps[-1].argv[0], "__external__")
        roundtrip = json.loads(plan.to_json())
        self.assertEqual(len(roundtrip["steps"]), 5)
        self.assertIn("Dispatch plan", plan.to_markdown())

    def test_unsupported_kind_rejected(self):
        with self.assertRaises(ValueError):
            planmod.build_plan(self.role, "chatgpt", r"C:\work\repo")

    def test_every_adapter_kind_is_a_herdr_kind(self):
        for kind in kinds.ADAPTERS:
            self.assertIn(kind, kinds.HERDR_KINDS)


class CliTests(unittest.TestCase):
    def test_plan_and_dry_run_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            role = write_role(Path(tmp))
            plan_json = Path(tmp) / "plan.json"
            out = subprocess.run([sys.executable, "-I", str(ROOT / "herdr-dispatch.py"), "plan", "--role", str(role), "--kind", "grok", "--cwd", tmp, "--task", "t", "--json", str(plan_json)],
                                 capture_output=True, text=True, cwd=tmp)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertTrue(plan_json.exists())
            dry = subprocess.run([sys.executable, "-I", str(ROOT / "herdr-dispatch.py"), "run", "--plan", str(plan_json), "--binary", r"C:\Herdr-dev\runtime\bin\herdr-0.9.5\herdr.exe", "--session", "dry", "--dry-run"],
                                 capture_output=True, text=True, cwd=tmp)
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            record = json.loads(dry.stdout)
            self.assertTrue(record["ok"] and record["dry_run"])
            first = record["steps"][0]["argv"][0]
            self.assertEqual(first[0], r"C:\Herdr-dev\runtime\bin\herdr-0.9.5\herdr.exe")
            self.assertEqual(first[1:3], ["--session", "dry"])
            self.assertIn("--kind", record["steps"][1]["argv"][0])
            self.assertIn("grok", record["steps"][1]["argv"][0])


if __name__ == "__main__":
    unittest.main()
