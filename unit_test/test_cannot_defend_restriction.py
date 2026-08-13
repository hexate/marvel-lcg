"""Which player gets banned from triggering a defense ability, and which cards can load at all.

`UnitCannotDefend` builds a second ability when `cannot_trigger_defense_ability` is set, and has to
decide who the ban applies to. The old code read:

    if cannot_trigger_defense_ability == True and which_unit == "Attached":
        check_player = "AttachedPlayer"
    elif which_unit:
        assert isinstance(which_unit, CardFinder)
        check_player = PlayerFinder(which_unit)
    else:
        check_player = "AnyPlayer"

"Attached" is not a CardType. It is commented out of `CARD_TYPE_PREFIX`, so the first branch could
never be taken and the attached-identity literal is spelled "AttachedIdentity", which is what the
sibling factories match on. Every caller therefore reached the `elif`, and three of the four real
call sites pass something that is not a `CardFinder`, so the assert fired at import time and the
card could not load.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import unittest

import engine  # noqa: F401  must precede any game import
from game.ability.factory import AbilityFactory
from game.card.card_finder.finder import CardFinder
from game.card.face.base.unit import Unit2
from game.card.face.card_type.ally import Ally
from game.player.player_finder import PlayerFinder


class TestCardsThatCouldNotLoad(unittest.TestCase):
    """The real argument shapes, taken from the call sites rather than invented."""

    REAL_CALL_SITES = [
        ("Tracking Display", "cards/pack/sm/osborn_tech/27152.py", Unit2, "AttachedVillain"),
        ("Rollin', Rollin'", "cards/pack/nova/armadillo/28030.py", "Character", "AttachedEnemy"),
        ("Trickster Magic", "cards/pack/tt/trickster_magic/55061.py", Ally, "Villain"),
    ]

    def test_a_non_finder_restriction_builds_instead_of_asserting(self):
        """These three are the cards the assert made unloadable."""
        for name, path, which_unit, attacker in self.REAL_CALL_SITES:
            with self.subTest(card=name):
                self.assertNotIsInstance(
                    which_unit, CardFinder,
                    f"{path} would have satisfied the old assert, so it is not a witness")

                abilities = AbilityFactory.UnitCannotDefend(
                    which_unit, attacker, cannot_trigger_defense_ability=True)

                self.assertEqual(len(abilities), 2,
                                 f"{name} should build the cannot-defend ability and the ban")


class TestTheCardsThemselvesImport(unittest.TestCase):
    """The end-user symptom was not a wrong ban, it was a card that would not load at all."""

    CARDS = {
        "27152": "cards.pack.sm.osborn_tech.27152",           # Tracking Display
        "28030": "cards.pack.nova.armadillo.28030",           # Rollin', Rollin'
        "55061": "cards.pack.tt.trickster_magic.55061",       # Puppet Master
        "50156": "cards.pack.aos.supersonic.50156",           # Supersonic, the CardFinder caller
    }

    def test_every_caller_builds_its_abilities(self):
        import importlib

        for card_id, module in self.CARDS.items():
            with self.subTest(card=card_id):
                abilities = importlib.import_module(module).GetAbilities()

                self.assertTrue(abilities, f"{card_id} built no abilities")


class _CapturedBan:
    """Records the `which_player` that `UnitCannotDefend` hands to the ban factory.

    That argument is the whole decision and is otherwise closed over where no test can see it.
    """

    def __enter__(self):
        self.seen = []
        self.original = AbilityFactory.PlayersCannotTriggerAbility

        def spy(which_player, which_ability, **kwargs):
            self.seen.append(which_player)
            return self.original(which_player, which_ability, **kwargs)

        AbilityFactory.PlayersCannotTriggerAbility = staticmethod(spy)
        return self

    def __exit__(self, *exc):
        AbilityFactory.PlayersCannotTriggerAbility = self.original

    @property
    def which_player(self):
        assert len(self.seen) == 1, f"expected exactly one ban, got {self.seen}"
        return self.seen[0]


class TestWhoGetsBanned(unittest.TestCase):

    def _ban_for(self, which_unit, attacker="Villain"):
        with _CapturedBan() as captured:
            AbilityFactory.UnitCannotDefend(
                which_unit, attacker, cannot_trigger_defense_ability=True)
            return captured.which_player

    def test_a_finder_still_bans_only_that_card_s_controller(self):
        """Supersonic (`cards/pack/aos/supersonic/50156.py`) is the one caller the assert allowed.

        It is the branch with something to lose, so it is the regression this pins.
        """
        finder = CardFinder(non_trait="AERIAL")

        which_player = self._ban_for(finder, attacker="This")

        self.assertIsInstance(which_player, PlayerFinder)

    def test_an_unrestricted_shape_bans_every_player(self):
        """A literal or a CardFace class restricts every character, so no player may respond.

        This characterises the branch rather than blessing it. The ban invalidates any non-forced
        `defense`-labelled ability from a matching player while the matching attacker is
        attacking, so for Puppet Master (`55061`, "Allies cannot ... defend against the villain's
        attacks") "AnyPlayer" also reaches the hero's own defense abilities, which that card does
        not say. That question was unreachable while the assert made the card unloadable, and is
        worth settling separately. Pinned here so the answer cannot change silently.
        """
        for which_unit in (Unit2, "Character", Ally):
            with self.subTest(which_unit=which_unit):
                self.assertEqual(self._ban_for(which_unit), "AnyPlayer")

    def test_the_attached_identity_literal_reaches_its_branch(self):
        """The old spelling was "Attached", which is not a CardType, so this was dead code.

        Nothing in `cards/` passes it today. It is pinned so the branch cannot rot again
        unnoticed, since a silent fall-through here bans every player instead of one.
        """
        self.assertEqual(self._ban_for("AttachedIdentity"), "AttachedPlayer")


if __name__ == "__main__":
    unittest.main()
