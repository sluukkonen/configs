import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
COMMAND_PATH = ".local/bin/configs"
spec = importlib.util.spec_from_loader("configs", SourceFileLoader("configs", str(REPOSITORY / COMMAND_PATH)))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class InstallerFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="configs tests ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repository = self.root / "source repository"
        self.target = self.root / "home directory"
        self.repository.mkdir()
        self.target.mkdir()
        self.git("init", "-q")
        self.source(COMMAND_PATH, (REPOSITORY / COMMAND_PATH).read_text(), 0o755)

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repository), "-c", "core.excludesFile=/dev/null", *args],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def commit(self, repository, message):
        subprocess.run(
            ["git", "-C", str(repository), "-c", "user.name=Configs Tests",
             "-c", "user.email=configs@example.invalid", "-c", "commit.gpgsign=false",
             "-c", "core.hooksPath=/dev/null", "commit", "-qm", message],
            check=True, capture_output=True,
        )

    def source(self, relative=".zshrc", contents="original\n", mode=0o644):
        path = self.repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        path.chmod(mode)
        self.git("add", "--", relative)
        return path

    def installed(self, relative=".zshrc", contents="original\n", mode=0o644):
        path = self.target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        path.chmod(mode)
        return path

    def run_sync(self, command="apply", expected=0, *options):
        result = subprocess.run(
            [sys.executable, str(self.repository / COMMAND_PATH), command,
             "--target", str(self.target), *options],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def state(self):
        return json.loads((self.target / sync.STATE_PATH).read_text())

    def tree(self):
        return {str(path.relative_to(self.target)): (
            path.lstat().st_mode, path.lstat().st_mtime_ns,
            os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None,
        ) for path in self.target.rglob("*")}

    def plan(self):
        state = sync.load_state(self.target)
        operations, conflicts, _ = sync.make_plan(self.repository, self.target, state)
        self.assertEqual(conflicts, [])
        return state, operations


class InstallerTests(InstallerFixture):
    def test_install_idempotence_and_uncommitted_update(self):
        source = self.source()
        self.assertIn("INSTALL .zshrc", self.run_sync())
        installed = self.target / ".zshrc"
        self.assertFalse(installed.is_symlink())
        before = installed.stat().st_mtime_ns
        before_tree = self.tree()
        self.assertNotIn("UPDATE", self.run_sync())
        self.assertEqual(installed.stat().st_mtime_ns, before)
        self.assertEqual(before_tree, self.tree())
        source.write_text("repository edit\n")
        self.assertIn("UPDATE .zshrc", self.run_sync())
        self.assertEqual(installed.read_text(), "repository edit\n")
        self.assertEqual(self.state()["repository"], str(self.repository))

    def test_diff_is_read_only_and_displays_text_and_modes(self):
        source = self.source()
        before = self.tree()
        self.assertIn("+original", self.run_sync("diff"))
        self.assertEqual(before, self.tree())
        self.run_sync()
        source.write_text("updated\n")
        source.chmod(0o755)
        before = self.tree()
        output = self.run_sync("diff")
        self.assertIn("-original", output)
        self.assertIn("+updated", output)
        self.assertIn("mode 644 -> 755", output)
        self.assertEqual(before, self.tree())

    def test_adopt_identical_restrictive_file(self):
        self.source()
        installed = self.installed(mode=0o600)
        before = installed.stat().st_mtime_ns
        self.assertIn("ADOPT", self.run_sync())
        self.assertEqual(installed.stat().st_mtime_ns, before)
        self.assertEqual(self.state()["files"][".zshrc"]["mode"], 0o600)

    def test_diff_color_preserves_plain_output_and_missing_newline_marker(self):
        self.source(contents="++repository\n")
        self.installed(contents="--local")
        before = self.tree()
        plain = self.run_sync("diff", 1, "--color", "never")
        self.assertNotIn("\033[", self.run_sync("diff", expected=1))
        colored = self.run_sync("diff", 1, "--color", "always")
        self.assertIn("\033[1m--- installed/.zshrc\033[0m", colored)
        self.assertIn("\033[36m@@", colored)
        self.assertIn("\033[31m---local\033[0m", colored)
        self.assertIn("\033[32m+++repository\033[0m", colored)
        self.assertEqual(re.sub(r"\x1b\[[0-9;]*m", "", colored), plain)
        self.assertEqual(before, self.tree())

    def test_diff_color_policy(self):
        for tty, env, expected in ((True, {}, True), (False, {}, False),
                                   (True, {"NO_COLOR": "1"}, False),
                                   (True, {"TERM": "dumb"}, False),
                                   (True, {"NO_COLOR": ""}, True)):
            with self.subTest(tty=tty, env=env):
                with mock.patch.object(sync.sys.stdout, "isatty", return_value=tty), mock.patch.dict(os.environ, env, clear=True):
                    self.assertEqual(sync.use_color("auto"), expected)
                    self.assertEqual(sync.use_color(None), expected)
                    self.assertTrue(sync.use_color("always"))
                    self.assertFalse(sync.use_color("never"))
        for command in ("apply", "update", "repo", "prune"):
            self.assertIn("only supported for diff", self.run_sync(command, 2, "--color", "always"))

    def test_diff_uses_delta_for_terminal_output_without_changing_target(self):
        self.source(contents="repository\n", mode=0o755)
        self.installed(contents="local")
        self.source(".binary", "\0binary")
        operations, conflicts, _ = sync.make_plan(self.repository, self.target, sync.load_state(self.target))
        before = self.tree()
        output = io.StringIO()
        with mock.patch.object(sync.sys, "stdout", output), \
                mock.patch.object(output, "isatty", return_value=True), \
                mock.patch.object(sync.shutil, "which", return_value="/tools/delta"), \
                mock.patch.object(sync.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            sync.show_diff_plan(operations, conflicts, [".obsolete"], True)
        self.assertEqual(run.call_args.args[0], ["/tools/delta", "--color-only"])
        report = run.call_args.kwargs["input"]
        for expected in ("CONFLICT .zshrc", "-local", "+repository", "\\ No newline at end of file",
                         "mode 644 -> 755", "Binary contents differ", "NO LONGER SELECTED"):
            self.assertIn(expected, report)
        self.assertNotIn("\033[", report)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(before, self.tree())

    def test_diff_delta_fallback_and_output_policy(self):
        self.source()
        _, operations = self.plan()
        for tty, color, available, failure in (
            (False, True, True, None),
            (True, False, True, None),
            (True, True, False, None),
            (True, True, True, OSError("cannot execute")),
            (True, True, True, 2),
        ):
            with self.subTest(tty=tty, color=color, available=available, failure=failure):
                output, errors = io.StringIO(), io.StringIO()
                with mock.patch.object(sync.sys, "stdout", output), \
                        mock.patch.object(sync.sys, "stderr", errors), \
                        mock.patch.dict(os.environ, {"PAGER": ""}), \
                        mock.patch.object(output, "isatty", return_value=tty), \
                        mock.patch.object(sync.shutil, "which", return_value="/tools/delta" if available else None), \
                        mock.patch.object(sync.subprocess, "run") as run:
                    if isinstance(failure, OSError):
                        run.side_effect = failure
                    else:
                        run.return_value = subprocess.CompletedProcess([], failure or 0)
                    sync.show_diff_plan(operations, [], [], color)
                self.assertIn("INSTALL .zshrc", output.getvalue())
                self.assertIn("+original", output.getvalue())
                self.assertEqual("\033[" in output.getvalue(), color)
                self.assertEqual(run.called, tty and color and available)
                self.assertEqual(bool(errors.getvalue()), failure is not None)

    def test_diff_does_not_launch_delta_for_empty_report(self):
        output = io.StringIO()
        with mock.patch.object(sync.sys, "stdout", output), \
                mock.patch.object(output, "isatty", return_value=True), \
                mock.patch.object(sync.shutil, "which", return_value="/tools/delta"), \
                mock.patch.object(sync.subprocess, "run") as run:
            sync.show_diff_plan([], [], [], True)
        run.assert_not_called()
        self.assertEqual(output.getvalue(), "")

    def test_builtin_diff_uses_pager_with_and_without_color(self):
        self.source()
        _, operations = self.plan()
        for color in (True, False):
            for env, expected in (({}, ["less", "-FRX"]),
                                  ({"PAGER": '"/tools/my pager" --option'}, ["/tools/my pager", "--option"])):
                with self.subTest(color=color, env=env):
                    output = io.StringIO()
                    with mock.patch.object(sync.sys, "stdout", output), \
                            mock.patch.object(output, "isatty", return_value=True), \
                            mock.patch.dict(os.environ, env, clear=True), \
                            mock.patch.object(sync.shutil, "which", side_effect=lambda name: None if name == "delta" else name), \
                            mock.patch.object(sync.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
                        sync.show_diff_plan(operations, [], [], color)
                    self.assertEqual(run.call_args.args[0], expected)
                    report = run.call_args.kwargs["input"]
                    self.assertIn("+original", report)
                    self.assertEqual("\033[" in report, color)
                    self.assertEqual(output.getvalue(), "")

    def test_builtin_pager_fallback_and_output_policy(self):
        for tty, env, available, failure, warning in (
            (False, {}, True, None, False),
            (True, {"TERM": "dumb"}, True, None, False),
            (True, {"PAGER": ""}, True, None, False),
            (True, {"PAGER": "missing-pager"}, False, None, False),
            (True, {"PAGER": "'"}, True, None, True),
            (True, {}, True, OSError("cannot execute"), True),
            (True, {}, True, 2, True),
        ):
            with self.subTest(tty=tty, env=env, available=available, failure=failure):
                output, errors = io.StringIO(), io.StringIO()
                with mock.patch.object(sync.sys, "stdout", output), \
                        mock.patch.object(sync.sys, "stderr", errors), \
                        mock.patch.object(output, "isatty", return_value=tty), \
                        mock.patch.dict(os.environ, env, clear=True), \
                        mock.patch.object(sync.shutil, "which", return_value="pager" if available else None), \
                        mock.patch.object(sync.subprocess, "run") as run:
                    if isinstance(failure, OSError):
                        run.side_effect = failure
                    else:
                        run.return_value = subprocess.CompletedProcess([], failure or 0)
                    sync.page_report("report\n")
                self.assertEqual(output.getvalue(), "report\n")
                self.assertEqual(bool(errors.getvalue()), warning)
                self.assertEqual(run.called, failure is not None)

    def test_builtin_pager_does_not_launch_for_empty_report(self):
        with mock.patch.object(sync.subprocess, "run") as run:
            sync.page_report("")
        run.assert_not_called()

    def test_conflict_does_not_block_other_files(self):
        self.source(".vimrc")
        self.source(".zshrc")
        self.installed(contents="local\n")
        output = self.run_sync(expected=sync.CONFLICTS_EXIT)
        self.assertIn("CONFLICT", output)
        self.assertIn("INSTALL .vimrc", output)
        self.assertEqual((self.target / ".zshrc").read_text(), "local\n")
        self.assertEqual((self.target / ".vimrc").read_text(), "original\n")
        self.assertIn(".vimrc", self.state()["files"])
        self.assertNotIn(".zshrc", self.state()["files"])

    def test_diff_shows_conflicting_contents_and_missing_newline(self):
        self.source(contents="repository\n")
        self.installed(contents="local")
        before = self.tree()
        output = self.run_sync("diff", expected=1)
        self.assertIn("-local", output)
        self.assertIn("+repository", output)
        self.assertIn("\\ No newline at end of file", output)
        self.assertEqual(before, self.tree())

    def test_local_edits_and_deletions_conflict(self):
        self.source()
        self.run_sync()
        installed = self.target / ".zshrc"
        installed.write_text("local\n")
        before = self.tree()
        self.assertIn("CONFLICT", self.run_sync(expected=sync.CONFLICTS_EXIT))
        self.assertEqual(before, self.tree())
        installed.unlink()
        before = self.tree()
        self.assertIn("locally deleted", self.run_sync(expected=sync.CONFLICTS_EXIT))
        self.assertEqual(before, self.tree())

    def test_matching_source_resolves_local_content_edit(self):
        source = self.source()
        self.installed(mode=0o600)
        self.run_sync()
        (self.target / ".zshrc").write_text("agreed\n")
        source.write_text("agreed\n")
        self.assertIn("ADOPT", self.run_sync())
        self.assertEqual(self.state()["files"][".zshrc"]["mode"], 0o600)

    def test_local_permission_changes_conflict(self):
        self.source()
        self.run_sync()
        (self.target / ".zshrc").chmod(0o600)
        before = self.tree()
        self.assertIn("CONFLICT", self.run_sync(expected=sync.CONFLICTS_EXIT))
        self.assertEqual(before, self.tree())

    def test_executable_and_restrictive_permissions(self):
        source = self.source(".local/bin/example", "#!/bin/sh\n", 0o755)
        self.run_sync()
        installed = self.target / ".local/bin/example"
        self.assertEqual(stat.S_IMODE(installed.stat().st_mode), 0o755)
        self.source(".ssh/config", "Host example\n")
        self.installed(".ssh/config", "Host example\n", 0o600)
        self.run_sync()
        self.source(".ssh/config", "Host updated\n")
        source.chmod(0o644)
        self.run_sync()
        self.assertEqual(stat.S_IMODE(installed.stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE((self.target / ".ssh/config").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.target / sync.STATE_PATH).stat().st_mode), 0o600)

    def test_symlinked_destinations_conflict(self):
        # Install the installer first so the conflict is the only pending change.
        self.run_sync()
        source = self.source()
        destination = self.target / ".zshrc"
        outside = self.root / "unrelated"
        outside.write_text("original\n")
        for link in (source, outside, self.root / "missing"):
            with self.subTest(link=link):
                destination.symlink_to(link)
                before = self.tree()
                self.assertIn("destination is a symlink", self.run_sync(expected=sync.CONFLICTS_EXIT))
                self.assertEqual(before, self.tree())
                destination.unlink()

    def test_destination_directories_and_symlinked_parents_conflict(self):
        self.source(".config/tool/config")
        outside = self.root / "outside"
        outside.mkdir()
        (self.target / ".config").symlink_to(outside, target_is_directory=True)
        self.assertIn("symlinked parent", self.run_sync(expected=sync.CONFLICTS_EXIT))
        self.assertEqual(list(outside.iterdir()), [])
        (self.target / ".config").unlink()
        (self.target / ".config/tool/config").mkdir(parents=True)
        self.assertIn("not a regular file", self.run_sync(expected=sync.CONFLICTS_EXIT))

    def test_state_symlinks_and_corruption_prevent_installation(self):
        self.source()
        state_path = self.target / sync.STATE_PATH
        state_path.parent.mkdir(parents=True)
        state_path.symlink_to(self.root / "absent")
        self.assertIn("state must be a regular file", self.run_sync(expected=1))
        state_path.unlink()
        for contents in ("{", '{"version": 2}', '{"version": 1, "repository": "/repo", "files": {"../bad": {}}}'):
            state_path.write_text(contents)
            before = self.tree()
            self.assertIn("invalid installation state", self.run_sync(expected=1))
            self.assertEqual(before, self.tree())
        self.assertFalse((self.target / ".zshrc").exists())

    def test_state_parent_symlink_is_rejected(self):
        self.source()
        outside = self.root / "state"
        outside.mkdir()
        (self.target / ".local").mkdir()
        (self.target / ".local/state").symlink_to(outside, target_is_directory=True)
        self.assertIn("symlinked parent", self.run_sync(expected=1))
        self.assertEqual(list(outside.iterdir()), [])

    def test_excludes_tooling_and_untracked_files(self):
        for path in (
            ".gitignore", ".gitattributes", ".gitmodules", ".github/workflows/test.yml",
            "AGENTS.md", "README.md", "Brewfile", "Brewfile.lock.json", "init.sh",
            "tests/test_example.py", "docs/setup.md", "__pycache__/cached.pyc",
        ):
            self.source(path, "# tooling\n")
        (self.repository / "README.md").unlink()
        self.source(".zshrc")
        (self.repository / ".vimrc").write_text("untracked\n")
        self.run_sync()
        self.assertEqual(set(self.state()["files"]), {".zshrc", COMMAND_PATH})

    def test_new_configuration_paths_are_selected_automatically(self):
        paths = (".newrc", ".config/new-tool/config", "bin/new-command")
        for relative in paths:
            self.source(relative, "new config\n", 0o755 if relative.startswith("bin/") else 0o644)
        self.run_sync()
        self.assertEqual(set(self.state()["files"]), set(paths) | {COMMAND_PATH})
        for relative in paths:
            self.assertEqual((self.target / relative).read_text(), "new config\n")
        self.assertEqual(stat.S_IMODE((self.target / "bin/new-command").stat().st_mode), 0o755)

    def test_exclusions_do_not_match_nested_names_or_root_prefixes(self):
        paths = (
            ".codex/AGENTS.md", ".codex/skills/example/README.md",
            ".config/tool/tests/example.py", ".config/tool/.gitignore",
            ".gitignore_global", "tests-extra/config", "README.md.local",
        )
        for relative in paths:
            self.source(relative)
        self.run_sync()
        expected = set(paths)
        self.assertEqual(set(self.state()["files"]), expected | {COMMAND_PATH})
        for relative in expected:
            self.assertEqual((self.target / relative).read_text(), "original\n")

    def test_newly_excluded_files_and_their_baselines_are_preserved(self):
        self.source("support/new-file")
        self.run_sync()
        installed = self.target / "support/new-file"
        installed.write_text("local edit\n")
        installer = self.repository / COMMAND_PATH
        installer.write_text(installer.read_text().replace(
            "REPOSITORY_ONLY = {", 'REPOSITORY_ONLY = {"support",', 1))
        before = self.tree()
        baseline = self.state()["files"]["support/new-file"]
        for command in ("diff", "apply"):
            output = self.run_sync(command)
            self.assertIn("NO LONGER SELECTED (left installed) support/new-file", output)
            if command == "diff":
                self.assertEqual(before, self.tree())
            self.assertEqual(before["support/new-file"], self.tree()["support/new-file"])
            self.assertEqual(baseline, self.state()["files"]["support/new-file"])

    def test_configuration_cannot_target_installer_state(self):
        self.run_sync()
        for relative in (sync.STATE_PATH, ".local/state/configs/other", ".local/state/configs", ".local/state"):
            with self.subTest(relative=relative):
                self.source(relative)
                before = self.tree()
                self.assertIn("overlaps installation state", self.run_sync(expected=sync.CONFLICTS_EXIT))
                self.assertEqual(before, self.tree())
                self.git("rm", "-f", "--", relative)
                # Git prunes empty parent directories, so later iterations can
                # test a file at an ancestor path of the previous source.

    def test_skill_directories_keep_distinct_repository_paths(self):
        paths = (".codex/skills/example/SKILL.md", ".agents/skills/example/SKILL.md")
        for relative in paths:
            self.source(relative, relative + "\n")
        self.run_sync()
        self.assertEqual(set(self.state()["files"]), set(paths) | {COMMAND_PATH})
        for relative in paths:
            self.assertEqual((self.target / relative).read_text(), relative + "\n")

    def test_file_in_one_skill_root_does_not_collide_with_another_root(self):
        paths = (".agents/skills/example", ".codex/skills/example/SKILL.md")
        for relative in paths:
            self.source(relative)
        self.run_sync()
        for relative in paths:
            self.assertEqual((self.target / relative).read_text(), "original\n")

    def test_deleted_sources_are_skipped_and_symlinked_sources_rejected(self):
        source = self.source()
        source.unlink()
        self.assertIn("CHECKOUT DELETED .zshrc (excluded from installation)", self.run_sync())
        self.assertFalse(os.path.lexists(self.target / ".zshrc"))
        outside = self.root / "outside"
        outside.write_text("outside\n")
        source.symlink_to(outside)
        self.assertIn("tracked source is missing or symlinked", self.run_sync(expected=sync.CONFLICTS_EXIT))
        self.git("add", "--", ".zshrc")
        self.assertIn("unsupported", self.run_sync(expected=1))

    def test_source_parent_symlink_is_rejected(self):
        source = self.source(".config/tool/config")
        moved = self.root / "moved"
        source.parent.rename(moved)
        source.parent.symlink_to(moved, target_is_directory=True)
        self.assertIn("symlinked parent", self.run_sync(expected=1))

    def test_removed_files_are_reported_and_preserved(self):
        self.source()
        self.run_sync()
        self.git("rm", "-f", "--", ".zshrc")
        self.assertIn("NO LONGER SELECTED", self.run_sync())
        self.assertEqual((self.target / ".zshrc").read_text(), "original\n")
        self.assertIn(".zshrc", self.state()["files"])

    def test_skill_directory_symlinks_use_normal_parent_checks(self):
        self.run_sync()
        self.source(".codex/skills/commit/SKILL.md")
        unrelated = self.root / "other skills"
        unrelated.mkdir()
        link = self.target / ".codex/skills"
        link.parent.mkdir()
        link.symlink_to(unrelated, target_is_directory=True)
        before = self.tree()
        self.assertIn("symlinked parent", self.run_sync(expected=sync.CONFLICTS_EXIT))
        self.assertEqual(before, self.tree())
        self.assertTrue(link.is_symlink())
        self.assertEqual(list(unrelated.iterdir()), [])

    def test_unselected_skills_directory_is_untouched(self):
        relative = ".codex/skills/commit/SKILL.md"
        self.source(relative)
        other = self.installed(".agents/skills/commit/SKILL.md", "unrelated\n")
        before = other.stat().st_mtime_ns
        self.run_sync()
        self.assertEqual((self.target / relative).read_text(), "original\n")
        self.assertEqual(other.read_text(), "unrelated\n")
        self.assertEqual(other.stat().st_mtime_ns, before)
        self.assertEqual(set(self.state()["files"]), {relative, COMMAND_PATH})

    def test_atomic_replace_failure_preserves_old_file_and_cleans_temporary(self):
        source = self.source()
        self.run_sync()
        source.write_text("new\n")
        state, operations = self.plan()
        before = self.tree()
        with mock.patch.object(sync.os, "replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                sync.apply_plan(self.repository, self.target, state, operations)
        # The parent directory mtime may change when the temporary file is
        # created, but no installed file or manifest may change.
        self.assertEqual((self.target / ".zshrc").read_text(), "original\n")
        self.assertEqual(self.tree()[sync.STATE_PATH], before[sync.STATE_PATH])
        self.assertEqual(set(self.tree()), set(before))
        self.run_sync()

    def test_failed_manifest_write_is_recoverable_with_restrictive_mode(self):
        source = self.source()
        self.installed(mode=0o600)
        self.run_sync()
        source.write_text("new\n")
        state, operations = self.plan()
        with mock.patch.object(sync, "save_state", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                sync.apply_plan(self.repository, self.target, state, operations)
        self.assertEqual((self.target / ".zshrc").read_text(), "new\n")
        self.assertIn("ADOPT", self.run_sync())
        self.assertEqual(self.state()["files"][".zshrc"]["mode"], 0o600)

    def test_mid_apply_edit_is_not_overwritten(self):
        self.source()
        state, operations = self.plan()
        self.installed(contents="concurrent edit\n")
        with self.assertRaisesRegex(sync.SyncError, "changed during apply"):
            sync.apply_plan(self.repository, self.target, state, operations)
        self.assertEqual((self.target / ".zshrc").read_text(), "concurrent edit\n")

    def test_concurrent_installer_is_rejected(self):
        self.source()
        with sync.installation_lock(self.target):
            self.assertIn("another installer", self.run_sync(expected=1))
        self.assertEqual(list(self.target.iterdir()), [])

    def test_binary_diff_and_newline_in_filename(self):
        source = self.source(".config/file with\nnewline")
        source.write_bytes(b"\x00\xff")
        before = self.tree()
        self.assertIn("Binary contents differ", self.run_sync("diff"))
        self.assertEqual(before, self.tree())
        self.run_sync()
        self.assertEqual((self.target / ".config/file with\nnewline").read_bytes(), b"\x00\xff")

    def test_repository_move_updates_locator(self):
        self.source()
        self.run_sync()
        moved = self.root / "moved repository"
        self.repository.rename(moved)
        self.repository = moved
        self.run_sync()
        self.assertEqual(self.state()["repository"], str(moved))

    def test_target_inside_repository_is_rejected_including_parent_alias(self):
        target = self.repository / "target"
        target.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(self.repository, target_is_directory=True)
        self.target = alias / "target"
        self.assertIn("inside the repository", self.run_sync(expected=1))
        self.assertEqual(list(target.iterdir()), [])

    def test_configuration_destination_cannot_overlap_checkout(self):
        nested = self.target / ".config/checkout"
        nested.parent.mkdir()
        self.repository.rename(nested)
        self.repository = nested
        self.source(".config/checkout/file")
        self.assertIn("overlaps the repository", self.run_sync(expected=sync.CONFLICTS_EXIT))
        self.assertFalse((nested / "file").exists())

    def test_state_destination_cannot_overlap_checkout(self):
        nested = self.target / ".local/state/configs"
        nested.parent.mkdir(parents=True)
        self.repository.rename(nested)
        self.repository = nested
        self.source()
        self.assertIn("state would overlap", self.run_sync(expected=1))
        self.assertFalse((nested / "state.json").exists())

    def test_untracked_command_prevents_partial_migration(self):
        self.source()
        self.git("rm", "--cached", "--", COMMAND_PATH)
        before = self.tree()
        self.assertIn("git add .local/bin/configs", self.run_sync(expected=1))
        self.assertEqual(before, self.tree())


class PruneTests(InstallerFixture):
    def obsolete(self, *paths):
        for path in paths:
            self.source(path)
        self.run_sync()
        self.git("rm", "-f", "--", *paths)

    def test_prunes_obsolete_files_and_forgets_missing_files(self):
        self.obsolete("old/file", "missing")
        (self.target / "missing").unlink()
        self.installed("unmanaged")
        before = self.tree()
        output = self.run_sync("prune", 0, "--dry-run")
        self.assertIn("WOULD REMOVE old/file", output)
        self.assertIn("WOULD FORGET missing", output)
        self.assertEqual(before, self.tree())
        output = self.run_sync("prune")
        self.assertIn("REMOVE old/file", output)
        self.assertIn("FORGET missing", output)
        self.assertTrue((self.target / "old").is_dir())
        self.assertTrue((self.target / "unmanaged").exists())
        self.assertEqual(set(self.state()["files"]), {COMMAND_PATH})
        self.assertFalse((self.target / "old/file").exists())
        before = self.tree()
        self.run_sync("prune")
        self.assertEqual(before, self.tree())
        self.assertNotIn("NO LONGER SELECTED", self.run_sync("diff"))

    def test_conflicts_do_not_block_safe_files_or_forget_their_baselines(self):
        self.obsolete("content", "mode", "safe", "link", "directory")
        (self.target / "content").write_text("edited\n")
        (self.target / "mode").chmod(0o600)
        (self.target / "link").unlink()
        (self.target / "link").symlink_to(self.target / "content")
        (self.target / "directory").unlink()
        (self.target / "directory").mkdir()
        state = self.state()
        before = self.tree()
        self.run_sync("prune", 1, "--dry-run")
        self.assertEqual(before, self.tree())
        self.run_sync("prune", expected=1)
        self.assertFalse((self.target / "safe").exists())
        for path in ("content", "mode", "link", "directory"):
            self.assertEqual(before[path], self.tree()[path])
            self.assertEqual(state["files"][path], self.state()["files"][path])

    def test_case_only_rename_preserves_active_configuration(self):
        self.source("old")
        self.run_sync()
        if not (self.target / "OLD").exists():
            self.skipTest("requires a case-insensitive filesystem")
        self.git("mv", "old", "temporary-name")
        self.git("mv", "temporary-name", "OLD")
        self.run_sync()
        before = self.tree()
        self.assertIn("aliases an active configuration", self.run_sync("prune", 1, "--dry-run"))
        self.assertEqual(before, self.tree())
        self.assertIn("aliases an active configuration", self.run_sync("prune", expected=1))
        self.assertEqual(before, self.tree())
        self.run_sync()
        self.assertEqual((self.target / "OLD").read_text(), "original\n")

    def test_filesystem_alias_is_preserved_on_any_filesystem(self):
        self.obsolete("old", "safe")
        self.source("active")
        os.link(self.target / "old", self.target / "active")
        self.run_sync()
        self.assertIn("aliases an active configuration", self.run_sync("prune", expected=1))
        self.assertTrue((self.target / "old").exists())
        self.assertTrue((self.target / "active").exists())
        self.assertFalse((self.target / "safe").exists())

    def test_alias_created_after_planning_is_preserved(self):
        self.obsolete("old")
        self.source("active")
        state = self.state()
        operations, conflicts = sync.make_prune_plan(self.repository, self.target, state)
        self.assertEqual(conflicts, [])
        os.link(self.target / "old", self.target / "active")
        self.assertIn("aliases an active configuration", sync.prune_plan(self.target, state, operations)[0])
        self.assertTrue((self.target / "old").exists())

    def test_case_alias_of_reserved_directory_is_preserved(self):
        self.run_sync()
        if not (self.target / ".LOCAL").exists():
            self.skipTest("requires a case-insensitive filesystem")
        path = ".LOCAL/STATE/CONFIGS/obsolete"
        self.installed(path)
        state = self.state()
        snapshot, _ = sync.inspect(self.target, path)
        state["files"][path] = sync.file_record(snapshot)
        sync.save_state(self.target, state)
        before = self.tree()
        self.assertIn("aliases repository or installation state", self.run_sync("prune", expected=1))
        self.assertEqual(before, self.tree())

    def test_newly_excluded_file_can_be_pruned_despite_active_conflict(self):
        self.source("support/file")
        self.source()
        self.run_sync()
        installer = self.repository / COMMAND_PATH
        installer.write_text(installer.read_text().replace("REPOSITORY_ONLY = {", 'REPOSITORY_ONLY = {"support",', 1))
        (self.target / ".zshrc").write_text("active local edit\n")
        self.run_sync("prune")
        self.assertFalse((self.target / "support/file").exists())
        self.assertEqual((self.target / ".zshrc").read_text(), "active local edit\n")
        self.assertIn(".zshrc", self.state()["files"])

    def test_symlinked_parent_is_preserved(self):
        self.obsolete("old/file")
        outside = self.root / "outside"
        (self.target / "old").rename(outside)
        (self.target / "old").symlink_to(outside, target_is_directory=True)
        self.assertIn("symlinked parent", self.run_sync("prune", expected=1))
        self.assertTrue((outside / "file").exists())
        self.assertIn("old/file", self.state()["files"])

    def test_reserved_paths_are_preserved(self):
        nested = self.target / "checkout"
        self.repository.rename(nested)
        self.repository = nested
        self.run_sync()
        state = self.state()
        for path in ("checkout", "checkout/.git/config", ".local", ".local/state", sync.STATE_PATH):
            state["files"][path] = {"sha256": "0" * 64, "mode": 0o644}
        sync.save_state(self.target, state)
        before = self.tree()
        self.assertIn("overlaps", self.run_sync("prune", expected=1))
        self.assertEqual(before, self.tree())

    def test_invalid_selection_and_corrupt_state_abort_before_deleting(self):
        self.obsolete("old")
        self.git("rm", "--cached", "--", COMMAND_PATH)
        before = self.tree()
        self.assertIn("tracked .local/bin/configs", self.run_sync("prune", expected=1))
        self.assertEqual(before, self.tree())
        self.git("add", "--", COMMAND_PATH)
        (self.target / sync.STATE_PATH).write_text("{")
        before = self.tree()
        self.assertIn("invalid installation state", self.run_sync("prune", expected=1))
        self.assertEqual(before, self.tree())

    def test_missing_state_and_no_candidates_do_not_create_state(self):
        before = self.tree()
        self.run_sync("prune")
        self.assertEqual(before, self.tree())

    def test_prune_rechecks_removed_and_missing_destinations(self):
        self.obsolete("changed", "missing", "safe")
        (self.target / "missing").unlink()
        state = self.state()
        operations, conflicts = sync.make_prune_plan(self.repository, self.target, state)
        self.assertEqual(conflicts, [])
        (self.target / "changed").write_text("new edit\n")
        (self.target / "missing").write_text("new file\n")
        output = io.StringIO()
        with mock.patch.object(sync.sys, "stdout", output):
            conflicts = sync.prune_plan(self.target, state, operations)
        self.assertEqual(output.getvalue(), "REMOVE safe\n")
        self.assertEqual(len(conflicts), 2)
        self.assertFalse((self.target / "safe").exists())
        self.assertEqual((self.target / "changed").read_text(), "new edit\n")
        self.assertEqual((self.target / "missing").read_text(), "new file\n")
        self.assertIn("changed", self.state()["files"])
        self.assertIn("missing", self.state()["files"])

    def test_deletion_failure_retains_baseline(self):
        self.obsolete("old")
        state = self.state()
        operations, _ = sync.make_prune_plan(self.repository, self.target, state)
        before = self.tree()
        with mock.patch.object(Path, "unlink", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                sync.prune_plan(self.target, state, operations)
        self.assertEqual(before, self.tree())

    def test_failed_state_write_after_deletion_is_recoverable(self):
        self.obsolete("a", "b")
        state = self.state()
        operations, _ = sync.make_prune_plan(self.repository, self.target, state)
        with mock.patch.object(sync, "save_state", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                sync.prune_plan(self.target, state, operations)
        self.assertFalse((self.target / "a").exists())
        self.assertTrue((self.target / "b").exists())
        self.assertIn("a", self.state()["files"])
        self.assertIn("FORGET a", self.run_sync("prune"))
        self.assertEqual(set(self.state()["files"]), {COMMAND_PATH})

    def test_lock_and_dry_run_argument_validation(self):
        self.obsolete("old")
        before = self.tree()
        with sync.installation_lock(self.target):
            self.assertIn("another installer", self.run_sync("prune", expected=1))
        for command in ("diff", "apply", "update", "repo"):
            self.assertIn("only supported for prune", self.run_sync(command, 2, "--dry-run"))
        self.assertEqual(before, self.tree())


class UpdateCommandTests(InstallerFixture):
    def install_commands(self):
        for name in ("configs", "update-mac"):
            self.source(".local/bin/" + name, (REPOSITORY / ".local/bin" / name).read_text(), 0o755)
        self.run_sync()
        self.commands = self.root / "commands"
        self.commands.mkdir()
        self.log = self.root / "calls"
        for name in ("zsh", "brew", "softwareupdate"):
            command = self.commands / name
            command.write_text(
                "#!/bin/bash\nset -eu\nprintf '%s:%s:%s\\n' \"${0##*/}\" \"$PWD\" \"$*\" >> \"$CALL_LOG\"\n"
                + ('echo "No new software available."\n' if name == "softwareupdate" else "")
            )
            command.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.target), CALL_LOG=str(self.log),
                        PATH=str(self.commands) + os.pathsep + os.environ["PATH"])

    def test_update_commands_use_saved_repository(self):
        self.install_commands()
        result = subprocess.run(["bash", str(self.target / ".local/bin/update-mac")],
                                cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.log.read_text()
        self.assertIn("brew:{}:bundle install --no-upgrade".format(self.repository), calls)
        self.assertIn("brew:{}:cleanup".format(self.repository), calls)

    def test_missing_or_invalid_locator_stops_before_external_commands(self):
        self.install_commands()
        state_path = self.target / sync.STATE_PATH
        for contents in (None, "[]", '{"version":1,"repository":"/absent"}'):
            if contents is None:
                state_path.unlink()
            else:
                state_path.write_text(contents)
            for command in ([sys.executable, str(self.target / COMMAND_PATH), "update"],
                            ["bash", str(self.target / ".local/bin/update-mac")]):
                result = subprocess.run(command,
                                        cwd=self.root, env=self.env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Run python3", result.stderr)
                self.assertFalse(self.log.exists())

    def test_init_works_from_another_directory_and_stops_on_conflicts(self):
        shutil.copyfile(REPOSITORY / "init.sh", self.repository / "init.sh")
        self.source()
        (self.target / ".zgenom").mkdir()
        env = dict(os.environ, HOME=str(self.target))
        result = subprocess.run(["bash", str(self.repository / "init.sh")], cwd=self.root,
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.target / ".zshrc").write_text("local\n")
        result = subprocess.run(["bash", str(self.repository / "init.sh")], cwd=self.root,
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.target / ".zshrc").read_text(), "local\n")

    def test_init_installs_missing_zgenom_once_even_with_conflicts(self):
        shutil.copyfile(REPOSITORY / "init.sh", self.repository / "init.sh")
        self.source()
        commands = self.root / "commands"
        commands.mkdir()
        log = self.root / "clone calls"
        git = commands / "git"
        real_git = shutil.which("git")
        git.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\nfrom pathlib import Path\n"
            "if sys.argv[1] == 'clone':\n"
            "    with Path({!r}).open('a') as log:\n"
            "        log.write(repr(sys.argv[1:]) + '\\n')\n"
            "    Path(sys.argv[-1]).mkdir()\n"
            "else:\n"
            "    os.execv({!r}, [{!r}] + sys.argv[1:])\n".format(str(log), real_git, real_git)
        )
        git.chmod(0o755)
        env = dict(os.environ, HOME=str(self.target), PATH=str(commands) + os.pathsep + os.environ["PATH"])
        for _ in range(2):
            result = subprocess.run(["bash", str(self.repository / "init.sh")], cwd=self.root,
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.target / COMMAND_PATH).is_file())
        calls = log.read_text()
        self.assertEqual(len(calls.splitlines()), 1)
        self.assertIn("https://github.com/jandamm/zgenom.git", calls)
        (self.target / ".zgenom").rmdir()
        (self.target / ".zshrc").write_text("local conflict\n")
        result = subprocess.run(["bash", str(self.repository / "init.sh")], cwd=self.root,
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, sync.CONFLICTS_EXIT, result.stdout + result.stderr)
        # Other files may already be applied, so .zshrc must not be left without zgenom.
        self.assertEqual(len(log.read_text().splitlines()), 2)
        self.assertTrue((self.target / ".zgenom").is_dir())
        self.assertEqual((self.target / ".zshrc").read_text(), "local conflict\n")


class ConfigCommandTests(InstallerFixture):
    def setUp(self):
        super().setUp()
        self.source()
        self.run_sync()
        self.env = dict(os.environ, HOME=str(self.target),
                        PATH=str(self.target / ".local/bin") + os.pathsep + os.environ["PATH"])

    def run_command(self, *arguments, expected=0):
        result = subprocess.run(["configs", *arguments], cwd=self.root, env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_installed_commands_use_checkout_and_are_executable(self):
        self.assertEqual(self.run_command("repo").strip(), str(self.repository))
        (self.repository / ".zshrc").write_text("changed\n")
        before = self.tree()
        self.assertIn("UPDATE .zshrc", self.run_command("diff"))
        self.assertEqual(before, self.tree())
        installer = self.repository / COMMAND_PATH
        installer.write_text(installer.read_text().replace("Configuration applied.", "Fresh installer applied."))
        self.assertIn("Fresh installer applied.", self.run_command("apply"))
        self.assertEqual((self.target / ".zshrc").read_text(), "changed\n")
        self.assertEqual((self.target / COMMAND_PATH).read_bytes(), installer.read_bytes())

    def test_alternate_target_uses_its_own_state(self):
        # The installed command must not mistake its Git home for the checkout,
        # even when --target points to a different installation.
        subprocess.run(["git", "init", "-q", str(self.target)], check=True, capture_output=True)
        other = self.root / "other home"
        other.mkdir()
        subprocess.run([sys.executable, str(self.repository / COMMAND_PATH), "apply", "--target", str(other)],
                       check=True, capture_output=True)
        before = self.tree()
        (self.repository / ".zshrc").write_text("other target\n")
        self.run_command("apply", "--target", str(other))
        self.assertEqual((other / ".zshrc").read_text(), "other target\n")
        self.assertEqual(before, self.tree())

    def test_installed_commands_use_saved_checkout_when_home_is_a_git_repository(self):
        subprocess.run(["git", "init", "-q", str(self.target)], check=True, capture_output=True)
        self.assertEqual(self.run_command("repo").strip(), str(self.repository))
        (self.repository / ".zshrc").write_text("working copy edit\n")
        before = self.tree()
        self.assertIn("UPDATE .zshrc", self.run_command("diff"))
        self.assertEqual(before, self.tree())
        self.run_command("apply")
        self.assertEqual((self.target / ".zshrc").read_text(), "working copy edit\n")
        self.git("add", "--", ".zshrc")
        self.setup_remote()
        self.publish()
        self.run_command("update")
        self.assertEqual((self.target / ".zshrc").read_text(), "upstream config\n")

    def test_moved_checkout_recovers_through_direct_apply(self):
        moved = self.root / "moved repository"
        self.repository.rename(moved)
        self.repository = moved
        self.assertIn("Run python3", self.run_command("repo", expected=1))
        self.run_sync()
        self.assertEqual(self.run_command("repo").strip(), str(moved))

    def test_symlinked_checkout_command_parent_is_rejected_before_dispatch(self):
        moved = self.root / "moved bin"
        (self.repository / ".local/bin").rename(moved)
        (self.repository / ".local/bin").symlink_to(moved, target_is_directory=True)
        self.assertIn("symlinked parent", self.run_command("apply", expected=1))

    def test_missing_and_corrupt_state_rejected_for_every_command(self):
        state_path = self.target / sync.STATE_PATH
        for contents in (None, "[]", "{", '{"version": 2}'):
            if contents is None:
                state_path.unlink()
            else:
                state_path.write_text(contents)
            before = self.tree()
            for command in ("diff", "apply", "update", "repo"):
                self.assertIn("Run python3", self.run_command(command, expected=1))
                self.assertEqual(before, self.tree())

    def test_explicit_command_required(self):
        self.assertIn("usage:", self.run_command(expected=2))

    def test_installed_diff_forwards_color_option(self):
        (self.repository / ".zshrc").write_text("changed\n")
        self.assertIn("\033[32m+changed\033[0m", self.run_command("diff", "--color", "always"))
        self.assertNotIn("\033[", self.run_command("diff", "--color", "never"))

    def test_installed_prune_forwards_preview_and_alternate_target(self):
        other = self.root / "other home"
        other.mkdir()
        self.source("old")
        subprocess.run([sys.executable, str(self.repository / COMMAND_PATH), "apply", "--target", str(other)],
                       check=True, capture_output=True)
        self.git("rm", "-f", "--", "old")
        before = self.tree()
        state_bytes = (other / sync.STATE_PATH).read_bytes()
        self.assertIn("WOULD REMOVE old", self.run_command("prune", "--target", str(other), "--dry-run"))
        self.assertTrue((other / "old").exists())
        self.assertEqual((other / sync.STATE_PATH).read_bytes(), state_bytes)
        self.run_command("prune", "--target", str(other))
        self.assertFalse((other / "old").exists())
        self.assertEqual(before, self.tree())

    def setup_remote(self):
        self.commit(self.repository, "Initial configs")
        self.remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "--bare", str(self.repository), str(self.remote)],
                       check=True, capture_output=True)
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "HEAD")
        self.upstream = self.root / "upstream checkout"
        subprocess.run(["git", "clone", str(self.remote), str(self.upstream)],
                       check=True, capture_output=True)

    def publish(self, relative=".zshrc", contents="upstream config\n"):
        (self.upstream / relative).write_text(contents)
        subprocess.run(["git", "-C", str(self.upstream), "add", "--", relative],
                       check=True, capture_output=True)
        self.commit(self.upstream, "Update configs")
        subprocess.run(["git", "-C", str(self.upstream), "push"], check=True, capture_output=True)

    def test_update_pulls_and_applies_with_fresh_installer(self):
        self.setup_remote()
        self.publish()
        installer = self.upstream / COMMAND_PATH
        self.publish(COMMAND_PATH, installer.read_text().replace("Configuration applied.", "Updated installer applied."))
        self.assertIn("Updated installer applied.", self.run_command("update"))
        self.assertEqual((self.target / ".zshrc").read_text(), "upstream config\n")
        self.assertEqual((self.target / COMMAND_PATH).read_bytes(), installer.read_bytes())
        self.assertFalse((self.target / ".zgenom").exists())

    def install_zgenom(self, status=0):
        log = self.root / "zgenom calls"
        script = self.target / ".zgenom/zgenom.zsh"
        script.parent.mkdir()
        # Record the installed .zshrc to show plugins update after applying.
        script.write_text(
            'ZGEN_DIR={sources}\nzgenom() {{ print -r -- "$1 $(<{zshrc})" >> {log}; return {status}; }}\n'.format(
                sources=shlex.quote(str(script.parent / "sources")),
                zshrc=shlex.quote(str(self.target / ".zshrc")), log=shlex.quote(str(log)), status=status))
        return log

    def test_update_refreshes_zgenom_after_applying(self):
        if shutil.which("zsh") is None:
            self.skipTest("requires zsh")
        log = self.install_zgenom()
        self.setup_remote()
        self.publish()
        self.run_command("update")
        self.assertEqual(log.read_text(), "selfupdate upstream config\nupdate upstream config\n")
        # A freshly cloned zgenom has no sources directory until the first save.
        self.assertTrue((self.target / ".zgenom/sources").is_dir())

    def test_zgenom_failure_is_reported_after_applying(self):
        if shutil.which("zsh") is None:
            self.skipTest("requires zsh")
        log = self.install_zgenom(status=1)
        self.setup_remote()
        self.publish()
        self.assertIn("updating zgenom plugins failed", self.run_command("update", expected=1))
        self.assertEqual((self.target / ".zshrc").read_text(), "upstream config\n")
        self.assertEqual(log.read_text(), "selfupdate upstream config\n")

    def test_zgenom_updates_despite_unrelated_conflicts(self):
        if shutil.which("zsh") is None:
            self.skipTest("requires zsh")
        log = self.install_zgenom()
        self.source(".vimrc", "base\n")
        self.run_sync()
        self.setup_remote()
        self.publish(".vimrc", "upstream vim\n")
        self.publish()
        (self.target / ".vimrc").write_text("local conflict\n")
        output = self.run_command("update", expected=sync.CONFLICTS_EXIT)
        self.assertIn("Applied 1 change; 1 conflict remains.", output)
        self.assertIn("conflicts remain. Run configs resolve.", output)
        self.assertEqual((self.target / ".zshrc").read_text(), "upstream config\n")
        self.assertEqual((self.target / ".vimrc").read_text(), "local conflict\n")
        self.assertEqual(log.read_text(), "selfupdate upstream config\nupdate upstream config\n")

    def test_zgenom_is_not_updated_when_applying_fails(self):
        log = self.install_zgenom()
        self.setup_remote()
        # Git can track a symlink, but the installer refuses to plan one.
        (self.upstream / ".vimrc").symlink_to(".zshrc")
        subprocess.run(["git", "-C", str(self.upstream), "add", "--", ".vimrc"], check=True, capture_output=True)
        self.publish()
        self.assertIn("configuration application failed", self.run_command("update", expected=1))
        self.assertFalse(log.exists())

    def test_update_preserves_uncommitted_tracked_edits(self):
        self.source(".vimrc", "base\n")
        self.run_sync()
        self.setup_remote()
        (self.repository / ".vimrc").write_text("working copy edit\n")
        self.publish()
        self.run_command("update")
        self.assertEqual((self.target / ".vimrc").read_text(), "working copy edit\n")
        self.assertEqual((self.target / ".zshrc").read_text(), "upstream config\n")

    def test_divergent_history_stops_before_apply_even_with_merge_configured(self):
        self.setup_remote()
        self.source(".vimrc", "local commit\n")
        self.commit(self.repository, "Local change")
        self.git("config", "pull.ff", "true")
        self.git("config", "pull.rebase", "false")
        head = self.git("rev-parse", "HEAD").stdout
        self.publish()
        before = self.tree()
        self.run_command("update", expected=1)
        self.assertEqual(head, self.git("rev-parse", "HEAD").stdout)
        self.assertEqual(before, self.tree())

    def test_pull_failure_does_not_apply_working_copy(self):
        self.setup_remote()
        self.git("remote", "set-url", "origin", str(self.root / "missing remote"))
        (self.repository / ".zshrc").write_text("unapplied edit\n")
        before = self.tree()
        self.run_command("update", expected=1)
        self.assertEqual(before, self.tree())

    def test_update_conflict_keeps_pulled_repository_and_local_edit(self):
        self.setup_remote()
        self.publish()
        (self.target / ".zshrc").write_text("installed edit\n")
        before = self.tree()
        self.assertIn("Repository updated, but conflicts remain",
                      self.run_command("update", expected=sync.CONFLICTS_EXIT))
        self.assertEqual((self.repository / ".zshrc").read_text(), "upstream config\n")
        self.assertEqual(before, self.tree())

    def test_update_lock_prevents_pull(self):
        self.setup_remote()
        self.publish()
        head = self.git("rev-parse", "HEAD").stdout
        with sync.installation_lock(self.target):
            self.assertIn("another installer", self.run_command("update", expected=1))
        self.assertEqual(head, self.git("rev-parse", "HEAD").stdout)


class ExportImportTests(InstallerFixture):
    def setUp(self):
        super().setUp()
        # Keep the checkout under the home directory, like ~/Code/configs.
        nested = self.target / "Code/configs"
        nested.parent.mkdir()
        self.repository.rename(nested)
        self.repository = nested
        self.source()
        self.commit(self.repository, "Initial configs")
        self.run_sync()
        self.releases = {platform: self.release(platform) for platform in sync.DEFAULT_PLATFORMS}
        self.zgenom = self.target / ".zgenom"
        self.gitstatus = self.zgenom / "sources/romkatv/powerlevel10k/___/gitstatus"
        self.install_zgenom()
        self.archive = self.root / "export.tar.gz"
        self.other = self.root / "other home"
        self.other.mkdir()

    def release(self, platform):
        name = "gitstatusd-" + platform
        contents = ("binary " + platform).encode()
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            archive.addfile(info, io.BytesIO(contents))
        return output.getvalue()

    def install_info(self):
        lines = ["# uname_s_glob=\"ignored\"; uname_m_glob=\"*\"; file=\"x\"; version=\"v0\"; sha256=\"0\";"]
        for platform, data in self.releases.items():
            kernel, machine = platform.split("-")
            lines.append('uname_s_glob="{}"; uname_m_glob="{}"; file="gitstatusd-${{uname_s}}-${{uname_m}}"; '
                         'version="v1.5.4"; sha256="{}";'.format(kernel, machine, sync.digest(data)))
        return "\n".join(lines) + "\n"

    def install_zgenom(self):
        files = {
            "zgenom.zsh": "zgenom\n",
            "sources/init.zsh": "source /absolute/exporting/path\n",
            "sources/zcompdump_5.9": "dump\n",
            "sources/zcompdump_5.9.zwc": "compiled\n",
            "sources/romkatv/powerlevel10k/___/powerlevel10k.zsh-theme": "theme\n",
            "sources/romkatv/powerlevel10k/___/powerlevel10k.zsh-theme.zwc": "compiled\n",
            "sources/romkatv/powerlevel10k/___/gitstatus/install.info": self.install_info(),
        }
        for relative, contents in files.items():
            path = self.zgenom / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
        (self.zgenom / "sources/theme-link").symlink_to("romkatv/powerlevel10k/___/powerlevel10k.zsh-theme")

    def export(self, platforms=sync.DEFAULT_PLATFORMS):
        downloads = []
        self.stderr = io.StringIO()

        def download(url):
            downloads.append(url)
            platform = re.search(r"gitstatusd-(.+)\.tar\.gz$", url).group(1)
            return self.releases[platform]

        with mock.patch.object(sync, "download", side_effect=download), \
                mock.patch.object(sync.sys, "stdout", io.StringIO()), \
                mock.patch.object(sync.sys, "stderr", self.stderr):
            sync.export_archive(self.repository, self.target, self.archive, platforms)
        return downloads

    def members(self):
        with tarfile.open(str(self.archive)) as archive:
            return {member.name: member for member in archive.getmembers()}

    def read(self, name):
        with tarfile.open(str(self.archive)) as archive:
            return archive.extractfile(name).read()

    def run_import(self, command, *options, expected=0):
        result = subprocess.run(
            [sys.executable, str(command), "import", *options, "--target", str(self.other)],
            cwd=self.root, env=dict(os.environ, HOME=str(self.other)), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def extract(self):
        directory = self.root / "transfer"
        directory.mkdir(exist_ok=True)
        subprocess.run(["tar", "-xzf", str(self.archive), "-C", str(directory)], check=True)
        return directory / sync.EXPORT_ROOT

    def test_export_bundles_repository_plugins_and_gitstatusd(self):
        downloads = self.export(("linux-x86_64", "darwin-arm64"))
        self.assertEqual(downloads, [sync.GITSTATUS_URL.format(version="v1.5.4", file="gitstatusd-" + platform)
                                     for platform in ("linux-x86_64", "darwin-arm64")])
        members = self.members()
        root = sync.EXPORT_ROOT + "/"
        manifest = json.loads(self.read(root + "manifest.json"))
        self.assertEqual(manifest["branch"], self.git("symbolic-ref", "--short", "HEAD").stdout.decode().strip())
        self.assertEqual(manifest["repository"], "Code/configs")
        self.assertEqual(self.read(root + "configs"), (self.repository / COMMAND_PATH).read_bytes())
        self.assertEqual(stat.S_IMODE(members[root + "configs"].mode), 0o755)
        self.assertIn(root + "repository.bundle", members)
        self.assertIn(root + "zgenom/sources/romkatv/powerlevel10k/___/powerlevel10k.zsh-theme", members)
        self.assertEqual(members[root + "zgenom/sources/theme-link"].linkname,
                         "romkatv/powerlevel10k/___/powerlevel10k.zsh-theme")
        for excluded in ("sources/init.zsh", "sources/zcompdump_5.9", "sources/zcompdump_5.9.zwc",
                         "sources/romkatv/powerlevel10k/___/powerlevel10k.zsh-theme.zwc"):
            self.assertNotIn(root + "zgenom/" + excluded, members)
        usrbin = root + "zgenom/sources/romkatv/powerlevel10k/___/gitstatus/usrbin/"
        for platform in ("linux-x86_64", "darwin-arm64"):
            self.assertEqual(self.read(usrbin + "gitstatusd-" + platform), ("binary " + platform).encode())
            self.assertEqual(stat.S_IMODE(members[usrbin + "gitstatusd-" + platform].mode), 0o755)
        self.assertNotIn(usrbin + "gitstatusd-linux-aarch64", members)
        self.assertTrue(all(member.uid == 0 and member.uname == "" for member in members.values()))
        self.assertFalse(self.gitstatus.joinpath("usrbin").exists())

    def test_export_warns_about_and_omits_uncommitted_changes(self):
        committed = (self.repository / COMMAND_PATH).read_bytes()
        (self.repository / COMMAND_PATH).write_bytes(committed + b"# uncommitted\n")
        self.export(("linux-x86_64",))
        self.assertIn("uncommitted changes are not exported", self.stderr.getvalue())
        self.assertEqual(self.read(sync.EXPORT_ROOT + "/configs"), committed)

    def test_checksum_mismatch_and_unknown_platform_abort_without_archive(self):
        self.releases["linux-x86_64"] = self.release("tampered")
        with self.assertRaisesRegex(sync.SyncError, "checksum mismatch"):
            self.export(("linux-x86_64",))
        with self.assertRaisesRegex(sync.SyncError, "no gitstatusd release for plan9-mips"):
            self.export(("plan9-mips",))
        self.assertFalse(self.archive.exists())
        self.assertEqual([path.name for path in self.root.iterdir() if path.name.startswith(".configs-")], [])

    def test_gitstatus_release_follows_install_globs(self):
        install_info = ('uname_s_glob="linux"; uname_m_glob="armv8l"; file="gitstatusd-${uname_s}-aarch64"; '
                        'version="v1.5.4"; sha256="' + "a" * 64 + '";\n')
        self.assertEqual(sync.gitstatus_release(install_info, "linux-armv8l"),
                         ("gitstatusd-linux-aarch64", "v1.5.4", "a" * 64))
        with self.assertRaisesRegex(sync.SyncError, "invalid gitstatus"):
            sync.gitstatus_release(install_info.replace("v1.5.4", "$(touch x)"), "linux-armv8l")
        commented = '  # uname_s_glob="linux"; an indented note\n' + install_info
        self.assertEqual(sync.gitstatus_release(commented, "linux-armv8l")[0], "gitstatusd-linux-aarch64")

    def test_import_into_new_home_from_extracted_archive(self):
        self.export()
        export = self.extract()
        output = self.run_import(export / "configs")
        self.assertIn("Configuration imported.", output)
        checkout = self.other / "Code/configs"
        self.assertEqual((checkout / ".zshrc").read_text(), "original\n")
        self.assertEqual((self.other / ".zshrc").read_text(), "original\n")
        state = json.loads((self.other / sync.STATE_PATH).read_text())
        self.assertEqual(state["repository"], str(checkout.resolve()))
        self.assertEqual(subprocess.run(["git", "-C", str(checkout), "remote"], capture_output=True,
                                        text=True, check=True).stdout, "")
        usrbin = self.other / ".zgenom/sources/romkatv/powerlevel10k/___/gitstatus/usrbin"
        self.assertEqual(sorted(path.name for path in usrbin.iterdir()),
                         sorted("gitstatusd-" + platform for platform in sync.DEFAULT_PLATFORMS))
        self.assertTrue(os.access(usrbin / "gitstatusd-linux-x86_64", os.X_OK))
        self.assertFalse((self.other / ".zgenom/sources/init.zsh").exists())
        self.assertTrue((self.other / ".zgenom/sources/theme-link").is_symlink())
        self.assertFalse(os.path.lexists(self.other / ".zgenom.import"))
        self.assertFalse(os.path.lexists(self.other / ".zgenom.previous"))

    def test_reimport_fast_forwards_checkout_and_replaces_plugins(self):
        self.git("remote", "add", "origin", "https://example.invalid/configs.git")
        self.export()
        self.run_import(self.extract() / "configs")
        checkout = self.other / "Code/configs"
        self.assertEqual(subprocess.run(["git", "-C", str(checkout), "remote", "get-url", "origin"],
                                        capture_output=True, text=True, check=True).stdout.strip(),
                         "https://example.invalid/configs.git")
        self.source(contents="second version\n")
        self.commit(self.repository, "Second version")
        (self.zgenom / "zgenom.zsh").unlink()
        (self.zgenom / "new-plugin.zsh").write_text("new\n")
        self.export(("linux-x86_64",))
        self.assertIn("Configuration imported.", self.run_import(self.other / COMMAND_PATH, str(self.archive)))
        self.assertEqual((self.other / ".zshrc").read_text(), "second version\n")
        self.assertEqual((self.other / ".zgenom/new-plugin.zsh").read_text(), "new\n")
        self.assertFalse((self.other / ".zgenom/zgenom.zsh").exists())

    def test_unrelated_conflict_still_installs_configuration_and_plugins(self):
        self.source(".vimrc", "base\n")
        self.commit(self.repository, "Add vimrc")
        self.export()
        self.run_import(self.extract() / "configs")
        marker = self.other / ".zgenom/local-marker"
        marker.write_text("replaced\n")
        (self.other / ".vimrc").write_text("local edit\n")
        self.source(contents="second version\n")
        self.source(".vimrc", "second vim\n")
        self.commit(self.repository, "Second version")
        self.export(("linux-x86_64",))
        output = self.run_import(self.other / COMMAND_PATH, str(self.archive), expected=sync.CONFLICTS_EXIT)
        self.assertIn("conflicts remain. Run configs resolve", output)
        self.assertEqual((self.other / ".zshrc").read_text(), "second version\n")
        self.assertEqual((self.other / ".vimrc").read_text(), "local edit\n")
        self.assertFalse(marker.exists())

    def test_checkout_on_another_branch_is_not_changed(self):
        self.export()
        self.run_import(self.extract() / "configs")
        checkout = self.other / "Code/configs"
        subprocess.run(["git", "-C", str(checkout), "switch", "-q", "-c", "other"], check=True)
        self.assertIn("is on other", self.run_import(self.other / COMMAND_PATH, str(self.archive), expected=1))

    def test_repository_outside_home_needs_explicit_location(self):
        self.export()
        export = self.extract()
        manifest = json.loads((export / "manifest.json").read_text())
        manifest["repository"] = None
        (export / "manifest.json").write_text(json.dumps(manifest))
        self.assertIn("pass --repository", self.run_import(export / "configs", expected=1))
        location = self.root / "elsewhere/configs"
        self.run_import(export / "configs", str(export), "--repository", str(location))
        self.assertEqual((location / ".zshrc").read_text(), "original\n")
        self.assertEqual((self.other / ".zshrc").read_text(), "original\n")

    def test_unsafe_archives_are_rejected_before_extracting(self):
        root = sync.EXPORT_ROOT + "/"
        directory, file, link = tarfile.DIRTYPE, tarfile.REGTYPE, tarfile.SYMTYPE
        cases = {
            "parent": [(root + "../escaped", file, "")],
            "absolute link": [(root + "link", link, "/etc/passwd")],
            "escaping link": [(root + "link", link, "../../escaped")],
            "device": [(root + "device", tarfile.CHRTYPE, "")],
            "outside its directory": [(root + "zgenom/link", link, "../configs")],
            # These stay inside zgenom/ lexically, so only the link-walk and
            # duplicate checks can catch them.
            "write through link": [(root + "zgenom/a", directory, ""), (root + "zgenom/a/up", link, "../b"),
                                   (root + "zgenom/a/up/file", file, "")],
            "link through link": [(root + "zgenom/a/b", directory, ""), (root + "zgenom/a/b/up", link, "../../c"),
                                  (root + "zgenom/escape", link, "a/b/up/../../../escaped")],
            "duplicate": [(root + "zgenom/same", link, "other"), (root + "zgenom/same", file, "")],
        }
        for case, entries in cases.items():
            with self.subTest(case=case):
                with tarfile.open(str(self.archive), "w:gz") as archive:
                    for name, kind, target in entries:
                        info = tarfile.TarInfo(name)
                        info.type, info.linkname = kind, target
                        archive.addfile(info, io.BytesIO(b""))
                output = self.run_import(self.repository / COMMAND_PATH, str(self.archive), expected=1)
                self.assertRegex(output, "unsafe archive|unsupported archive entry|duplicate archive entry")
                self.assertFalse(os.path.lexists(self.root / "escaped"))
                self.assertFalse(os.path.lexists(self.other / "Code"))

    def test_truncated_or_corrupted_archives_report_cleanly(self):
        self.export(("linux-x86_64",))
        data = self.archive.read_bytes()
        corrupted = bytearray(data)
        corrupted[len(data) // 2:len(data) // 2 + 64] = bytes(64)
        for case, contents in (("truncated", data[:len(data) // 2]), ("corrupted", bytes(corrupted)),
                               ("not gzip", b"not an archive")):
            with self.subTest(case=case):
                self.archive.write_bytes(contents)
                output = self.run_import(self.repository / COMMAND_PATH, str(self.archive), expected=1)
                self.assertIn("invalid export archive", output)
                self.assertNotIn("Traceback", output)
                self.assertFalse(os.path.lexists(self.other / "Code"))

    def test_export_rejects_links_that_import_would_refuse(self):
        for target in ("/usr/share/outside", "../../outside"):
            with self.subTest(target=target):
                link = self.zgenom / "sources/outside-link"
                link.symlink_to(target)
                with self.assertRaisesRegex(sync.SyncError, "import would reject.*outside-link"):
                    self.export(("linux-x86_64",))
                self.assertFalse(self.archive.exists())
                link.unlink()

    def test_origin_credentials_are_not_exported(self):
        self.git("remote", "add", "origin", "https://user:secret-token@example.invalid/configs.git")
        self.export(("linux-x86_64",))
        manifest = json.loads(self.read(sync.EXPORT_ROOT + "/manifest.json"))
        self.assertEqual(manifest["origin"], "https://example.invalid/configs.git")
        self.assertNotIn(b"secret-token", self.read(sync.EXPORT_ROOT + "/manifest.json"))
        for url, expected in (("ssh://git:secret@host/configs.git", "ssh://git@host/configs.git"),
                              ("ssh://git@host/configs.git", "ssh://git@host/configs.git"),
                              ("git@github.com:owner/configs.git", "git@github.com:owner/configs.git")):
            self.assertEqual(sync.without_credentials(url), expected)

    def test_installed_export_forwards_archive_and_platforms(self):
        def run(*options):
            return subprocess.run([sys.executable, str(self.target / COMMAND_PATH), "export", *options],
                                  cwd=self.root, env=dict(os.environ, HOME=str(self.target)),
                                  capture_output=True, text=True)

        # Only the forwarded platform can produce this error, without any download.
        result = run("out.tar.gz", "--platform", "plan9-mips")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no gitstatusd release for plan9-mips", result.stderr)
        shutil.rmtree(self.gitstatus)
        result = run("out.tar.gz")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.root / "out.tar.gz").is_file())

    def test_export_and_import_argument_validation(self):
        for options, message in (
            (("apply", "--platform", "linux-x86_64"), "--platform is only supported for export"),
            (("export", "--platform", "Linux x86"), "--platform must look like"),
            (("export", "--repository", "elsewhere"), "--repository is only supported for import"),
            (("export", "one.tar.gz", "two.tar.gz"), "at most one archive"),
            (("import", "one.tar.gz", "two.tar.gz"), "at most one archive"),
            (("apply", "archive.tar.gz"), "paths are only supported"),
        ):
            with self.subTest(options=options):
                self.assertIn(message, self.run_sync(options[0], 2, *options[1:]))
        self.assertIn("pass the export archive", self.run_sync("import", 1))


class RepositoryPayloadTests(InstallerFixture):
    def test_complete_repository_payload_installs_and_reapplies(self):
        result = subprocess.run(
            ["git", "-C", str(REPOSITORY), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            check=True, stdout=subprocess.PIPE,
        )
        payload = {}
        for raw_path in result.stdout.split(b"\0"):
            if not raw_path:
                continue
            relative = os.fsdecode(raw_path)
            source = REPOSITORY / relative
            if not source.is_file() or not sync.is_installable(relative):
                continue
            copied = self.repository / relative
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, copied)
            copied.chmod(stat.S_IMODE(source.stat().st_mode))
            self.git("add", "--", relative)
            payload[relative] = copied.read_bytes()

        self.assertIn(COMMAND_PATH, payload)
        before = self.tree()
        self.run_sync("diff")
        self.assertEqual(before, self.tree())
        self.run_sync()
        self.assertEqual(set(self.state()["files"]), set(payload))
        for relative, contents in payload.items():
            self.assertEqual((self.target / relative).read_bytes(), contents)
            self.assertEqual((self.repository / relative).read_bytes(), contents)
        before = self.tree()
        self.run_sync()
        self.assertEqual(before, self.tree())


if __name__ == "__main__":
    unittest.main()
