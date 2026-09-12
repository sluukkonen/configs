import importlib.util
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / ".local/bin/pinentry-auto"
spec = importlib.util.spec_from_loader("pinentry_auto", SourceFileLoader("pinentry_auto", str(SCRIPT)))
pinentry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pinentry)


class PinentryTests(unittest.TestCase):
    def select(self, platform, available, path_result=None):
        with mock.patch.object(pinentry.sys, "platform", platform), \
                mock.patch.object(pinentry.shutil, "which", return_value=path_result), \
                mock.patch.object(pinentry.Path, "is_file", autospec=True,
                                  side_effect=lambda path: str(path) in available), \
                mock.patch.object(pinentry.os, "access", side_effect=lambda path, mode: path in available):
            return pinentry.find_pinentry()

    def test_macos_prefers_pinentry_mac_from_path(self):
        self.assertEqual(self.select("darwin", {"/custom/pinentry-mac", "/opt/homebrew/bin/pinentry-mac"},
                                     "/custom/pinentry-mac"), "/custom/pinentry-mac")

    def test_macos_finds_both_homebrew_prefixes_without_path(self):
        for prefix in ("/opt/homebrew", "/usr/local"):
            with self.subTest(prefix=prefix):
                program = prefix + "/bin/pinentry-mac"
                self.assertEqual(self.select("darwin", {program}), program)

    def test_linux_uses_system_choice_even_if_pinentry_mac_is_on_path(self):
        self.assertEqual(self.select("linux", {"/usr/bin/pinentry", "/custom/pinentry-mac"},
                                     "/custom/pinentry-mac"), "/usr/bin/pinentry")

    def test_missing_program_fails(self):
        for platform in ("darwin", "linux"):
            with self.subTest(platform=platform), self.assertRaises(FileNotFoundError):
                self.select(platform, set())

    def test_non_executable_program_is_rejected(self):
        with mock.patch.object(pinentry.sys, "platform", "linux"), \
                mock.patch.object(pinentry.Path, "is_file", return_value=True), \
                mock.patch.object(pinentry.os, "access", return_value=False):
            with self.assertRaises(FileNotFoundError):
                pinentry.find_pinentry()

    def test_exec_preserves_arguments_and_environment(self):
        with mock.patch.object(pinentry, "find_pinentry", return_value="/chosen/pinentry"), \
                mock.patch.object(pinentry.sys, "argv", [str(SCRIPT), "--display", ":0"]), \
                mock.patch.object(pinentry.os, "execv") as execute:
            original_environment = dict(os.environ)
            pinentry.main()
            execute.assert_called_once_with("/chosen/pinentry", ["/chosen/pinentry", "--display", ":0"])
            self.assertEqual(dict(os.environ), original_environment)

    def test_exec_failure_reports_on_stderr_only(self):
        with mock.patch.object(pinentry, "find_pinentry", return_value="/chosen/pinentry"), \
                mock.patch.object(pinentry.os, "execv", side_effect=PermissionError("not executable")), \
                mock.patch.object(pinentry.sys, "stderr") as errors, \
                mock.patch.object(pinentry.sys, "stdout") as output:
            self.assertEqual(pinentry.main(), 1)
            self.assertTrue(errors.write.called)
            output.write.assert_not_called()

    def test_wrapper_is_executable_and_shared_config_uses_it(self):
        self.assertTrue(os.access(SCRIPT, os.X_OK))
        config = SCRIPT.parents[2] / ".gnupg/gpg-agent.conf"
        self.assertIn("pinentry-program ~/.local/bin/pinentry-auto\n", config.read_text())


if __name__ == "__main__":
    unittest.main()
