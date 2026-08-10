"""When may a player decline a prompt (tracker item J8)?

`ChoiceOne` treats input id 0 as "no thanks". On a forced prompt it asserted that there was exactly
one option and that it needed no targets, which is a real rule: a forced prompt you can walk away
from is not forced. The problem was the assert. Clicking Cancel on the "Spider-Man End Phase"
prompt, which is forced and offers several options, is a legal-looking UI action that crashed the
engine, reproduced in a browser game on 2026-08-09.

The engine takes that id from a client over HTTP, so a client that offers a button the engine will
not honour has to produce a refusal, not a stack trace. `ChoiceOne` already has a way to say "I
cannot use this input": it returns `(None, True)` and the caller asks again.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import unittest

import engine  # noqa: F401  must precede any game import
from engine.controller.controller import Controller


class _Descriptor:
    """Stands in for game.render.descriptor.effect.EffectDescriptor."""

    def __init__(self, min_targets: int = 0, max_targets: int = 0):
        self.target_num_range = [min_targets, max_targets]


class TestDeclineContract(unittest.TestCase):

    def test_an_optional_prompt_can_always_be_declined(self):
        self.assertTrue(Controller.CanDecline(False, [_Descriptor(), _Descriptor()]))
        self.assertTrue(Controller.CanDecline(False, [_Descriptor(1, 1)]))

    def test_a_forced_prompt_with_one_targetless_option_can_be_declined(self):
        """Declining is how you resolve a forced prompt whose only option asks for nothing."""
        self.assertTrue(Controller.CanDecline(True, [_Descriptor()]))

    def test_a_forced_prompt_with_several_options_cannot_be_declined(self):
        """J8. This is the End Phase prompt, and it used to raise instead of refusing."""
        self.assertFalse(Controller.CanDecline(True, [_Descriptor(), _Descriptor()]))

    def test_a_forced_prompt_needing_a_target_cannot_be_declined(self):
        self.assertFalse(Controller.CanDecline(True, [_Descriptor(1, 1)]))

    def test_a_forced_prompt_with_no_options_cannot_be_declined(self):
        """Nothing to resolve and nothing to decline. Refuse rather than index into an empty list."""
        self.assertFalse(Controller.CanDecline(True, []))


if __name__ == "__main__":
    unittest.main()
