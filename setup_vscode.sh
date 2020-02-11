#!/usr/bin/env bash

set -euo pipefail

CONFDIR="$(pwd)/.config/Code/User"
EXTENSIONS="$CONFDIR/extensions.txt"
TMPFILE=$(mktemp)
MACOS_CONFDIR="$HOME/Library/Application Support/Code/User"
SETTINGS_FILE=settings.json

( code --list-extensions ; cat "$EXTENSIONS" ) | sort -fu > "$TMPFILE"
mv "$TMPFILE" "$EXTENSIONS"

xargs -n 1 code --install-extension < "$EXTENSIONS"

if [[ "$(uname)" == "Darwin" ]]; then
  mkdir -p "$MACOS_CONFDIR"
  ln -fs "$CONFDIR/$SETTINGS_FILE" "$MACOS_CONFDIR/$SETTINGS_FILE"
fi
