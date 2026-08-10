Went ahead and implemented the second half of this, and one of my numbers needs correcting.

The 34x I quoted was the capture measured on its own against a bare `numpy.random.shuffle`. That part holds up. But through `Random.Shuffle`, which is what actually runs, gating the capture off gives 18.9x rather than 34x. Over 20,000 shuffles of a 50-card list it goes from 21.6 µs per call to 1.1 µs, and retained memory goes from 49.9 MB to zero.

The gap is `AddCounter`. It builds an f-string and calls `Log.DebugSilent` on every draw whether or not the category is enabled, which costs 0.54 µs. Raw `numpy.random.shuffle` is 0.67 µs and `Random.Shuffle` with capture disabled is 1.21 µs, so that logging is about 45% of what's left. Small, but it's now the largest thing in there, and it'd be easy to skip the formatting when the category is off if you think that's worth doing.

What I ended up with is close to the diff above. Capture sits behind a new `enable_random_undo`, default off, and `SetSeed` clears the list since positions recorded against an old seed can't be rewound to anyway. `Undo` asserts with an explanation when capture is off rather than popping an empty list, so the cheat at `cheat_cmd_helper.py:390` fails readably if someone forgets the flag instead of raising IndexError.

There are tests, including one that rewinds the generator and reshuffles to confirm the cheat still produces the same sequence. Happy to send the whole thing whenever you want it.
