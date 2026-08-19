#!/usr/bin/env bash
# Get a clean clone to the point where ./play.sh will work.
#
#   ./build.sh            build whatever is missing
#   ./build.sh --force    rebuild both halves from scratch
#   ./build.sh --watch    build, then keep recompiling the client as you edit it
#
# There are two halves and until now neither was scripted end to end: a Python virtualenv for the
# engine, and a TypeScript compile for the browser client. The compiled `.js` is gitignored, so a
# fresh clone renders nothing until the second one has run, and the instructions for it were a
# comment in `play.sh` telling you to install TypeScript globally. Tracked as C3.
#
# Nothing here is global. TypeScript is a devDependency of `public/js`, so the version is pinned
# with the project instead of being whatever `npm install -g typescript` happens to give you that
# month, which is what broke the build on 2026-08-10 when that became TypeScript 7.
#
# Note for anyone tempted to add a "clean" step here: do not delete `*.js` under `public/js`.
# `.gitignore` hides them all, but `lib/click-effect.js`, `lib/notifications.js`, `lib/sortable.js`
# and `lib/vanilla-tilt.js` are vendored third-party sources that were force-added past that rule.
# They look like build output and are not. `--force` deliberately only removes `.venv` and
# `node_modules`, both of which are reproducible.
set -euo pipefail
cd "$(dirname "$0")"

FORCE=0
WATCH=0
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        --watch) WATCH=1 ;;
        -h|--help) sed -n '2,6p' "$0" | sed -e 's/^#//' -e 's/^ //'; exit 0 ;;
        *) echo "build.sh: unknown option '$arg'" >&2; exit 2 ;;
    esac
done

need() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "build.sh: '$1' is not on PATH. $2" >&2
        exit 1
    }
}

# ---------------------------------------------------------------- engine
need python3 "Install Python 3.11 or newer."

if [ "$FORCE" = 1 ] && [ -d .venv ]; then
    echo "==> Removing .venv (--force)"
    rm -rf .venv
fi

if [ ! -x .venv/bin/python ]; then
    echo "==> Creating .venv"
    python3 -m venv .venv
    ./.venv/bin/pip -q install --upgrade pip
    ./.venv/bin/pip -q install -r requirements.txt
else
    echo "==> .venv present, skipping (use --force to rebuild)"
fi

# ---------------------------------------------------------------- client
need npm "Install Node.js, which ships npm. The client is TypeScript and has to be compiled."

if [ "$FORCE" = 1 ] && [ -d public/js/node_modules ]; then
    echo "==> Removing public/js/node_modules (--force)"
    rm -rf public/js/node_modules
fi

if [ ! -d public/js/node_modules ]; then
    echo "==> Installing the client's build dependencies"
    ( cd public/js && npm install --silent --no-fund --no-audit )
else
    echo "==> public/js/node_modules present, skipping (use --force to rebuild)"
fi

if [ "$WATCH" = 1 ]; then
    echo "==> Compiling the client and watching for changes (Ctrl-C to stop)"
    exec sh -c 'cd public/js && npm run --silent watch'
fi

echo "==> Compiling the client"
( cd public/js && npm run --silent build )

count=$(find public/js -name '*.js' -not -path '*/node_modules/*' 2>/dev/null | wc -l | tr -d ' ')
echo "==> Done. $count compiled files. Start the game with ./play.sh"
