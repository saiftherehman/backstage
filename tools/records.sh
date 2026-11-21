#!/bin/bash
# Opens or encrypts Backstage session records ([sessions] encrypt = true).
#
#   tools/records.sh open sessions/2026-11-20_1430_assistant_weekly-sync.backstage
#   tools/records.sh seal sessions/2026-11-20_1430_assistant_weekly-sync
#
# "open" decrypts into a private folder in memory (cleared at logout) and
# opens it in Files. The encrypted file is left as it is.
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
# Paths are made absolute first, since the helper code runs from helper/.
args=()
for arg in "$@"; do
    if [ -e "$arg" ]; then args+=("$(realpath "$arg")"); else args+=("$arg"); fi
done
cd "$PROJECT/helper"
exec "$PROJECT/.venv/bin/python" -m backstage.vault "${args[@]}"
