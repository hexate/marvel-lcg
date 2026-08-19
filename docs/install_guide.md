# Install Guide

## 1. Install python

https://www.python.org/ftp/python/

We've tested in py 3.10.5 and py 3.14.2

## 2. Install requirements

```cmd
pip install -r requirements.txt
```

## 3. Download nodejs

https://nodejs.org/en/download

## 4. Build

One command, from the project root:

```sh
./build.sh
```

It creates the Python virtualenv, installs the engine's dependencies, installs the client's build
dependencies and compiles the TypeScript. It is idempotent, so running it again only recompiles.

TypeScript is a dependency of the project rather than something you install globally, so the version
is pinned here and does not drift. `npm install -g typescript` is no longer needed and is worth
avoiding: it installs whichever major is current, which is how the build broke on 2026-08-10.

```sh
./build.sh --watch    # build, then keep recompiling the client as you edit it
./build.sh --force    # rebuild the virtualenv and the client dependencies from scratch
```

`public/js/watch.bat` still exists for Windows and still works. `./build.sh --watch` does the same
thing on every platform.

## 5. Nothing to do here

Step 4 covers what this used to.

## 6. Download assets

You need to download the game to gain its `assets` folder from [itch.io](https://irefrixs.itch.io/marvel-lcg) and put it in the root folder of this project

## 7. Start the game

```
py main.py
```

## 8. Run the tests (optional)

The test suite replays recorded games, and recorded games are player data, so none ship with the
source. Two things are missing from a fresh clone:

```
cp launch.json launch-debug.json
```

`unit_test/test_all.py` reads `launch-debug.json`, which is a developer-local config and is not
committed. A copy of `launch.json` is enough to run the tests.

Then put at least one recorded game in `replays/min_test/`. Play a game and it saves into
`replays/` on its own, then copy one across. A scene only works as a test case if the game asks
nothing further after its last recorded input, so record until the game ends. A save made in the
middle of a turn will replay to that point and then sit waiting for the next decision, which in a
test means it fails with `EOFError` from `input()`.

Most of the tests need none of that. To run everything that is self-contained:

```
py tools/run_tests.py
```

That works on a fresh clone with no assets, no `launch-debug.json` and no recorded games. Once you
have put a scene in `replays/min_test/`, the replay suite runs too:

```
py -m unittest unit_test.test_all.TestMain.test_min
```

`py -m unittest discover unit_test` is safe to run as well. It used to execute
`unit_test/test_task.py`, which was not a test: it bumped the version in `build.py`, made a git
commit, and wrote a zip into the repository root. Those chores are `tools/package.py` now, which
takes an explicit subcommand, so no discovery can reach them. Discovery still picks up `test_all`,
which needs the recorded games described above; `tools/run_tests.py` skips that one for you.
