#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/sync_configs.py" apply

[[ -d ~/.zgen ]] || git clone https://github.com/tarjoilija/zgen ~/.zgen
