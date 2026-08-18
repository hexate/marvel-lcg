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

## 4. Install typescript

```
npm install -g typescript
```

## 5. Compile ts to js

On Windows, double click to run "\public\js\watch.bat"

On macOS and Linux, run the same command directly:

```sh
cd public/js
tsc --watch
```

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
