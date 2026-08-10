"""Engine.SaveCrash must not mask the failure it is reporting on.

Engine.game is declared as an annotation and only assigned near the end of Engine.Initialize
(engine.py:104). Anything that fails before that point reaches Log.OnCrash, which logs the real
exception and then calls Engine.SaveCrash. Touching Engine.game there raises AttributeError, and
that becomes the error the user sees, with the real cause buried further up the log.

Originally reported by @kmelkon in irefrixs/marvel-lcg#1 with a fix in #2, which was closed
without being merged.
"""
import unittest

import engine  # noqa: F401  establishes import order
from engine import Engine


class TestSaveCrashBeforeGameExists(unittest.TestCase):

    def setUp(self):
        self.had_game = hasattr(Engine, "game")
        self.saved_game = getattr(Engine, "game", None)
        self.saved_crashed = Engine.has_crashed
        self.saved_unit_test = Engine.in_unit_test

        if self.had_game:
            del Engine.game
        Engine.has_crashed = False
        Engine.in_unit_test = False  # otherwise SaveCrash calls exit(-1)

    def tearDown(self):
        if self.had_game:
            Engine.game = self.saved_game
        elif hasattr(Engine, "game"):
            del Engine.game
        Engine.has_crashed = self.saved_crashed
        Engine.in_unit_test = self.saved_unit_test

    def test_savecrash_survives_a_failure_before_game_exists(self):
        """A startup crash must surface itself, not an AttributeError from the handler."""
        self.assertFalse(hasattr(Engine, "game"), "precondition: Engine.game must be unset")

        Engine.SaveCrash()  # must not raise

        self.assertTrue(Engine.has_crashed, "the crash should still be recorded as handled")


if __name__ == "__main__":
    unittest.main()
