#!/usr/bin/env bash
# ingest.sh - cross-platform launcher for the ingest-prompt binary.
#
# Input options (pick one):
#   1. Pass a file path as the first argument:  ./ingest.sh /path/to/input.txt
#   2. Pipe input via stdin:                    cat input.txt | ./ingest.sh
#
# Output:
#   stdout: prepared text (header line preserved, body replaced)
#   stderr: error message on failure
#   exit:   0 on success, 1 on processing failure, 2 on usage error

set -e
dir="$(cd "$(dirname "$0")" && pwd)"

case "$(uname -s)" in
    Darwin*)              exe="$dir/ingest-prompt-osx"   ;;
    Linux*)               exe="$dir/ingest-prompt-linux" ;;
    MINGW*|CYGWIN*|MSYS*) exe="$dir/ingest-prompt.exe"   ;;
    *)                    exe="$dir/ingest-prompt.exe"   ;;
esac

if [ ! -x "$exe" ] && [ ! -f "$exe" ]; then
    echo "ingest-prompt: binary not found for this platform: $exe" >&2
    exit 1
fi

set +e
if [ -n "$1" ]; then
    "$exe" "$1"
else
    "$exe"
fi
exit $?
