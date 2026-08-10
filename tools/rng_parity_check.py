#!/usr/bin/env python3
"""Measure a pure-Python MT19937 against numpy's legacy RandomState, draw for draw.

Why this exists. Every existing save file encodes numpy's sequence, so numpy is the canonical
generator (irefrixs, issue #4, 2026-08-10). The bundled `engine/lib/mt19937.py` was meant to
reproduce it and does not, which is F3. Any candidate replacement has to be checked against the
three operations `engine/lib/random.py` actually performs, not against MT19937 in the abstract:

    Random.Shuffle       -> numpy.random.shuffle
    Random.RandomChoice  -> numpy.random.choice
    Random.RandomChoice2 -> numpy.random.choice(size=k, replace=False)

Matching the raw 32-bit stream is necessary but nowhere near sufficient. Two implementations can
agree on every word and still deal different cards, because what matters is how many words each
operation consumes and how it maps them onto indices. A single operation that consumes a different
number of draws desynchronizes everything after it.

Usage:

    .venv/bin/python tools/rng_parity_check.py                    # audit the recommended candidate
    .venv/bin/python tools/rng_parity_check.py --candidate PATH   # audit some other file
    .venv/bin/python tools/rng_parity_check.py --bundled          # audit ours, the F3 control

The candidate must expose a class named `Mt19937` (or `--class-name`) with `NextUInt32`, `Shuffle`,
`Choice` and `ChooseWithoutReplacement`. With no `--candidate`, the file irefrixs recommended is
fetched to `out/` and pinned to the commit he linked.

Exits non-zero if any check fails, so it can gate a change.
"""
import argparse
import importlib.util
import os
import sys
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# The file irefrixs pointed at in issue #4, pinned to the commit he linked rather than to a branch,
# so this check keeps measuring the thing he actually recommended.
CANDIDATE_URL = (
    "https://raw.githubusercontent.com/mggarofalo/marvel-lcg/"
    "3c8743eb7827c2fe26690510d816697fc6ae0a57/py_src/engine/lib/mt19937.py"
)
CANDIDATE_CACHE = os.path.join(REPO_ROOT, "out", "mt19937_candidate.py")

# Deck-sized and hand-sized, plus 2^k+1 sizes where masked rejection rejects most often, plus 2 and
# 3 where an off-by-one in a Fisher-Yates bound hides.
SIZES = (2, 3, 5, 7, 9, 13, 15, 17, 33, 40, 52, 60, 65, 101, 129, 250, 513, 1025)
SEEDS = range(300)


