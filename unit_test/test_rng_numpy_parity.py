"""The bundled generator must reproduce numpy's sequence, operation for operation.

Every save file in existence encodes numpy's sequence, so numpy is the canonical generator and the
bundled one is only useful if it is indistinguishable from it (irefrixs, issue #4, 2026-08-10).
That is a stronger requirement than "both are MT19937". Two correct Mersenne Twisters agreeing on
every word still deal different cards if they map words onto indices differently or consume a
different number of words per operation.

These tests cover exactly the three operations `engine/lib/random.py` dispatches to a backend, and
deliberately import nothing but numpy so the whole file travels with the fix.
`tools/rng_parity_check.py` is the same comparison at much wider coverage; this file is the part
that runs on every test pass. Making the same claim end to end, by dealing a real hand twice,
needs a harness that can drive a game without a replay file, so that test ships with the harness
instead of here.

`game/` cannot be imported on its own because of a circular import between game.object and
game.player, so `import engine` has to come first.
"""
import unittest

import engine  # noqa: F401  must precede any game import
from engine.lib.mt19937 import Random as Bundled
import numpy.random

SEEDS = (0, 1, 42, 12345, 999983, 2**31 - 2)
# Deck and hand sizes, plus 2 and 3 where a Fisher-Yates bound is easy to get wrong, plus 2^k+1
# sizes where masked rejection rejects a draw most often.
SIZES = (2, 3, 5, 9, 17, 33, 40, 52, 65, 101)


class TestShuffleParity(unittest.TestCase):

    def test_shuffle_matches_numpy(self):
        for seed in SEEDS:
            for n in SIZES:
                numpy.random.seed(seed)
                want = list(range(n))
                numpy.random.shuffle(want)

                bundled = Bundled(seed)
                got = list(range(n))
                bundled.shuffle(got)

                self.assertEqual(want, got, f"diverged at seed={seed} n={n}")


class TestChoiceParity(unittest.TestCase):

    def test_choice_one_matches_numpy(self):
        """`Random.RandomChoice` dispatches here."""
        for seed in SEEDS:
            for n in (2, 3, 7, 13, 52, 100):
                numpy.random.seed(seed)
                want = int(numpy.random.choice(list(range(n))))

                got = Bundled(seed).choice_one(list(range(n)))

                self.assertEqual(want, got, f"diverged at seed={seed} n={n}")

    def test_choice_without_replacement_matches_numpy(self):
        """`Random.RandomChoice2` dispatches here.

        numpy implements `replace=False` as `permutation(n)[:k]`, a full shuffle truncated, so it
        spends `n - 1` draws where picking `k` items directly would spend `k`. Getting the returned
        items right is not enough; the stream has to end up in the same place.
        """
        for seed in SEEDS:
            for n, k in ((10, 3), (52, 7), (20, 5), (52, 1), (8, 8)):
                numpy.random.seed(seed)
                want = [int(v) for v in numpy.random.choice(list(range(n)), size=k, replace=False)]

                got = Bundled(seed).choice(list(range(n)), replace=False, size=k)

                self.assertEqual(want, got, f"diverged at seed={seed} n={n} k={k}")

    def test_choice_with_replacement_matches_numpy(self):
        """Nothing in the engine calls this, so it is pinned rather than relied on.

        It matches today. Without a test, a later change to the unused branch could quietly make it
        wrong, and the next caller would inherit a bug that looks like working code.
        """
        for seed in SEEDS:
            for n, k in ((10, 3), (52, 5), (2, 8)):
                numpy.random.seed(seed)
                want = [int(v) for v in numpy.random.choice(list(range(n)), size=k, replace=True)]

                got = Bundled(seed).choice(list(range(n)), replace=True, size=k)

                self.assertEqual(want, got, f"diverged at seed={seed} n={n} k={k}")


class TestStreamStaysInLockstep(unittest.TestCase):
    """The test that actually matters for replay.

    A game does not perform one draw, it performs thousands off one stream. Every operation above
    could return the right answer in isolation while consuming the wrong number of words, and the
    divergence would only appear later, as a different card somewhere deep in the game. Interleaving
    the three operations catches that.
    """

    OPERATIONS = [("shuffle", 52, 0), ("choice", 12, 0), ("sample", 40, 5),
                  ("shuffle", 7, 0), ("choice", 52, 0), ("sample", 10, 1),
                  ("shuffle", 2, 0), ("choice", 3, 0), ("sample", 52, 51)] * 6

    def test_fifty_four_operations_stay_in_lockstep(self):
        for seed in SEEDS:
            numpy.random.seed(seed)
            bundled = Bundled(seed)

            for step, (kind, n, k) in enumerate(self.OPERATIONS):
                items = list(range(n))
                if kind == "shuffle":
                    want = items[:]
                    numpy.random.shuffle(want)
                    got = items[:]
                    bundled.shuffle(got)
                elif kind == "choice":
                    want = int(numpy.random.choice(items))
                    got = bundled.choice_one(items)
                else:
                    want = [int(v) for v in numpy.random.choice(items, size=k, replace=False)]
                    got = bundled.choice(items, replace=False, size=k)

                self.assertEqual(want, got,
                                 f"stream diverged at seed={seed} operation {step}: {kind}(n={n})")


class _Card:
    """Stands in for a game object: no ordering, no equality, not convertible to a number."""

    def __init__(self, card_id: str):
        self.card_id = card_id

    def __repr__(self):
        return f"_Card({self.card_id})"


class TestObjectListParity(unittest.TestCase):
    """The engine shuffles decks of card objects, never lists of ints.

    numpy turns a list of arbitrary objects into an object array, which is a different code path
    from the integer one the tests above exercise. If index selection differed there, every test
    above could pass while real decks diverged.
    """

    def test_shuffle_of_objects_matches_numpy(self):
        for seed in SEEDS:
            deck = [_Card(f"c{i}") for i in range(52)]

            numpy.random.seed(seed)
            want = deck[:]
            numpy.random.shuffle(want)

            bundled = Bundled(seed)
            got = deck[:]
            bundled.shuffle(got)

            self.assertEqual([c.card_id for c in want], [c.card_id for c in got],
                             f"diverged at seed={seed}")

    def test_choice_of_objects_matches_numpy(self):
        for seed in SEEDS:
            deck = [_Card(f"c{i}") for i in range(52)]

            numpy.random.seed(seed)
            want = numpy.random.choice(deck)  # type: ignore

            got = Bundled(seed).choice_one(deck)

            self.assertEqual(want.card_id, got.card_id, f"diverged at seed={seed}")


if __name__ == "__main__":
    unittest.main()
