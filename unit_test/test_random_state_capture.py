"""Tests for RNG state capture (the debug-undo support in engine/lib/random.py).

Every draw used to call numpy.random.get_state() and append the result to Random.states. That
copies numpy's Mersenne buffer each time, measured at roughly 34x the cost of the shuffle itself,
and nothing ever trims the list. The only consumer is Random.Undo, reached from a single debug
cheat, so the capture is now opt-in.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes
first even though these tests only touch engine.
"""
import unittest

import engine  # noqa: F401  must precede any game import
from engine.lib.random import Random, ENABLE_RANDOM_UNDO, DISABLE_NUMPY_RANDOM


class _Backend:
    """Force a specific RNG backend for the duration of a test."""

    def __init__(self, numpy_disabled: bool):
        self.numpy_disabled = numpy_disabled

    def __enter__(self):
        self.previous = DISABLE_NUMPY_RANDOM.value
        DISABLE_NUMPY_RANDOM.value = self.numpy_disabled
        return self

    def __exit__(self, *exc):
        DISABLE_NUMPY_RANDOM.value = self.previous


class _Capture:
    """Turn state capture on or off for the duration of a test."""

    def __init__(self, enabled: bool):
        self.enabled = enabled

    def __enter__(self):
        self.previous = ENABLE_RANDOM_UNDO.value
        ENABLE_RANDOM_UNDO.value = self.enabled
        Random.SetSeed(1234)
        return self

    def __exit__(self, *exc):
        ENABLE_RANDOM_UNDO.value = self.previous


class TestStateCapture(unittest.TestCase):

    def test_capture_is_off_by_default(self):
        self.assertFalse(ENABLE_RANDOM_UNDO.value)

    def test_nothing_is_retained_when_capture_is_off(self):
        with _Capture(False):
            for _ in range(50):
                Random.Shuffle(list(range(10)))
            self.assertEqual(len(Random.states), 0)

    def test_state_is_retained_when_capture_is_on(self):
        with _Capture(True):
            for _ in range(50):
                Random.Shuffle(list(range(10)))
            self.assertEqual(len(Random.states), 50)

    def test_seeding_clears_retained_state(self):
        with _Capture(True):
            for _ in range(10):
                Random.Shuffle(list(range(10)))
            self.assertEqual(len(Random.states), 10)
            Random.SetSeed(99)
            self.assertEqual(len(Random.states), 0)

    def test_undo_still_rewinds_the_generator(self):
        """The debug cheat this machinery exists for must keep working."""
        with _Capture(True):
            deck = list(range(20))

            first = deck[:]
            Random.Shuffle(first)

            Random.Undo()

            again = deck[:]
            Random.Shuffle(again)

            self.assertEqual(first, again, "Undo did not restore the generator position")

    def test_undo_rewinds_the_bundled_backend_too(self):
        """The bundled backend is the default now, so the cheat has to work there.

        It used to hit a bare `pass`, which meant `Unshuffle` at cheat_cmd_helper.py:390 quietly
        did nothing rather than rewinding. A debug command that silently no-ops is worse than one
        that refuses.
        """
        with _Backend(numpy_disabled=True), _Capture(True):
            deck = list(range(20))

            first = deck[:]
            Random.Shuffle(first)

            Random.Undo()

            again = deck[:]
            Random.Shuffle(again)

            self.assertEqual(first, again, "Undo did not restore the bundled generator")

    def test_undo_without_capture_explains_itself(self):
        """Calling the cheat with capture off must say why, not raise IndexError on an empty pop."""
        with _Capture(False):
            Random.Shuffle(list(range(10)))
            with self.assertRaises(AssertionError) as caught:
                Random.Undo()
            self.assertIn("enable_random_undo", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
