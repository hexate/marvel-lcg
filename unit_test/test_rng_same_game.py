"""Both RNG backends deal the same game from the same seed, checked through the real engine.

Split out from test_rng_numpy_parity.py on purpose. That file compares generators and imports
nothing but numpy, so it can travel with the F10 fix as a self-contained contribution. This one
needs the replay-independent harness (tracker item I2), so it lives where the harness lives.

The claim here is the one a player would care about: not "the two generators agree on a sequence of
integers" but "the same seed deals the same cards". It needs no replay fixture, so it does not
depend on the replay determinism it is testing.

`game/` cannot be imported on its own because of a circular import between game.object and
game.player, so `import engine` has to come first.
"""
import unittest

import engine  # noqa: F401  must precede any game import


class TestBackendsDealTheSameGame(unittest.TestCase):

    def _opening_hand(self, *, numpy_disabled: bool, seed: int = 42, expect_backend: str = ""):
        from unit_test.harness import GameFixture
        from engine.lib.random import Random, DISABLE_NUMPY_RANDOM

        previous = DISABLE_NUMPY_RANDOM.value
        DISABLE_NUMPY_RANDOM.value = numpy_disabled
        try:
            if expect_backend:
                # Without this the test could pass by running numpy twice and comparing it to
                # itself, which is the failure mode a config-flipping test is most likely to have.
                self.assertEqual(Random.BackendName(), expect_backend,
                                 "the backend flag did not take effect")
            with GameFixture("rhino", ["spider_man"], seed=seed) as fx:
                return [card.name for card in fx.player(0).hand_cards.Get()]
        finally:
            DISABLE_NUMPY_RANDOM.value = previous

    def test_same_seed_deals_the_same_opening_hand(self):
        on_numpy = self._opening_hand(numpy_disabled=False, expect_backend="numpy")
        on_bundled = self._opening_hand(numpy_disabled=True, expect_backend="mt19937-v2")

        self.assertEqual(on_numpy, on_bundled,
                         "the same seed dealt two different hands, so saves are not portable")
        self.assertTrue(on_numpy, "no cards dealt; the comparison would pass on two empty hands")

    def test_a_different_seed_deals_a_different_hand(self):
        """Proves the hand depends on the generator, so the comparison above means something."""
        seed_42 = self._opening_hand(numpy_disabled=False, seed=42)
        seed_7 = self._opening_hand(numpy_disabled=False, seed=7)

        self.assertNotEqual(seed_42, seed_7, "the opening hand does not depend on the seed")


if __name__ == "__main__":
    unittest.main()
