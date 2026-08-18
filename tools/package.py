#!/usr/bin/env python3
"""Release chores: bump the version, package the card definitions.

    python tools/package.py version    # bump BUILD in build.py and commit it
    python tools/package.py zip        # write cards-<version>.zip into the repo root
    python tools/package.py all        # both, in that order

This used to be `unit_test/test_task.py`, a `unittest.TestCase` whose two methods asserted nothing.
Its own comment admitted what it was: "Just use as a work, to help me increase the version number".
Being named `test_*` in a folder of tests meant `python -m unittest discover unit_test` ran it, so
merely running the suite rewrote `build.py`, made a `git commit`, and dropped a zip in the repo
root. That is not a hypothetical: it put four `Package version` commits on a working branch and
moved this fork from 0.5.9.201 to 205, and the version it bumps is stamped into every save file by
`Scene.GetSaveFileName`. Tests must be safe to run, and a test that commits to your branch is not.

So these are a script now, and the subcommand is required. Running this file with no arguments
prints help and changes nothing. `tools/run_tests.py` excluded it by name to work around the old
arrangement; out of the `test_` namespace, no discovery can reach it and nothing has to remember.
"""
import argparse
import os
import sys
import time
import zipfile

# Every folder holding card definitions. Adding a pack means adding it here.
FOLDERS = [
    './cards/pack/angel/',
    './cards/pack/angel/angel/',
    './cards/pack/ant/',
    './cards/pack/ant/ant_man/',
    './cards/pack/bkw/',
    './cards/pack/cap/',
    './cards/pack/core/',
    './cards/pack/cw/',
    './cards/pack/cw/hulkling/',
    './cards/pack/cw/tigra/',
    './cards/pack/cyclops/',
    './cards/pack/cyclops/cyclops/',
    './cards/pack/deadpool/',
    './cards/pack/deadpool/deadpool/',
    './cards/pack/drax/',
    './cards/pack/drax/drax/',
    './cards/pack/drs/',
    './cards/pack/falcon/',
    './cards/pack/gam/',
    './cards/pack/gambit/gambit/',
    './cards/pack/hlk/',
    './cards/pack/hlk/hulk/',
    './cards/pack/iceman/',
    './cards/pack/iceman/frostbite/',
    './cards/pack/ironheart/',
    './cards/pack/jubilee/',
    './cards/pack/jubilee/jubilee/',
    './cards/pack/msm/',
    './cards/pack/msm/ms_marvel/',
    './cards/pack/mts/',
    './cards/pack/mut_gen/',
    './cards/pack/ncrawler/',
    './cards/pack/ncrawler/nightcrawler/',
    './cards/pack/nebu/',
    './cards/pack/nebu/nebula/',
    './cards/pack/next_evol/',
    './cards/pack/nova/',
    './cards/pack/nova/nova/',
    './cards/pack/phoenix/',
    './cards/pack/phoenix/phoenix/',
    './cards/pack/psylocke/',
    './cards/pack/qsv/',
    './cards/pack/qsv/quicksilver/',
    './cards/pack/rogue/',
    './cards/pack/scw/',
    './cards/pack/scw/scarlet_witch/',
    './cards/pack/silk/',
    './cards/pack/sm/',
    './cards/pack/spdr/',
    './cards/pack/spiderham/',
    './cards/pack/stld/',
    './cards/pack/stld/star_lord/',
    './cards/pack/storm/',
    './cards/pack/thor/',
    './cards/pack/thor/thor/',
    './cards/pack/trors/',
    './cards/pack/valk/',
    './cards/pack/vision/',
    './cards/pack/vision/vision/',
    './cards/pack/vnm/',
    './cards/pack/vnm/venom/',
    './cards/pack/warm/',
    './cards/pack/warm/war_machine/',
    './cards/pack/winter/',
    './cards/pack/wolv/',
    './cards/pack/wsp/',
    './cards/pack/wsp/wasp/',
    './cards/pack/x23/',
    './cards/pack/x23/x_23/',
]

# Card contents decide the archive, not when it was built, so every entry gets the same stamp. Two
# builds of the same cards then produce byte-identical zips and can be compared.
UNIFORM_TIMESTAMP = "2022-01-01 00:00:00"

# Not card data: package metadata and campaign wiring that ships with the code instead.
SKIP_FILES = {'__init__.py', 'campaign.py'}


def ZipCards() -> str:
    """Write every card definition into cards-<version>.zip and return the path."""
    from build import Build

    output_zip = f"./cards-{Build.MAJOR}.{Build.MINOR}.{Build.PATCH}.{Build.BUILD}.zip"
    stamp = time.localtime(time.mktime(time.strptime(UNIFORM_TIMESTAMP, "%Y-%m-%d %H:%M:%S")))[:6]

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder in FOLDERS:
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if not os.path.isfile(file_path) or file in SKIP_FILES:
                    continue
                arcname = os.path.relpath(file_path, os.path.dirname(folder))
                zipf.write(file_path, arcname)
                zipf.getinfo(arcname).date_time = stamp

    print(f"Zipped files into {output_zip}")
    return output_zip


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    # Required, so that running the file by accident cannot commit anything.
    parser.add_argument("action", choices=["version", "zip", "all"],
                        help="version: bump and commit build.py; zip: package the cards")
    args = parser.parse_args()

    # Paths here are relative to the repository root, as they are everywhere else in this codebase.
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.getcwd())

    if args.action in ("version", "all"):
        from build_marvel import IncreaseVersion
        IncreaseVersion()
    if args.action in ("zip", "all"):
        ZipCards()
    return 0


if __name__ == "__main__":
    sys.exit(main())
