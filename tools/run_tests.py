#!/usr/bin/env python3
"""Run every unit test that is safe to run and does not need data we cannot ship.

    python tools/run_tests.py          # the whole safe suite
    python tools/run_tests.py -v       # with test names

One module under `unit_test/` is deliberately left out.

`test_all` replays recorded games. Those are player data, they are gitignored, and they are not in
the repository, so on a fresh clone it has nothing to replay. Run it yourself once you have put a
scene in `replays/min_test/`, and see docs/install_guide.md for which scenes can work.

Everything else is self-contained: no assets, no launch-debug.json, no corpus. Verified by running
this against a clean clone.
"""
import argparse
import os
import pathlib
import sys
import unittest

# `test_task` was the other entry here: it committed to git and wrote a zip into the repo root when
# the suite ran. Excluding it by name only protected this runner, so the chores moved to
# `tools/package.py` instead and now sit outside the `test_` namespace entirely. Nothing has to
# remember, and plain `unittest discover` is safe too.
EXCLUDED = {
    "test_all": "replays a corpus of recorded games, which is not in the repository",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true", help="print each test name")
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parent.parent
    # The engine resolves data with paths like "./cards", and `core.utility.func.ROOT_DIR` is the
    # working directory as it was at import time, so this has to happen before anything is loaded.
    os.chdir(root)
    sys.path.insert(0, str(root))

    found = sorted(path.stem for path in (root / "unit_test").glob("test_*.py"))
    for name in sorted(EXCLUDED):
        if name in found:
            print(f"skipping unit_test.{name}: {EXCLUDED[name]}")

    selected = [f"unit_test.{name}" for name in found if name not in EXCLUDED]
    if not selected:
        print("no test modules found", file=sys.stderr)
        return 1
    print(f"running {len(selected)} test modules\n")

    suite = unittest.defaultTestLoader.loadTestsFromNames(selected)
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
