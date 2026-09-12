# Dotfiles

This repository installs regular configuration files into your home directory.
The repository is the source of truth: edits become active after you apply them.
Every selected file keeps its repository-relative path under your home directory;
for example, `.codex/skills/commit/SKILL.md` installs to
`~/.codex/skills/commit/SKILL.md`. There are no application-specific path mappings
or cleanup rules.
The installer requires Python 3.8 or newer and Git, without pip packages. It
targets Linux and macOS. Individual configuration files and helper commands may
require their own applications.

## Install and update

From a checkout, preview and apply configuration changes:

```sh
python3 .local/bin/configs diff
python3 .local/bin/configs apply
```

On a new machine, install Python 3.8+ and Git, clone this repository, then run
`./init.sh`. It applies the configuration and installs zgen if it is missing. It can
also be invoked by absolute path from another working directory. It stops if
configuration installation fails.

After installation, start a new login shell to pick up `~/.local/bin` on PATH,
or run `export PATH="$HOME/.local/bin:$PATH"` in your current shell. Then use:

```sh
configs diff
configs apply
configs update
```

`configs update` runs `git pull --ff-only` in the saved checkout, then applies
configuration using the newly pulled installer. Divergent history or another
pull failure stops the update before application; resolve the Git issue in the
checkout and retry. Uncommitted tracked edits remain eligible for application if
Git can pull successfully. If application fails after pulling, the repository
stays updated; resolve the reported error and rerun `configs apply`.
Routine updates do not run bootstrap or install/update zgen or its plugins.

`configs repo` prints the checkout path. `update-mac` uses it to run Homebrew and
macOS updates from that directory. Bootstrap and update commands require the
applications they invoke; they do not provision Python, Git, or Homebrew.

To edit configuration, change its file in this repository, run `diff`, then
`apply`. The installer reads working-copy contents, including uncommitted edits
to tracked files. New files become eligible automatically after `git add`, whether
they are dotfiles, configuration directories, or ordinary paths such as
`bin/new-command`.

`REPOSITORY_ONLY` in `.local/bin/configs` excludes repository support files and
directories. Entries match only the first path component: `README.md` and
`tests/` are excluded, while `.codex/AGENTS.md` and documentation inside skill
directories remain eligible. Add an exclusion when introducing new repository
tooling; placing support files under `tests/` or `docs/` needs no further entry.
Untracked files and Git's internal metadata are never selected. The installer's
own state directory is reserved; configurations targeting it or its ancestors
are rejected before installation.

Stage new files and deletions before applying working-copy changes. The installer
requires `.local/bin/configs` to be tracked and rejects missing tracked sources.

`diff` returns zero when the proposed changes are conflict-free, even if changes
are pending. Commands return nonzero for conflicts or errors. Text diffs
can contain the contents of your configuration files. Binary changes are
reported without printing their contents.

`configs diff` colors additions green, deletions red, and hunk headers cyan when
stdout is a terminal. Redirected output stays plain. Use `--color always` to
retain color in a pipe (for example, `configs diff --color always | less -R`),
or `--color never` to disable it. Automatic color respects a nonempty `NO_COLOR`
and `TERM=dumb`; an explicit `--color always` overrides those settings.

## Conflicts and permissions

Installation records each managed file's last installed SHA-256 hash and mode in
`~/.local/state/configs/state.json`. A subsequent apply updates files that still
match that baseline. Identical unmanaged files are adopted. Locally edited or
deleted files and differing unmanaged files are conflicts; the entire preflight
must succeed before any installed file is changed.

Resolve conflicts manually:

- To keep a local content edit, incorporate it into the corresponding repository
  file, review the diff in Git, then apply again.
- To discard a local edit, save anything you need and restore the file to its
  last installed contents and permissions. For an unmanaged conflict, move the
  existing file aside before applying.
- For a locally deleted file, restore it with the repository contents and the
  permissions recorded in the manifest before applying.
- For a permission conflict, review the change and restore the recorded mode
  before applying. There is no force-overwrite or automatic merge command.

New files use the repository file's permission bits. Existing regular files
keep their read/write restrictions, or become more restrictive if the source
does. Executable bits follow the repository only for user classes that already
have read or execute access to the destination. Newly created directories are
private (`0700`), and the manifest is written with mode `0600`. Existing parent
directory permissions are not changed. Special file types and special permission
bits are unsupported.

Files removed from the repository or newly excluded are reported as no longer
selected and left installed by `apply` and `update`. To clean them up explicitly:

```sh
configs prune --dry-run
configs prune
```

Prune deletes obsolete regular files only when their contents and permissions
still match the recorded baseline. It forgets state entries for successfully
deleted or already-missing files, so they stop appearing in subsequent reports.
Directories and unmanaged files are left untouched; empty directories are not
removed. Deletions are permanent, without a backup or confirmation prompt.

Locally changed obsolete files, symlinks, and unsafe paths are preserved and
reported as conflicts. Safe candidates are still pruned, but the command returns
nonzero when anything needs attention. Filesystem aliases of active configurations
are also preserved, including case-only renames on case-insensitive filesystems
and hard links. Their obsolete state entries remain; do not move or delete an
alias to resolve the report, since it may refer to the active file itself.
For locally edited obsolete files, resolve conflicts manually: restore the
recorded file to allow deletion, or move it aside and rerun prune to forget it.
Active configuration conflicts do not prevent obsolete-file cleanup.

`--dry-run` reports proposed deletions, forgotten entries, and conflicts without
changing files or state. It is supported only for `prune`; `--target` selects an
alternate installation as with the other commands. Prune saves progress after
each removal and stops on deletion or state-write errors. If a file was deleted
before saving its state failed, rerunning prune forgets the missing file.

Preserved obsolete files retain their baselines, protecting local changes if
their paths are reintroduced. After pruning, a reintroduced path is treated as
a new installation. No automatic pruning, templating, imports, or background
sync is provided.

## Symlink migration and recovery

An existing file symlink pointing directly to its corresponding source in this
checkout is replaced atomically with a regular file. Unrelated or broken links
are conflicts. Symlinked parent directories inside the home directory are
rejected: convert those directories to real directories or relocate their
contents manually before using this installer.

The manifest also records the checkout location, which installed `configs`
commands use regardless of the current working directory. Invoking the script
directly in a checkout uses that checkout instead. If you move the checkout,
run its installer directly:

```sh
python3 /new/path/to/configs/.local/bin/configs apply
```

This refreshes the saved location after a successful preflight. Before the first
migration, links that still point to an old checkout location must be repaired
manually. Keep the manifest: deleting it loses the baseline needed to distinguish
local changes from repository changes. If the manifest is corrupt, restore a
known-good copy and rerun; the installer will not overwrite corrupt state.

Writes are atomic per file, not transactional across the whole installation.
An I/O failure may leave some files updated; their baselines are saved as work
succeeds. Rerunning can adopt a file that was written just before a manifest
write failed. Conflicting edits made after a partial failure still require manual
resolution. Concurrent installer runs against the same home directory are
rejected; other programs are not locked out from editing their configuration.

## Test

```sh
python3 -m unittest discover -s tests -v
bash -n init.sh .local/bin/update-mac
shellcheck init.sh .local/bin/update-mac
```

Tests use temporary Git repositories and home directories, and stub external
update commands. Git update tests use local remotes without network access.
To inspect an isolated installation manually, create a temporary
directory and pass it with `--target` (for example, `configs diff --target /tmp/configs-home`). The target
must already exist and must not be inside this repository. A preview never
creates installation state or modifies the target.
