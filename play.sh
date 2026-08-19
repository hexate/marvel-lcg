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

# Both halves are `build.sh`'s job now. It is idempotent, so the common case where everything is
# already built costs one `find` and two directory checks.
#
# The client count excludes `node_modules`, which is full of `.js` and would otherwise make an
# uncompiled clone look compiled.
if [ ! -x .venv/bin/python ] \
   || [ "$(find public/js -name '*.js' -not -path '*/node_modules/*' 2>/dev/null | wc -l | tr -d ' ')" -lt 10 ]; then
    echo "Something is not built yet. Running ./build.sh first." >&2
    ./build.sh
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
