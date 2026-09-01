"""Check that a rollout does not change the game it is predicting.

The invariant: `search:<w>:1:1` performs no perturbation and never adopts anything, so it must
replay `util:<w>` exactly. Any seed where the two disagree is a leak from the forward model back
into the live position.

Run this after touching `clone.py`, `search.py`, `turnplan.py`, or anything in the engine that a
rollout drives. It is cheap, about 15 seconds for 60 seeds, and it is the only check that catches
this class of bug: the games still finish, the results still look plausible, and nothing raises.

    .venv/bin/python tools/sim/check_isolation.py <scenario> <deck> [weights] [n]

History, so the number means something. It was 17 of 60 before the nested-container fix (J42) and
6 of 60 after. Zero is the goal and has never been reached.

When it is non-zero, the way to find the cause is a log diff, not a state diff. State diffs kept
saying everything was identical, because the fingerprints could not see the difference. Instead:
run both arms, suppress the rollout's own log output by saving and restoring `Log.all_log_text`
around `playout`, and diff. The two logs agree for hundreds of lines and then one has an event the
other lacks, which names the mechanism directly. That is how Retaliate went missing.

What has been ruled out for the remaining 6 of 60, so nobody repeats it. Each of these was
implemented and measured, and each left the count at exactly 6:

- Every reachable object's `__dict__`, snapshotted and restored with no module filter at all,
  not just `game.`.
- `Engine.game` added as a snapshot root alongside the world and the ability cache.
- Container nesting deeper than 3. Depths 5, 8 and 12 are identical to 3.
- Closure cells. Traversing `__closure__` finds no closure dict keyed by a game object that is
  reachable from the world or the ability cache, so `apply_faces` is not reached that way.
- Class-level state. Only `Log.all_log_text` and `Random.counter` change across a rollout, and
  restoring the counter changes nothing.
- `Engine.game.controller_manager`, swapped to the clone's for the rollout.
- The outer policy's own state: it is never called during a rollout, 0 times, and its stall
  counters are unchanged.
- Wall-clock dependence. `GameSession.timeout` is 0 and nothing else in `game/` reads a clock.
- Run-to-run non-determinism from set iteration over object ids. Both arms are perfectly
  deterministic across repeats.

What is known about the mechanism: the live game loses a card's *applied* state. On seed 926 the
two logs are identical in content but offset by one line, the scorer's game having an
`unapply [Captain America's Shield]` the other lacks, and on seed 901 the same root shows up as
Retaliate silently not firing. `apply_faces` and `unapply_effects` live as closure variables in
`when_this_in_play` (`game/ability/factory/environment_helper2.py:105`), which is state that sits
in a Python cell rather than on any object, but restoring cells did not move the count.

Traps this has already produced, all of which look like a correct fix and are not:

- A shallow snapshot is not enough. Keywords live two levels down, `self.keywords[k][face]`, so
  restoring an object's own attributes hands back the same inner dict the rollout mutated.
- Engine code reaches state through `Engine.game`, not through the world. `player_action.py:258`
  does `game = Engine.game`, so a rollout drives the clone's board with the *live* replay module.
  Real, and not the cause of J42: swapping it left the count at exactly 17.
- Identical results across a change mean the change did not run. Twice now.
"""
import concurrent.futures as cf
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY_BIN = os.path.join(REPO, ".venv", "bin", "python")
if not os.path.exists(PY_BIN):
    PY_BIN = sys.executable


def outcome(scen, deck, seed, mode):
    p = subprocess.run([PY_BIN, os.path.join(HERE, "run_game.py"), scen, deck, str(seed), mode],
                       capture_output=True, text=True, timeout=1800)
    try:
        d = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return ("NO_OUTPUT",)
    return (d.get("total_villain_dmg"), d.get("won"), d.get("rounds"))


def main():
    scen = sys.argv[1] if len(sys.argv) > 1 else "rhino"
    deck = sys.argv[2] if len(sys.argv) > 2 else "captain_america_stun_lock"
    wpath = sys.argv[3] if len(sys.argv) > 3 else \
        "tools/sim/weights_%s_%s.json" % (scen, deck)
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    seeds = list(range(900, 900 + n))

    def run(mode):
        with cf.ThreadPoolExecutor(max_workers=10) as pool:
            return dict(zip(seeds, pool.map(lambda s: outcome(scen, deck, s, mode), seeds)))

    plain = run("util:%s" % wpath)
    noop = run("search:%s:1:1" % wpath)
    bad = [s for s in seeds if plain[s] != noop[s]]

    print("%s / %s, %d seeds" % (scen, deck, len(seeds)))
    print("rollout leaks into the live game on %d of %d seeds" % (len(bad), len(seeds)))
    for s in bad[:8]:
        print("   seed %-5d plain=%-18s no-op rollout=%s" % (s, plain[s], noop[s]))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