def load_candidate(path, class_name):
    spec = importlib.util.spec_from_file_location("rng_candidate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, class_name):
        sys.exit(f"{path} has no class named {class_name!r}")
    return getattr(module, class_name)


def fetch_candidate():
    if os.path.exists(CANDIDATE_CACHE):
        print(f"candidate: {CANDIDATE_CACHE} (cached)")
        return CANDIDATE_CACHE
    os.makedirs(os.path.dirname(CANDIDATE_CACHE), exist_ok=True)
    print(f"fetching {CANDIDATE_URL}")
    with urllib.request.urlopen(CANDIDATE_URL) as response:
        body = response.read()
    with open(CANDIDATE_CACHE, "wb") as handle:
        handle.write(body)
    print(f"candidate: {CANDIDATE_CACHE} ({len(body)} bytes)")
    return CANDIDATE_CACHE


class BundledAdapter:
    """`engine/lib/mt19937.py` behind the candidate interface, as a known-bad control.

    It has no `ChooseWithoutReplacement`; `choice(replace=False)` is the nearest thing.
    """

    def __init__(self, seed):
        from engine.lib.mt19937 import Random
        self.rand = Random(seed)

    # Same state under different names, so the seeding check compares like with like instead of
    # reporting a missing attribute as a divergence.
    @property
    def mt(self):
        return self.rand.MT

    @property
    def index(self):
        return self.rand.index

    def NextUInt32(self):
        return self.rand.extract_number()

    def Shuffle(self, items):
        self.rand.shuffle(items)

    def Choice(self, sequence):
        return self.rand.choice_one(sequence)

    def ChooseWithoutReplacement(self, sequence, k):
        return self.rand.choice(list(sequence), replace=False, size=k)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--candidate", help="path to the implementation under test")
    parser.add_argument("--class-name", default="Mt19937")
    parser.add_argument("--bundled", action="store_true",
                        help="audit engine/lib/mt19937.py instead, the F3 control")
    args = parser.parse_args()

    try:
        import numpy as np
    except ImportError:
        sys.exit("numpy is required to measure against it: .venv/bin/python -m pip install numpy")

    if args.bundled:
        Candidate = BundledAdapter
        print("candidate: engine/lib/mt19937.py (bundled, expected to fail)")
    else:
        path = args.candidate or fetch_candidate()
        Candidate = load_candidate(path, args.class_name)
    print(f"reference: numpy {np.__version__} legacy RandomState\n")

    failures = []

    def check(name, predicate, cases):
        """Run `predicate` over `cases`, stopping at the first divergence."""
        for case in cases:
            detail = predicate(*case)
            if detail:
                failures.append(name)
                print(f"FAIL  {name}\n      first divergence: {detail}")
                return
        print(f"PASS  {name}  ({len(cases)} cases)")

    # Seeding. numpy uses init_genrand for a scalar seed that fits in 32 bits, so a correct
    # candidate lands on numpy's exact internal state before any draw happens.
    def seeding(seed):
        np.random.seed(seed)
        _, keys, pos = np.random.get_state()[:3]
        candidate = Candidate(seed)
        state = getattr(candidate, "mt", None)
        if state is None:
            return f"seed={seed}: no `mt` attribute to compare"
        if list(keys) != list(state) or pos != candidate.index:
            first = next((i for i, (a, b) in enumerate(zip(keys, state)) if a != b), None)
            return (f"seed={seed}: position numpy={pos} candidate={candidate.index}, "
                    f"first differing word at index {first}")
        return None

    # Raw stream. randint over the full 32-bit range accepts every draw, so this is the stream
    # itself with no rejection in the way.
    def raw_stream(seed):
        words = [int(w) for w in np.random.RandomState(seed).randint(0, 2**32, 1500, dtype=np.uint32)]
        candidate = Candidate(seed)
        mine = [candidate.NextUInt32() for _ in range(1500)]
        if words != mine:
            i = next(i for i, (a, b) in enumerate(zip(words, mine)) if a != b)
            return f"seed={seed}: word {i} numpy={words[i]} candidate={mine[i]}"
        return None

    def shuffle(seed, n):
        np.random.seed(seed)
        want = list(range(n))
        np.random.shuffle(want)
        candidate = Candidate(seed)
        got = list(range(n))
        candidate.Shuffle(got)
        if want != got:
            return f"seed={seed} n={n}: numpy={want[:10]} candidate={got[:10]}"
        return None

    def choice(seed, n):
        np.random.seed(seed)
        want = int(np.random.choice(list(range(n))))
        got = Candidate(seed).Choice(list(range(n)))
        if want != got:
            return f"seed={seed} n={n}: numpy={want} candidate={got}"
        return None

    # numpy implements replace=False as permutation(n)[:k], a full shuffle truncated, so it spends
    # n-1 draws where a partial Fisher-Yates spends k. Same distribution, different stream position.
    def without_replacement(seed, n, k):
        np.random.seed(seed)
        want = [int(v) for v in np.random.choice(list(range(n)), size=k, replace=False)]
        got = list(Candidate(seed).ChooseWithoutReplacement(list(range(n)), k))
        if want != got:
            return f"seed={seed} n={n} k={k}: numpy={want} candidate={got}"
        return None

    # The one that matters most: a game does not perform one operation, it performs thousands off a
    # single stream. Anything consuming the wrong number of draws shows up here even if every
    # isolated operation above passed.
    INTERLEAVED = [("shuffle", 52), ("choice", 12), ("shuffle", 40), ("choice", 3),
                   ("shuffle", 7), ("choice", 52), ("shuffle", 2), ("choice", 2)] * 8

    def interleaved(seed):
        np.random.seed(seed)
        candidate = Candidate(seed)
        for step, (kind, n) in enumerate(INTERLEAVED):
            if kind == "shuffle":
                want = list(range(n))
                np.random.shuffle(want)
                got = list(range(n))
                candidate.Shuffle(got)
            else:
                want = int(np.random.choice(list(range(n))))
                got = candidate.Choice(list(range(n)))
            if want != got:
                return f"seed={seed}: diverged at operation {step}, {kind}(n={n})"
        return None

    check("seeding lands on numpy's internal state", seeding, [(s,) for s in SEEDS])
    check("raw uint32 stream", raw_stream, [(s,) for s in SEEDS])
    check("Shuffle vs numpy.random.shuffle", shuffle,
          [(s, n) for s in SEEDS for n in SIZES])
    check("Choice vs numpy.random.choice", choice,
          [(s, n) for s in SEEDS for n in (2, 3, 7, 13, 52, 100, 1000)])
    check("ChooseWithoutReplacement vs choice(replace=False)", without_replacement,
          [(s, n, k) for s in SEEDS for n, k in ((10, 3), (52, 7), (20, 5), (52, 1), (8, 8))])
    check(f"{len(INTERLEAVED)} interleaved operations on one stream", interleaved,
          [(s,) for s in SEEDS])

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        print("A candidate that fails any check cannot replay existing save files faithfully.")
        return 1
    print("Every check passed. This implementation reproduces numpy for the operations the "
          "engine performs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
