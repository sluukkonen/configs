import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync_configs", REPOSITORY / "sync_configs.py")
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
        shutil.copyfile(REPOSITORY / "sync_configs.py", self.repository / "sync_configs.py")

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

    def run_sync(self, command="apply", expected=0):
        result = subprocess.run(
            [sys.executable, str(self.repository / "sync_configs.py"), command,
             "--target", str(self.target)],
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
            "create_symlink.py",
        ):
            self.source(path, "# tooling\n")
        self.git("add", "--", "sync_configs.py")
        (self.repository / "create_symlink.py").unlink()
        self.source(".zshrc")
        (self.repository / ".vimrc").write_text("untracked\n")
        self.run_sync()
        self.assertEqual(set(self.state()["files"]), {".zshrc"})

    def test_new_configuration_paths_are_selected_automatically(self):
        paths = (".newrc", ".config/new-tool/config", "bin/new-command")
        for relative in paths:
            self.source(relative, "new config\n", 0o755 if relative.startswith("bin/") else 0o644)
        self.run_sync()
        self.assertEqual(set(self.state()["files"]), set(paths))
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
        self.assertEqual(set(self.state()["files"]), expected)
        for relative in expected:
            self.assertEqual((self.target / relative).read_text(), "original\n")

    def test_newly_excluded_files_and_their_baselines_are_preserved(self):
        self.source("support/new-file")
        self.run_sync()
        installed = self.target / "support/new-file"
        installed.write_text("local edit\n")
        installer = self.repository / "sync_configs.py"
        installer.write_text(installer.read_text().replace(
            "REPOSITORY_ONLY = {", 'REPOSITORY_ONLY = {"support",', 1))
        before = self.tree()
        for command in ("diff", "apply"):
            output = self.run_sync(command)
            self.assertIn("NO LONGER SELECTED (left installed) support/new-file", output)
            self.assertEqual(before, self.tree())

    def test_configuration_cannot_target_installer_state(self):
        for relative in (sync.STATE_PATH, ".local/state/configs/other", ".local/state/configs", ".local/state", ".local"):
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
        self.assertEqual(set(self.state()["files"]), set(paths))
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
        self.assertEqual(set(self.state()["files"]), {skill, metadata})
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
        self.assertEqual(set(self.state()["files"]), {relative})

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

    def test_untracked_required_helper_prevents_partial_migration(self):
        self.source(".local/bin/update-config", "#!/bin/bash\n", 0o755)
        self.source()
        helper = self.repository / ".local/bin/configs-repo"
        helper.write_text("untracked helper\n")
        before = self.tree()
        self.assertIn("git add .local/bin/configs-repo", self.run_sync(expected=1))
        self.assertEqual(before, self.tree())


class UpdateCommandTests(InstallerFixture):
    def install_commands(self):
        for name in ("configs-repo", "update-config", "update-mac"):
            self.source(".local/bin/" + name, (REPOSITORY / ".local/bin" / name).read_text(), 0o755)
        self.source("init.sh", "#!/bin/bash\nset -eu\nprintf 'init:%s\\n' \"$PWD\" >> \"$CALL_LOG\"\n", 0o755)
        self.run_sync()
        self.commands = self.root / "commands"
        self.commands.mkdir()
        self.log = self.root / "calls"
        for name in ("git", "zsh", "brew", "softwareupdate"):
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
        for name in ("update-config", "update-mac"):
            result = subprocess.run(["bash", str(self.target / ".local/bin" / name)],
                                    cwd=self.root, env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.log.read_text()
        self.assertIn("git:{}:pull".format(self.repository), calls)
        self.assertIn("init:{}".format(self.repository), calls)
        self.assertIn("brew:{}:bundle --upgrade".format(self.repository), calls)

    def test_missing_or_invalid_locator_stops_before_external_commands(self):
        self.install_commands()
        state_path = self.target / sync.STATE_PATH
        for contents in (None, "[]", '{"version":1,"repository":"/absent"}'):
            if contents is None:
                state_path.unlink()
            else:
                state_path.write_text(contents)
            for name in ("update-config", "update-mac"):
                result = subprocess.run(["bash", str(self.target / ".local/bin" / name)],
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

        self.assertIn(".local/bin/configs-repo", payload)
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
