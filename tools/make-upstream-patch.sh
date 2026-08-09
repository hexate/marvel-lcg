#!/usr/bin/env bash
# Package one topic branch as an upstream-ready patch.
#
# irefrixs closes PRs and re-applies the content as his own commits (see PR #2, which was
# closed with mergedAt=null while its content shipped as ccb25a3). So the useful deliverable
# is a clean diff he can read and apply, not a merge request.
#
#   ./tools/make-upstream-patch.sh pr/test-harness
#
# Writes to out/patches/ :
#   <branch>.patch    git-am-able mailbox patch, full history
#   <branch>.diff     plain unified diff, paste-able into an issue
#
# Each pr/* branch must be based directly on upstream/master so its diff stands alone.
set -euo pipefail

BRANCH="${1:?usage: $0 <branch>}"
BASE="${2:-upstream/master}"
OUT="out/patches"

git rev-parse --verify --quiet "$BRANCH" >/dev/null || { echo "no such branch: $BRANCH" >&2; exit 1; }
git fetch -q upstream 2>/dev/null || true

if ! git merge-base --is-ancestor "$BASE" "$BRANCH"; then
    echo "warning: $BRANCH is not descended from $BASE — rebase it before sending" >&2
fi

mkdir -p "$OUT"
SAFE="${BRANCH//\//-}"

git format-patch "$BASE".."$BRANCH" --stdout > "$OUT/$SAFE.patch"
git diff "$BASE".."$BRANCH" > "$OUT/$SAFE.diff"

echo "$BRANCH  ($(git rev-list --count "$BASE".."$BRANCH") commit(s) on $BASE)"
git diff --stat "$BASE".."$BRANCH" | sed 's/^/  /'
echo
echo "  $OUT/$SAFE.patch   (git am)"
echo "  $OUT/$SAFE.diff    (paste into the issue)"
