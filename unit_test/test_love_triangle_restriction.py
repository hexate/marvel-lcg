"""Love Triangle (`55062`) restricts one ally, not everybody at the table.

The card reads:

    Attach to an ally you control. Otherwise, this card gains surge. Attached ally cannot attack
    the villain or defend against the villain's attacks.

Only the attached ally is named, so there is no player-level ban to add. The card passed
`cannot_trigger_defense_ability=True` anyway, and `"AttachedAlly"` is a plain literal rather than a
`CardFinder`, so it took the fall-through branch in `UnitCannotDefend` and banned **every** player
from triggering any `defense`-labelled ability while the villain attacks. Its own attack half,
`UnitCannotAttackTarget`, adds no such ban, so the two halves of one sentence disagreed.

Before the `UnitCannotDefend` fix this combination asserted at import and the card could not load
at all, which is why the over-broad ban was never observed in play.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import importlib
import unittest

import engine  # noqa: F401  must precede any game import
from game.ability.factory import AbilityFactory

MODULE = "cards.pack.tt.trickster_magic.55062"


class TestLoveTriangleAddsNoPlayerLevelBan(unittest.TestCase):

    def test_the_card_builds_exactly_its_four_abilities(self):
        """A fifth would be the player-level ban, which this card has no text for."""
        abilities = importlib.import_module(MODULE).GetAbilities()

        self.assertEqual(len(abilities), 4,
                         "an extra ability here is the every-player defense ban")

    def test_the_defend_half_matches_the_attack_half(self):
        """One sentence covers both halves, so they should restrict the same people."""
        attack = AbilityFactory.UnitCannotAttackTarget("AttachedAlly", cannot_attack="Villain")
        defend = AbilityFactory.UnitCannotDefend("AttachedAlly", "Villain",
                                                 cannot_trigger_defense_ability=False)

        self.assertEqual(len(defend), len(attack),
                         "the defend half added a restriction the attack half does not")

    def test_asking_for_the_ban_would_restrict_every_player(self):
        """Pins what the old argument bought, so the reason for `False` stays visible.

        `"AttachedAlly"` is a literal, not a `CardFinder`, so it cannot narrow the ban to the
        ally's controller. The only options are every player or nobody, and this card wants
        nobody.
        """
        with_ban = AbilityFactory.UnitCannotDefend("AttachedAlly", "Villain",
                                                   cannot_trigger_defense_ability=True)

        self.assertEqual(len(with_ban), 2)


if __name__ == "__main__":
    unittest.main()
