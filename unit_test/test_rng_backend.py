"""Tests for RNG backend recording on scenes.

A save file is an input log replayed through game logic, so replay only reproduces the original
game if the random number generator produces the same sequence. The engine ships two backends and
`disable_numpy_random` switches between them. They disagree from the same seed, so a scene
recorded under one and replayed under the other silently becomes a different game.

`game/` cannot be imported on its own because of a circular import between game.object and
game.player, so `import engine` has to come first.
"""
import unittest

import engine  # noqa: F401  must precede any game import
from engine.lib.random import Random
from engine.lib.mt19937 import Random as BundledRandom
import numpy.random


class TestBackendsDisagree(unittest.TestCase):

    def test_same_seed_gives_different_sequences(self):
        """The premise. If this ever fails, the rest of this file is unnecessary."""
        seed, deck = 12345, list(range(10))

        bundled = BundledRandom()
        bundled.seed(seed)
        a = deck[:]
        bundled.shuffle(a)

        numpy.random.seed(seed)
        b = deck[:]
        numpy.random.shuffle(b)

        self.assertNotEqual(a, b, "backends agree; the mismatch guard would be pointless")


class TestBackendGuard(unittest.TestCase):

    def test_backend_name_reflects_the_config(self):
        self.assertEqual(Random.BackendName(numpy_disabled=False), "numpy")
        self.assertEqual(Random.BackendName(numpy_disabled=True), "mt19937")

    def test_matching_backend_is_accepted(self):
        Random.CheckSceneBackend(Random.BackendName(), "some_scene.json")

    def test_mismatched_backend_is_refused(self):
        other = "mt19937" if Random.BackendName() == "numpy" else "numpy"
        with self.assertRaises(AssertionError) as caught:
            Random.CheckSceneBackend(other, "some_scene.json")
        self.assertIn(other, str(caught.exception))

    def test_unrecorded_backend_is_allowed(self):
        """Scenes saved before this field existed must still load."""
        Random.CheckSceneBackend("", "old_scene.json")


class _FakeReplay:
    history_inputs: list = []


class _FakeControllerManager:
    replay = _FakeReplay()


class _FakeGame:
    controller_manager = _FakeControllerManager()


class TestSceneRecordsBackend(unittest.TestCase):

    def test_save_stamps_the_backend(self):
        from game.scene import Scene
        from engine.user.user_info import UserInfo
        UserInfo.Initialize()

        scene = Scene()
        self.assertEqual(scene.rng, "", "a fresh scene should carry no backend yet")

        scene.PrepareSave(_FakeGame(), playtime=None)
        self.assertEqual(scene.rng, Random.BackendName())

    def test_save_does_not_overwrite_a_recorded_backend(self):
        """Re-saving a scene loaded from disk must keep the generator that actually produced it."""
        from game.scene import Scene
        from engine.user.user_info import UserInfo
        UserInfo.Initialize()

        scene = Scene()
        scene.SetMetadataStr("rng", "mt19937")
        scene.PrepareSave(_FakeGame(), playtime=None)
        self.assertEqual(scene.rng, "mt19937")


if __name__ == "__main__":
    unittest.main()
