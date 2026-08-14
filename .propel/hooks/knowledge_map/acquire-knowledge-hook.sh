#!/usr/bin/env bash
# acquire-knowledge-hook.sh
# Propel-IQ Knowledge Map — Post-write hook (bash wrapper)
# Use for: Copilot (.github/hooks/) and Windsurf on macOS/Linux

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_HOOK="$SCRIPT_DIR/acquire-knowledge-hook.py"

if [ ! -f "$PYTHON_HOOK" ]; then
    echo "[acquire-knowledge-hook] ERROR: Python hook not found at $PYTHON_HOOK" >&2
    exit 0
fi

python3 "$PYTHON_HOOK" || exit 0
