import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import sys
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
                         "mode 644 -> 755", "Binary contents differ", "NO LONGER SELECTED", conflicts[0]):
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

    def test_conflict_prevents_all_writes(self):
        self.source(".vimrc")
        self.source(".zshrc")
        self.installed(contents="local\n")
        before = self.tree()
        self.assertIn("CONFLICT", self.run_sync(expected=1))
        self.assertEqual(before, self.tree())
        self.assertFalse((self.target / ".vimrc").exists())

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
        self.assertIn("CONFLICT", self.run_sync(expected=1))
        self.assertEqual(before, self.tree())
        installed.unlink()
        before = self.tree()
        self.assertIn("locally deleted", self.run_sync(expected=1))
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
        self.assertIn("CONFLICT", self.run_sync(expected=1))
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

    def test_owned_relative_symlink_is_replaced_without_changing_source(self):
        source = self.source()
        destination = self.target / ".zshrc"
        destination.symlink_to(os.path.relpath(source, destination.parent))
        before = source.read_bytes()
        self.assertIn("CONVERT", self.run_sync())
        self.assertFalse(destination.is_symlink())
        self.assertEqual(source.read_bytes(), before)

    def test_unrelated_and_broken_symlinks_conflict(self):
        self.source()
        destination = self.target / ".zshrc"
        outside = self.root / "unrelated"
        outside.write_text("original\n")
        for link in (outside, self.root / "missing"):
            with self.subTest(link=link):
                destination.symlink_to(link)
                before = self.tree()
                self.assertIn("unrelated symlink", self.run_sync(expected=1))
                self.assertEqual(before, self.tree())
                destination.unlink()

    def test_symlink_parent_traversal_cannot_masquerade_as_owned_link(self):
        self.source()
        outside = self.root / "outside"
        (outside / "subdirectory").mkdir(parents=True)
        (outside / ".zshrc").write_text("unrelated\n")
        (self.repository / "detour").symlink_to(outside / "subdirectory", target_is_directory=True)
        destination = self.target / ".zshrc"
        destination.symlink_to(self.repository / "detour/../.zshrc")
        self.assertEqual(destination.read_text(), "unrelated\n")
        before = self.tree()
        self.assertIn("unrelated symlink", self.run_sync(expected=1))
        self.assertEqual(before, self.tree())

    def test_destination_directories_and_symlinked_parents_conflict(self):
        self.source(".config/tool/config")
        outside = self.root / "outside"
        outside.mkdir()
        (self.target / ".config").symlink_to(outside, target_is_directory=True)
        self.assertIn("symlinked parent", self.run_sync(expected=1))
        self.assertEqual(list(outside.iterdir()), [])
        (self.target / ".config").unlink()
        (self.target / ".config/tool/config").mkdir(parents=True)
        self.assertIn("not a regular file", self.run_sync(expected=1))

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
        for relative in (sync.STATE_PATH, ".local/state/configs/other", ".local/state/configs", ".local/state"):
            with self.subTest(relative=relative):
                self.source(relative)
                before = self.tree()
                self.assertIn("overlaps installation state", self.run_sync(expected=1))
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

    def test_missing_and_symlinked_sources_are_rejected(self):
        source = self.source()
        source.unlink()
        self.assertIn("tracked source is missing", self.run_sync(expected=1))
        outside = self.root / "outside"
        outside.write_text("outside\n")
        source.symlink_to(outside)
        self.assertIn("tracked source is missing or symlinked", self.run_sync(expected=1))
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

    def test_skill_files_and_metadata_convert_in_place(self):
        skill = ".codex/skills/commit/SKILL.md"
        metadata = ".codex/skills/commit/agents/openai.yaml"
        for relative in (skill, metadata):
            source = self.source(relative)
            legacy = self.target / relative
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.symlink_to(source)
        extra = self.installed(".codex/skills/commit/notes.txt", "keep\n")
        before = self.tree()
        self.assertIn("CONVERT .codex/skills/commit/SKILL.md", self.run_sync("diff"))
        self.assertEqual(before, self.tree())
        self.run_sync()
        for relative in (skill, metadata):
            self.assertFalse((self.target / relative).is_symlink())
            destination = self.target / relative
            self.assertTrue(destination.is_file())
            self.assertFalse(destination.is_symlink())
            self.assertEqual(destination.read_text(), "original\n")
        self.assertEqual(set(self.state()["files"]), {skill, metadata, COMMAND_PATH})
        self.assertFalse((self.target / ".agents").exists())
        self.assertEqual(extra.read_text(), "keep\n")
        self.run_sync()

    def test_skill_directory_symlinks_use_normal_parent_checks(self):
        self.source(".codex/skills/commit/SKILL.md")
        unrelated = self.root / "other skills"
        unrelated.mkdir()
        legacy = self.target / ".codex/skills"
        legacy.parent.mkdir()
        legacy.symlink_to(unrelated, target_is_directory=True)
        before = self.tree()
        self.assertIn("symlinked parent", self.run_sync(expected=1))
        self.assertEqual(before, self.tree())
        self.assertTrue(legacy.is_symlink())
        self.assertEqual(list(unrelated.iterdir()), [])

    def test_unselected_skills_directory_is_untouched(self):
        relative = ".codex/skills/commit/SKILL.md"
        source = self.source(relative)
        legacy = self.target / relative
        legacy.parent.mkdir(parents=True)
        legacy.symlink_to(source)
        other = self.installed(".agents/skills/commit/SKILL.md", "unrelated\n")
        before = other.stat().st_mtime_ns
        self.run_sync()
        self.assertFalse(legacy.is_symlink())
        self.assertEqual(legacy.read_text(), "original\n")
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
        self.assertIn("overlaps the repository", self.run_sync(expected=1))
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
    def legacy_link(self, relative, source=None):
        link = self.target / relative
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(source if source is not None else self.repository / relative)
        return link

    def obsolete(self, *paths):
        for path in paths:
            self.source(path)
        self.run_sync()
        self.git("rm", "-f", "--", *paths)

    def test_default_prune_does_not_scan_for_legacy_links(self):
        self.obsolete("old")
        link = self.legacy_link("unrecorded")
        state = self.state()
        with mock.patch.object(sync.os, "scandir", side_effect=AssertionError("unexpected recursive scan")):
            operations, conflicts = sync.make_prune_plan(self.repository, self.target, state)
        self.assertEqual(conflicts, [])
        self.assertEqual([operation["destination"] for operation in operations], ["old"])
        self.assertIn("REMOVE old", self.run_sync("prune"))
        self.assertTrue(link.is_symlink())

    def test_discovers_legacy_links_without_creating_state(self):
        paths = (".codex/skills/commit/agents/openai.yaml", "old/location", "old/directory")
        links = [self.legacy_link(paths[0])]
        destination = self.target / paths[1]
        links.append(self.legacy_link(paths[1], os.path.relpath(self.repository / paths[1], destination.parent)))
        directory = self.repository / paths[2]
        directory.mkdir(parents=True)
        links.append(self.legacy_link(paths[2], directory))
        directory.rmdir()
        before = self.tree()
        preview = self.run_sync("prune", 0, "--dry-run", "--legacy-links")
        self.assertEqual(before, self.tree())
        for path in paths:
            self.assertIn("WOULD REMOVE " + path, preview)
        output = self.run_sync("prune", 0, "--legacy-links")
        for path, link in zip(paths, links):
            self.assertIn("REMOVE " + path, output)
            self.assertFalse(link.is_symlink())
            self.assertTrue(link.parent.is_dir())
        self.assertFalse((self.target / sync.STATE_PATH).exists())
        before = self.tree()
        self.assertEqual(self.run_sync("prune", 0, "--legacy-links"), "")
        self.assertEqual(before, self.tree())

    def test_legacy_links_with_state_are_removed_once(self):
        self.obsolete("old")
        (self.target / "old").unlink()
        link = self.legacy_link("old")
        self.assertEqual(self.run_sync("prune", 0, "--legacy-links").count("REMOVE old\n"), 1)
        self.assertFalse(link.is_symlink())
        self.assertNotIn("old", self.state()["files"])

    def test_unrecorded_link_cleanup_does_not_rewrite_state(self):
        self.run_sync()
        state_path = self.target / sync.STATE_PATH
        before = (state_path.read_bytes(), state_path.stat().st_mtime_ns)
        self.legacy_link("old")
        self.run_sync("prune", 0, "--legacy-links")
        self.assertEqual(before, (state_path.read_bytes(), state_path.stat().st_mtime_ns))

    def test_preserves_valid_unrelated_and_active_links(self):
        source = self.source("active")
        self.legacy_link("valid", self.source("valid-source"))
        self.legacy_link("unrelated", self.root / "missing")
        self.legacy_link("prefix", Path(str(self.repository) + "-other") / "missing")
        self.legacy_link("active")
        source.unlink()
        before = self.tree()
        self.assertEqual(self.run_sync("prune", 0, "--legacy-links"), "")
        self.assertEqual(before, self.tree())

    def test_does_not_follow_symlinked_directories_or_misleading_targets(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "subdirectory").mkdir()
        (outside / "dead").symlink_to(self.repository / "missing")
        self.legacy_link("parent", outside)
        (self.repository / "detour").symlink_to(outside / "subdirectory", target_is_directory=True)
        self.legacy_link("misleading", self.repository / "detour/../missing")
        before = self.tree()
        self.assertEqual(self.run_sync("prune", 0, "--legacy-links"), "")
        self.assertEqual(before, self.tree())
        self.assertTrue((outside / "dead").is_symlink())

    def test_discovery_excludes_repository_and_state_directories(self):
        nested = self.target / "checkout"
        self.repository.rename(nested)
        self.repository = nested
        self.run_sync()
        links = [self.legacy_link("checkout/dead"), self.legacy_link(".local/state/configs/dead")]
        self.assertEqual(self.run_sync("prune", 0, "--legacy-links"), "")
        self.assertTrue(all(link.is_symlink() for link in links))

    def test_link_changes_and_revived_targets_are_preserved(self):
        for change in ("retarget", "replace", "revive", "parent"):
            with self.subTest(change=change):
                relative = change + "/dead"
                link = self.legacy_link(relative)
                state = sync.load_state(self.target)
                operations, conflicts = sync.make_prune_plan(self.repository, self.target, state, legacy_links=True)
                self.assertEqual(conflicts, [])
                if change == "retarget":
                    link.unlink()
                    link.symlink_to(self.root / "missing")
                elif change == "replace":
                    link.unlink()
                    link.write_text("local content")
                elif change == "revive":
                    source = self.repository / relative
                    source.parent.mkdir()
                    source.write_text("restored")
                else:
                    moved = self.root / "moved"
                    link.parent.rename(moved)
                    link.parent.symlink_to(moved, target_is_directory=True)
                self.assertEqual(len(sync.prune_plan(self.target, state, operations)), 1)
                self.assertTrue(link.is_symlink() or link.is_file())

    def test_discovery_errors_are_reported(self):
        with mock.patch.object(sync.os, "scandir", side_effect=PermissionError("cannot read directory")):
            operations, conflicts = sync.make_prune_plan(self.repository, self.target, sync.load_state(self.target), legacy_links=True)
        self.assertEqual(operations, [])
        self.assertEqual(len(conflicts), 1)
        self.assertIn("could not scan", conflicts[0])

    def test_unreadable_link_does_not_hide_other_candidates(self):
        blocked = self.legacy_link("blocked")
        self.legacy_link("safe")
        readlink = os.readlink

        def read(path, *args, **kwargs):
            if Path(path) == blocked:
                raise PermissionError("cannot read link")
            return readlink(path, *args, **kwargs)

        with mock.patch.object(sync.os, "readlink", side_effect=read):
            operations, conflicts = sync.make_prune_plan(self.repository, self.target, sync.load_state(self.target), legacy_links=True)
        self.assertEqual([operation["destination"] for operation in operations], ["safe"])
        self.assertEqual(len(conflicts), 1)
        self.assertIn("cannot read link", conflicts[0])

    def test_target_permission_errors_are_not_treated_as_broken_links(self):
        link = self.legacy_link("blocked")
        source = self.repository / "blocked"
        path_stat = Path.stat

        def inspect_path(path, *args, **kwargs):
            if path == source:
                raise PermissionError("cannot inspect target")
            return path_stat(path, *args, **kwargs)

        with mock.patch.object(Path, "stat", inspect_path):
            operations, conflicts = sync.make_prune_plan(self.repository, self.target, sync.load_state(self.target), legacy_links=True)
        self.assertEqual(operations, [])
        self.assertEqual(len(conflicts), 1)
        self.assertIn("cannot inspect target", conflicts[0])
        self.assertTrue(link.is_symlink())

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
        conflicts = sync.prune_plan(self.target, state, operations)
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
            self.assertIn("--legacy-links is only supported for prune", self.run_sync(command, 2, "--legacy-links"))
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
        self.assertIn("brew:{}:bundle --upgrade".format(self.repository), calls)

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
        (self.target / ".zgen").mkdir()
        env = dict(os.environ, HOME=str(self.target))
        result = subprocess.run(["bash", str(self.repository / "init.sh")], cwd=self.root,
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.target / ".zshrc").write_text("local\n")
        result = subprocess.run(["bash", str(self.repository / "init.sh")], cwd=self.root,
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.target / ".zshrc").read_text(), "local\n")

    def test_init_installs_missing_zgen_once_and_only_after_successful_apply(self):
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
        self.assertIn("https://github.com/tarjoilija/zgen", calls)
        (self.target / ".zgen").rmdir()
        (self.target / ".zshrc").write_text("local conflict\n")
        result = subprocess.run(["bash", str(self.repository / "init.sh")], cwd=self.root,
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(log.read_text(), calls)
        self.assertFalse((self.target / ".zgen").exists())


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

    def test_installed_prune_forwards_legacy_links_to_alternate_target(self):
        other = self.root / "other home"
        other.mkdir()
        self.run_sync("apply", 0, "--target", str(other))
        state_bytes = (other / sync.STATE_PATH).read_bytes()
        link = other / "legacy"
        link.symlink_to(self.repository / "deleted")
        before = self.tree()
        self.assertEqual(self.run_command("prune", "--target", str(other), "--dry-run"), "")
        self.assertIn("WOULD REMOVE legacy", self.run_command(
            "prune", "--target", str(other), "--legacy-links", "--dry-run"))
        self.assertTrue(link.is_symlink())
        self.run_command("prune", "--target", str(other), "--legacy-links")
        self.assertFalse(link.is_symlink())
        self.assertEqual((other / sync.STATE_PATH).read_bytes(), state_bytes)
        self.assertEqual(before, self.tree())

    def commit(self, repository, message):
        subprocess.run(
            ["git", "-C", str(repository), "-c", "user.name=Configs Tests",
             "-c", "user.email=configs@example.invalid", "-c", "commit.gpgsign=false",
             "-c", "core.hooksPath=/dev/null", "commit", "-qm", message],
            check=True, capture_output=True,
        )

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
        self.assertFalse((self.target / ".zgen").exists())

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

    def test_apply_conflict_leaves_pulled_repository_and_target_unchanged(self):
        self.setup_remote()
        self.publish()
        (self.target / ".zshrc").write_text("installed edit\n")
        before = self.tree()
        self.assertIn("Repository updated, but configuration application failed", self.run_command("update", expected=1))
        self.assertEqual((self.repository / ".zshrc").read_text(), "upstream config\n")
        self.assertEqual(before, self.tree())

    def test_update_lock_prevents_pull(self):
        self.setup_remote()
        self.publish()
        head = self.git("rev-parse", "HEAD").stdout
        with sync.installation_lock(self.target):
            self.assertIn("another installer", self.run_command("update", expected=1))
        self.assertEqual(head, self.git("rev-parse", "HEAD").stdout)


class RepositoryMigrationTests(InstallerFixture):
    def test_complete_repository_payload_migrates_and_reapplies(self):
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
            legacy = self.target / relative
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.symlink_to(copied)
            payload[relative] = copied.read_bytes()

        self.assertIn(COMMAND_PATH, payload)
        before = self.tree()
        self.run_sync("diff")
        self.assertEqual(before, self.tree())
        self.run_sync()
        self.assertEqual(set(self.state()["files"]), set(payload))
        for relative, contents in payload.items():
            installed = self.target / relative
            self.assertFalse(installed.is_symlink(), relative)
            self.assertEqual(installed.read_bytes(), contents)
            self.assertEqual((self.repository / relative).read_bytes(), contents)
        before = self.tree()
        self.run_sync()
        self.assertEqual(before, self.tree())


if __name__ == "__main__":
    unittest.main()
