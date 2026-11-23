SHELL_SCRIPTS := init.sh $(addprefix .local/bin/,ntfy ntfy-codex ntfy-run passphrase \
	restore-git-signing-keys update-fedora update-mac)

.PHONY: check lint format typecheck test

check: lint typecheck test

lint:
	uv run ruff check
	uv run ruff format --check
	shellcheck $(SHELL_SCRIPTS)

format:
	uv run ruff check --fix
	uv run ruff format

typecheck:
	uv run pyrefly check

test:
	uv run pytest
