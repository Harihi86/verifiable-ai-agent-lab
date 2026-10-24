import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import herdr_isolated as hi  # noqa: E402


class ScrubbedEnvTests(unittest.TestCase):
    def test_removes_inherited_herdr_and_xdg_context(self):
        base = {
            "HERDR_ENV": "1",
            "HERDR_SOCKET_PATH": r"\\.\pipe\prod",
            "HERDR_CLIENT_SOCKET_PATH": r"\\.\pipe\prod-client",
            "HERDR_SESSION": "<production-session-2>",
            "HERDR_PANE_ID": "w1:p1",
            "herdr_machine": "mac",
            "XDG_CONFIG_HOME": r"C:\herdr\.local\<private>",
            "XDG_STATE_HOME": r"C:\herdr\.local\<private>",
            "PATH": r"C:\Windows;C:\herdr\.local\<private>;C:\Users\x\<private-pilot-path>;C:\Program Files\nodejs",
            "USERPROFILE": r"C:\Users\x",
        }
        env = hi.scrubbed_env(base)
        self.assertFalse(any(k.upper().startswith("HERDR_") for k in env))
        self.assertNotIn("XDG_CONFIG_HOME", env)
        self.assertNotIn("XDG_STATE_HOME", env)
        self.assertEqual(env["USERPROFILE"], r"C:\Users\x")
        self.assertEqual(env["PATH"], r"C:\Windows;C:\Program Files\nodejs")

    def test_does_not_mutate_process_environment(self):
        before = dict(os.environ)
        hi.scrubbed_env()
        self.assertEqual(before, dict(os.environ))


class IsolatedRuntimeTests(unittest.TestCase):
    def setUp(self):
        (hi.RUNTIME_ROOT / "tmp").mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=str(hi.RUNTIME_ROOT / "tmp"))
        self.root = Path(self.tmp.name) / "rt"

    def tearDown(self):
        self.tmp.cleanup()

    def test_prepare_creates_release_and_debug_app_dirs_and_config(self):
        rt = hi.IsolatedRuntime(session_name="unit-test-session", root=self.root)
        rt.prepare()
        for app_dir in ("herdr", "herdr-dev"):
            self.assertTrue((rt.config_home / app_dir).is_dir())
            self.assertTrue((rt.state_home / app_dir).is_dir())
        text = rt.config_path.read_text(encoding="utf-8")
        for key in (
            "version_check = false",
            "manifest_check = false",
            "manage_ssh_config = false",
            "resume_agents_on_restore = false",
            "allow_nested = true",
            'delivery = "off"',
        ):
            self.assertIn(key, text)

    def test_env_points_every_root_inside_runtime(self):
        rt = hi.IsolatedRuntime(session_name="unit-test-session", root=self.root)
        rt.prepare()
        env = rt.env({"HERDR_ENV": "1", "PATH": r"C:\Windows", "USERPROFILE": r"C:\Users\x"})
        for key in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "HOME", "TMP", "TEMP"):
            self.assertTrue(Path(env[key]).is_relative_to(self.root), key)
        self.assertEqual(env["HERDR_CONFIG_PATH"], str(rt.config_path))
        self.assertNotIn("HERDR_ENV", env)
        herdr_keys = sorted(k for k in env if k.startswith("HERDR_"))
        self.assertEqual(herdr_keys, ["HERDR_CONFIG_PATH"])

    def test_command_uses_absolute_binary_and_explicit_session(self):
        rt = hi.IsolatedRuntime(session_name="unit-test-session", root=self.root)
        argv = rt.command("status")
        self.assertEqual(argv[0], str(hi.DEFAULT_BINARY))
        self.assertTrue(Path(argv[0]).is_absolute())
        self.assertEqual(argv[1:3], ["--session", "unit-test-session"])

    def test_resolution_record_lists_expected_paths(self):
        rt = hi.IsolatedRuntime(session_name="unit-test-session", root=self.root)
        rt.prepare()
        record = rt.resolution_record()
        self.assertEqual(record["binary_sha256_expected"], hi.EXPECTED_BINARY_SHA256)
        self.assertIn(str(rt.config_home / "herdr"), record["expected_config_dirs"])
        self.assertTrue(record["expected_session_dir"].endswith("unit-test-session"))


if __name__ == "__main__":
    unittest.main()
