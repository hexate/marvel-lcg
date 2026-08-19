# U9: new issue, test_task.py mutates the repo

Status: **POSTED** 2026-08-10 as [issue #6](https://github.com/irefrixs/marvel-lcg/issues/6).
Tracker item I8 (U9). Single topic, per his #1 request to split questions up.

**ANSWERED 2026-08-18, declined as working-as-intended.** Both cases are deliberate.
`test_IncreaseVersion` keeps its `test_` prefix because that is what makes VS Code draw a run
button next to it, which is how they trigger the bump by hand. `test_zip_cards` packages the
compiler bundle for the paid [Marvel LCG Scripts](https://irefrixs.itch.io/marvel-lcg-scripts)
build, the one that runs custom card scripts. Sunset, so no change upstream, and he explicitly
blessed changing it here: *"Since you have a fork, feel free to remove or rename them there if you
prefer."*

His second comment answers something nobody asked and is the more valuable half. Their suite runs
every existing save file through the engine and checks the CRC in the save JSON still matches, then
`check_is_pass` in `test_run.py` re-saves each passing file under the new version number, updating
both the version key and the filename, and once the run is green the old saves move to another
folder. They keep per-version corpora on purpose, so a change that breaks save compatibility can be
rolled back. That makes the version bump part of the ritual rather than a leak, and it is recorded
in section I of the tracker because it confirms the circularity problem from their side.

Fixed here on 2026-08-18 regardless: both chores moved to `tools/package.py` behind a required
subcommand.

Title: Running the unit test suite commits to git and bumps the version

---

Small one, and not urgent.

`unit_test/test_task.py` gets collected by any suite-wide run, and two of its cases are not tests:

- `test_IncreaseVersion` rewrites `BUILD` in `build.py`, then runs `git add` and `git commit`
  through `os.system` (`build_marvel.py:19-20`).
- `test_zip_cards` writes `cards-<version>.zip` into the repo root.

The file is upfront about it. The comment reads *"Just use as a work, to help me increase the
version number."* Obvious once you open it, easy to miss if you just run everything.

I ran the standalone tests three times while working on something else and came away with three
`Package version` commits on my branch and my fork sitting at `0.5.9.204` instead of `201`. The
commits were easy to drop. The version is the part that made me write this up rather than shrug:
`Scene.GetSaveFileName` stamps it into every save filename (`game/scene/scene.py:51`), and you
organise replays by version, so a stray bump means the build starts writing scenes claiming a
version you never released.

Two ways to fix it, whichever you prefer:

- move `IncreaseVersion` out of `unit_test/` into a script, since it is a release step rather than
  a test, or
- rename both methods so unittest stops collecting them, with a `__main__` entry to run them
  deliberately.

Either is a couple of lines and I am happy to send one if you want it.
