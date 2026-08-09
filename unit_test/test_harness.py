"""First replay-independent tests (tracker item I2).

These build a live game from a scenario + hero name with no fixture on disk, which means they
do not depend on replay determinism and do not break when unrelated behavior changes.
"""
import unittest

from unit_test.harness import GameFixture


class TestHarness(unittest.TestCase):

    def test_game_builds_without_a_replay_file(self):
        """A World can be constructed and inspected with no recorded game."""
        with GameFixture("rhino", ["spider_man"], seed=42) as fx:
            world = fx.world
            self.assertIsNotNone(world, "GameSetup produced no world")
            self.assertEqual(len(world.const_players), 1)
            self.assertTrue(world.scenario.IsVillainReady(), "no villain in play")
            self.assertGreaterEqual(len(world.area_schemes_main.Get()), 1, "no main scheme in play")

    def test_cheat_dsl_puts_a_named_card_in_hand(self):
        """The debug DSL can force board state, which is what makes assertions cheap to set up."""
        with GameFixture("rhino", ["spider_man"], seed=42) as fx:
            hand = fx.player(0).hand_cards
            before = hand.GetSize()
            fx.cheat("Gain('Enhanced Reflexes')")
            self.assertEqual(hand.GetSize(), before + 1)
            self.assertIn("Enhanced Reflexes", [f.name for f in hand.Get()])


if __name__ == "__main__":
    unittest.main()
