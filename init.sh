#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Clone zgenom first so a partial apply never leaves .zshrc without it.
[[ -d ~/.zgenom ]] || git clone https://github.com/jandamm/zgenom.git ~/.zgenom

# Let sudo use Touch ID. Append rather than overwrite to keep manual changes.
if [[ "$(uname)" == Darwin ]] && ! grep -qs pam_tid.so /etc/pam.d/sudo_local; then
  echo "auth       sufficient     pam_tid.so" | sudo tee -a /etc/pam.d/sudo_local > /dev/null
fi

python3 "$SCRIPT_DIR/.local/bin/configs" apply
