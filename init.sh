#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/.local/bin/configs" apply

[[ -d ~/.zgenom ]] || git clone https://github.com/jandamm/zgenom.git ~/.zgenom
