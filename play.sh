#!/usr/bin/env bash
# Start the game locally with the fork's fixes applied.
#
#   ./play.sh              normal play
#   ./play.sh --record     also save the replay when a game finishes
#
# Then open http://127.0.0.1:2345
#
# First run downloads card art from the CDN and is slow; the browser may look frozen while it
# does. Images cache into ./assets/pics/ and later runs are fast. Ctrl-C to stop.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "No .venv found. Creating one." >&2
    python3 -m venv .venv
    ./.venv/bin/pip -q install -r requirements.txt
fi

if [ "$(find public/js -name '*.js' 2>/dev/null | wc -l | tr -d ' ')" -lt 10 ]; then
    echo "TypeScript is not compiled. Run this first:" >&2
    echo "    cd public/js && npx -p typescript tsc" >&2
    echo "(tsconfig.json still declares moduleResolution node10, which TypeScript 7 rejects;" >&2
    echo " it emits anyway, or pin typescript@5.6. Tracked as A1.)" >&2
    exit 1
fi

ARGS=()
if [ "${1:-}" = "--record" ]; then
    # Off by default upstream, so a finished game is not saved unless asked.
    ARGS+=(-auto_save_after_game_over)
    echo "Recording on: a finished game will be written to ./replays/"
fi

echo "Serving on http://127.0.0.1:2345"
# ${ARGS[@]+...} guards the empty-array case: macOS ships bash 3.2, where "${ARGS[@]}" on an
# empty array under `set -u` is an unbound variable error.
exec ./.venv/bin/python main.py ${ARGS[@]+"${ARGS[@]}"}
