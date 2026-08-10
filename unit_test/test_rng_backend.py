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


class TestBackendsAgree(unittest.TestCase):
    """This assertion used to be its own opposite.

    F3 shipped a guard that refused to replay a scene across backends, and pinned the premise that
    the two disagreed so the guard could not quietly become pointless. F10 removed the premise
    instead: the bundled generator now reproduces numpy operation for operation, so the guard's job
    changed from "refuse the other backend" to "refuse the retired one". The pin stays, inverted,
    because everything below depends on the two being interchangeable.

    Full operation-by-operation coverage is in test_rng_numpy_parity.py.
    """

    def test_same_seed_gives_the_same_sequence(self):
        seed, deck = 12345, list(range(10))

        bundled = BundledRandom()
        bundled.seed(seed)
        a = deck[:]
        bundled.shuffle(a)

        numpy.random.seed(seed)
        b = deck[:]
        numpy.random.shuffle(b)

        self.assertEqual(a, b, "backends diverged; a save file is no longer portable between them")


class TestBackendGuard(unittest.TestCase):

    def test_backend_name_reflects_the_config(self):
        self.assertEqual(Random.BackendName(numpy_disabled=False), "numpy")
        self.assertEqual(Random.BackendName(numpy_disabled=True), "mt19937-v2",
                         "the bundled generator is versioned; plain 'mt19937' is the retired one")

    def test_matching_backend_is_accepted(self):
        Random.CheckSceneBackend(Random.BackendName(), "some_scene.json")

    def test_either_current_backend_is_accepted(self):
        """The two produce the same sequence, so a scene recorded under one replays under the other.

        This is the payoff irefrixs asked for in issue #4: the numpy dependency can be dropped
        without invalidating a single existing save. Note that neither call depends on which backend
        is configured right now, because the question is no longer "does it match" but "can this
        build reproduce that sequence".
        """
        Random.CheckSceneBackend(Random.BACKEND_NUMPY, "recorded_under_numpy.json")
        Random.CheckSceneBackend(Random.BACKEND_BUNDLED, "recorded_under_bundled.json")

    def test_retired_generator_is_refused(self):
        """The one case there is no way to honour.

        The old bundled sequence cannot be reproduced by any build, so the message must not send
        anyone hunting for a config flag the way the previous mismatch message did.
        """
        with self.assertRaises(AssertionError) as caught:
            Random.CheckSceneBackend(Random.BACKEND_BUNDLED_RETIRED, "old_bundled_scene.json")

        message = str(caught.exception)
        self.assertIn(Random.BACKEND_BUNDLED_RETIRED, message)
        self.assertIn("retired", message)
        self.assertIn("no config flag", message)
        self.assertIn("old_bundled_scene.json", message, "the message has to name the file")

    def test_unknown_backend_is_refused(self):
        """A future generator, or a corrupted field, must not be assumed compatible."""
        with self.assertRaises(AssertionError) as caught:
            Random.CheckSceneBackend("mt19937-v3", "scene_from_the_future.json")

        self.assertIn("unknown", str(caught.exception))

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
        """Re-saving a scene loaded from disk must keep the generator that actually produced it.

        Deliberately uses the retired value. A scene recorded by the old generator has to keep
        saying so after a re-save, otherwise re-saving would relabel an unreplayable file as a
        replayable one and the guard would wave it through next time.
        """
        from game.scene import Scene
        from engine.user.user_info import UserInfo
        UserInfo.Initialize()

        scene = Scene()
        scene.SetMetadataStr("rng", "mt19937")
        scene.PrepareSave(_FakeGame(), playtime=None)
        self.assertEqual(scene.rng, "mt19937")


if __name__ == "__main__":
    unittest.main()
