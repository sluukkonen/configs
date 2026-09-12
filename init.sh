#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/.local/bin/configs" apply

[[ -d ~/.zgen ]] || git clone https://github.com/tarjoilija/zgen ~/.zgen
