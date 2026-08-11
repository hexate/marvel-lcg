"""The game must not start with assertions disabled (tracker item J6).

619 `assert` statements across `core/`, `engine/`, `game/` and `cards/` carry the game rules, not
just internal invariants: legal targets, timing windows, resource costs. `python -O` deletes every
one of them, so the same build would walk straight past an illegal play instead of stopping.

Nothing in the repository passes `-O` today, so this is latent. It is one line in a packaging spec
away from being real, and the failure mode is a game that silently plays by no rules rather than
one that crashes, which is the worst way for it to go wrong.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import subprocess
import sys
import unittest

import engine  # noqa: F401  must precede any game import
from engine.engine import Engine


class TestAssertionsRequired(unittest.TestCase):

    def test_the_check_passes_when_assertions_are_on(self):
        Engine.CheckAssertionsEnabled(assertions_enabled=True)

    def test_the_check_refuses_when_assertions_are_off(self):
        with self.assertRaises(RuntimeError) as caught:
            Engine.CheckAssertionsEnabled(assertions_enabled=False)

        message = str(caught.exception)
        self.assertIn("-O", message, "the message has to name the flag that caused it")
        self.assertIn("assert", message)

    def test_it_actually_fires_under_python_dash_O(self):
        """The one that matters: `__debug__` has to be false in a real -O process.

        A unit test that passes the flag by hand proves the branch works, not that the branch is
        ever reached. This runs a real interpreter with -O.
        """
        result = subprocess.run(
            [sys.executable, "-O", "-c",
             "from engine.engine import Engine; Engine.CheckAssertionsEnabled()"],
            capture_output=True, text=True, timeout=120,
        )

        self.assertNotEqual(result.returncode, 0, "an -O process started without complaint")
        self.assertIn("-O", result.stderr)

    def test_it_stays_quiet_without_the_flag(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from engine.engine import Engine; Engine.CheckAssertionsEnabled()"],
            capture_output=True, text=True, timeout=120,
        )

        self.assertEqual(result.returncode, 0, result.stderr[-400:])


if __name__ == "__main__":
    unittest.main()
