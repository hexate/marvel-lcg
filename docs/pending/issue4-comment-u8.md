# U8: reply on issue #4

Status: POSTED 2026-08-10 as comment 5243489423, then edited at 18:31 UTC before he replied. This
file matches the live comment. Supersedes `issue4-comment-rng-figure.md` (U6), whose correction is
folded into section 1 below.

The edit rewrote section 1's second paragraph: the original blamed the f-string for 0.55 µs and
invited him to fix it, which was wrong on the number, wrong on the cause, and pointed at a saving
of microseconds per game. See F9.

Context this answers: irefrixs's two comments of 2026-08-10, giving the numpy history and pointing
at `mggarofalo/marvel-lcg`'s `mt19937.py`.

---

Thanks, that history answers it completely. Knowing numpy is canonical because every save encodes
its sequence, and that the pure-Python path was meant to reproduce numpy and never got there,
turns this from an open question into a fixed target. So I built it. Details in section 3, but the
short version is that your MT19937 was never the problem, and the gap is about 40 lines.

Two smaller things first.

## 1. Correcting my own number, 18.9x not 34x

The 34x in the title was the capture measured on its own against a bare `numpy.random.shuffle`.
That part holds up, but through `Random.Shuffle`, which is what actually runs, gating the capture
off gives 18.9x. Over 20,000 shuffles of a 50-card list it goes from 22.0 µs per call to 1.2 µs,
and retained memory goes from about 55 MB, measured with `tracemalloc`, to zero.

The rest of the gap is the wrapper itself, and I should be more precise than I was. Raw
`numpy.random.shuffle` is 0.62 µs against 1.16 µs for `Random.Shuffle` with capture disabled.
`AddCounter` is 0.312 µs of that 0.54, and the largest piece of it is not the f-string but the
`from engine.log import Log` inside the function, at 0.148 µs against 0.056 for the formatting.
Guarding both behind the category check takes it to 0.068 µs.

I am not suggesting you make that change. `AddCounter` runs once per draw, and a game makes very
few: I measured `GameSetup` at 2 draws solo and 6 at four players, because shuffling is per deck
rather than per decision. The saving across a whole game is microseconds. I am correcting it only
because I quoted a number at you and it should be right.

## 2. The state-capture cleanup you said yes to

That one is done: <https://github.com/hexate/marvel-lcg/compare/master...pr/random-state-capture>,
one commit off your master. Capture sits behind a new `enable_random_undo`,
default off. `SetSeed` clears the list, since positions recorded against an old seed cannot be
rewound to anyway. `Undo` asserts with an explanation when capture is off, so the cheat at
`cheat_cmd_helper.py:390` fails readably instead of raising `IndexError` on an empty list. There
are tests, including one that rewinds the generator and reshuffles to confirm the cheat still
produces the same sequence.

## 3. The pure-Python generator that matches numpy

I checked the file you linked. It does reproduce numpy for seeding, the raw word stream, `Shuffle`
and `Choice`, which is a genuinely useful result and worth saying plainly. It diverges in one
place: `ChooseWithoutReplacement`. numpy implements `choice(size=k, replace=False)` as
`permutation(n)[:k]`, a full shuffle truncated, spending `n - 1` draws. That file does a partial
Fisher-Yates spending `k`. Same distribution, different stream position, so one call desynchronises
every draw after it. Shuffling and taking the first `k` reproduces numpy exactly, which I tested
over 1,500 cases.

Then I ran the same comparison against your own `engine/lib/mt19937.py`, and this is the part worth
your time:

```
seeding, internal state after seed  : identical to numpy, 300 seeds
raw uint32 stream                   : identical to numpy, 450,000 words
```

Your Mersenne Twister is already numpy's, word for word. Everything that failed was the layer above
it:

- `randint` scales a float (`extract_number() / 2**32`) to pick an index. numpy uses masked
  rejection on the raw words, so it sometimes consumes more than one word per draw. No float
  scaling can imitate that, because the draw count itself carries information.
- `shuffle` makes `10 * len(X)` random transpositions. numpy walks Fisher-Yates downward and spends
  `len - 1` draws.

So the three functions, not the generator:

```python
def randbelow(self, n: int) -> int:
    """[0, n) the way numpy does it: mask to the next power of two, redraw if out of range."""
    mask = n - 1
    for shift in (1, 2, 4, 8, 16):
        mask |= mask >> shift
    while True:
        value = self.extract_number() & mask
        if value < n:
            return value

def randint(self, a: int, b: int):
    return a + self.randbelow(b - a)

def shuffle(self, X):
    for i in range(len(X) - 1, 0, -1):
        j = self.randbelow(i + 1)
        X[i], X[j] = X[j], X[i]

def choice(self, X, replace=True, size=1):
    newX = list(X)
    if replace:
        return [newX[self.randbelow(len(newX))] for _ in range(size)]
    self.shuffle(newX)          # numpy is permutation(n)[:size], not a partial shuffle
    return newX[:size]
```

`choice_one` needs no change, since it goes through `randint`.

With that in place the two backends are interchangeable. Verified per operation, on lists of card
objects rather than ints (numpy takes a different path for object arrays), and across 54
interleaved operations off one stream, which is what catches an operation that returns the right
answer while spending the wrong number of draws. The end-to-end check is the one I trust most:
Spider-Man against Rhino at seed 42 deals the identical opening hand under both backends, and a
different seed deals a different hand, so the comparison is not vacuous.

That means `disable_numpy_random` can default to `true` and the 10 MB dependency goes away without
invalidating a single save file. Which, if I have understood your version 1 problem correctly, is
the thing that was blocking it.

One consequence worth flagging rather than burying. Any scene recorded by the *old* bundled path
cannot be replayed after this change, because that sequence no longer exists anywhere. You said all
save files use numpy, so I expect that set is empty in practice, but it is a real edge. On my side I
versioned the recorded backend name to `mt19937-v2` and refuse the old value with a message saying
so, rather than letting it look replayable. Your call whether that is worth the string.

The branch is here, with the tests:
<https://github.com/hexate/marvel-lcg/compare/pr/rng-backend-determinism...pr/rng-numpy-parity>

That comparison is against the scene-stamp change rather than against master, since this builds on
it. One commit, four files. Happy to paste the diff inline instead if that is easier to read, and
no pressure either way given the project is sunset. You answered a question that had been bothering
me, and the fix mostly fell out of the answer, so it seemed worth handing back.
