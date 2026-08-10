"""Tests for the retry cap in PlayerAction.ChooseEffects.

Controller.ChoiceOne returns (None, True) when it cannot use the input it was given, and
ChooseEffects loops on that flag. With a human client the player sees the error and retries, so
the loop is correct. With any automated input source the same retry becomes an unkillable spin at
roughly 5,000 iterations a second, with nothing logged, which is indistinguishable from a deadlock
from outside.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes
first.
"""
import unittest
from unittest import mock

import engine  # noqa: F401  must precede any game import
from game.player.action.player_action import PlayerAction, MAX_INPUT_RETRIES


class _World:
    pass


class _Player:
    world = _World()


class _AlwaysRejects:
    """A PlayerAction whose controller never accepts the input, like a broken device."""

    def __init__(self):
        self.calls = 0

    def GetPlayer(self):
        return _Player()

    def ChoiceAndSpellEffect(self, effects, message, priority, forced):
        self.calls += 1
        return None, True  # the "cheat" flag, meaning try again


class _AcceptsImmediately(_AlwaysRejects):
    def ChoiceAndSpellEffect(self, effects, message, priority, forced):
        self.calls += 1
        return "an-effect", False


class TestInputRetryCap(unittest.TestCase):

    def setUp(self):
        self.filter_patch = mock.patch(
            "game.event.manager.EventManager.FilterAvailableEffects",
            staticmethod(lambda *a, **k: ["one-effect"]),
        )
        self.text_patch = mock.patch(
            "game.message.Message.PlayerOnEvent_Text",
            staticmethod(lambda *a, **k: None),
        )
        self.filter_patch.start()
        self.text_patch.start()
        self.addCleanup(self.filter_patch.stop)
        self.addCleanup(self.text_patch.stop)

    def test_a_rejecting_controller_gives_up_instead_of_spinning(self):
        actor = _AlwaysRejects()
        with self.assertRaises(AssertionError) as caught:
            PlayerAction.ChooseEffects(actor, ["e"], object())
        self.assertLessEqual(actor.calls, MAX_INPUT_RETRIES.value + 1)
        self.assertIn("retr", str(caught.exception).lower())

    def test_a_working_controller_is_untouched(self):
        actor = _AcceptsImmediately()
        result = PlayerAction.ChooseEffects(actor, ["e"], object())
        self.assertEqual(result, "an-effect")
        self.assertEqual(actor.calls, 1)


if __name__ == "__main__":
    unittest.main()
