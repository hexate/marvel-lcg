# U9: new issue, test_task.py mutates the repo

Status: DRAFT. Tracker item I8. Single topic, per his #1 request to split questions up.

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
