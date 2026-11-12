#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Clone zgenom first so a partial apply never leaves .zshrc without it.
[[ -d ~/.zgenom ]] || git clone https://github.com/jandamm/zgenom.git ~/.zgenom

python3 "$SCRIPT_DIR/.local/bin/configs" apply
