"""Tests for FaceEffect.Find's `when` filter.

`game/` cannot be imported on its own because of a circular import between game.object and
game.player, so `import engine` has to come first to establish the order.
"""
import types
import unittest

import engine  # noqa: F401  must precede any game import
from game.card.face.effect.face_effect import FaceEffect
from game.message import Message


class _RaisingAbility:
    """Stands in for an Ability whose `when` lookup fails unexpectedly."""

    @property
    def when(self):
        raise RuntimeError("simulated failure reading ability.when")


class _UnionAbility:
    """Stands in for card 43007, whose `when` is a union of two message types."""

    when = Message.WhenUnitWouldAttack | Message.WhenUnitWouldThwart


class _Effect:
    def __init__(self, ability):
        self.ability = ability


class TestEffectFilter(unittest.TestCase):

    def test_unexpected_error_is_not_swallowed(self):
        """An error other than TypeError must surface, not silently drop the ability.

        The `when` check is wrapped to tolerate abilities whose `when` is a union type (card
        43007). A bare `except` also absorbs genuine failures and `continue`s, which removes the
        effect from the result with no log and no crash, so a card silently stops working.
        """
        face_effect = FaceEffect(None)
        face_effect.global_effects.append(_Effect(_RaisingAbility()))

        with self.assertRaises(RuntimeError):
            face_effect.Find(when=Message.WhenUnitWouldAttack)

    def test_union_when_is_skipped_without_raising(self):
        """Card 43007's union `when` must still be tolerated.

        AbilityFactory.WhenUnitWouldAttackOrThwart builds an Ability whose `when` is
        Message.WhenUnitWouldAttack|Message.WhenUnitWouldThwart. issubclass() raises TypeError on
        a union, so the effect is skipped rather than matched. This guards the original
        workaround against the except clause being narrowed further.
        """
        union_ability = _UnionAbility()
        self.assertIsInstance(union_ability.when, types.UnionType)

        face_effect = FaceEffect(None)
        face_effect.global_effects.append(_Effect(union_ability))

        self.assertEqual(face_effect.Find(when=Message.WhenUnitWouldAttack), [])


if __name__ == "__main__":
    unittest.main()
