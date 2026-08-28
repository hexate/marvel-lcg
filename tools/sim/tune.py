"""Automated weight tuning for the utility policy.

Hand-tuning the priority ladder plateaued, and the manual loop kept getting fooled by
small seed sets: a configuration that won 1 game in 10 won 1 in 100 the moment the
seeds changed. So this searches the weights by machine and always reports on seeds it
did not train on.

Fitness is deliberately dense. Wins are far too rare to steer a search at this level
of play, so the score is mostly "how much of the villain did you get through", with a
large bonus for actually finishing:

    fitness = mean(damage_done / villain_hp) + 2 * win_rate

Usage:
    .venv/bin/python tools/sim/tune.py <scenario> <deck> <villain_hp> [iterations]
"""
import concurrent.futures as cf
import json
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
PY_BIN = os.path.join(REPO, ".venv", "bin", "python")
if not os.path.exists(PY_BIN):
    PY_BIN = sys.executable

from weights import DEFAULT_WEIGHTS  # noqa: E402

# 25 training seeds overfitted badly: 6 wins of 25 on train, 1 of 25 held out. A win
# is worth 4% of the score on a set that small, which is well inside the noise, so the
# climber chased individual seeds. More seeds, and lean on the dense term.
TRAIN = [11, 23, 37, 49, 61, 73, 85, 97, 109, 121, 133, 145, 157, 169, 181,
         193, 205, 217, 229, 241, 3, 17, 29, 41, 53, 65, 77, 89, 101, 113,
         125, 137, 149, 161, 173, 185, 197, 209, 221, 233, 5, 19, 31, 43, 57,
         69, 81, 93, 105, 117, 129, 141, 153, 165, 177, 189, 201, 213, 225, 237]
WIN_BONUS = 1.0

TEST = [2, 8, 14, 20, 26, 32, 38, 44, 50, 56, 62, 68, 74, 80, 86,
        92, 98, 104, 110, 116, 122, 128, 134, 140, 146]


def play(args):
    scen, deck, seed, wpath = args
    try:
        p = subprocess.run([PY_BIN, os.path.join(HERE, "run_game.py"),
                            scen, deck, str(seed), "util:" + wpath],
                           capture_output=True, text=True, timeout=60)
        lines = (p.stdout or "").strip().splitlines()
        return json.loads(lines[-1]) if lines else {}
    except Exception:
        return {}


def evaluate(weights, scen, deck, villain_hp, seeds, pool):
    fd, wpath = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(weights, f)
    try:
        rows = list(pool.map(play, [(scen, deck, s, wpath) for s in seeds]))
    finally:
        os.unlink(wpath)
    if not rows:
        return 0.0, 0, 0.0
    prog, wins = [], 0
    for r in rows:
        dmg = r.get("total_villain_dmg")
        if dmg is None:
            dmg = r.get("villain_dmg") or 0
        prog.append(min(1.0, dmg / float(villain_hp)))
        wins += 1 if r.get("won") else 0
    mean_prog = sum(prog) / len(prog)
    win_rate = wins / float(len(rows))
    return mean_prog + WIN_BONUS * win_rate, wins, mean_prog


def main():
    scen, deck = sys.argv[1], sys.argv[2]
    villain_hp = float(sys.argv[3])
    iters = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    warm = sys.argv[5] if len(sys.argv) > 5 else None
    rng = random.Random(1234)

    keys = sorted(DEFAULT_WEIGHTS)
    best = dict(DEFAULT_WEIGHTS)
    if warm:
        with open(warm) as f:
            best.update(json.load(f))

    with cf.ThreadPoolExecutor(max_workers=10) as pool:
        best_fit, best_wins, best_prog = evaluate(best, scen, deck, villain_hp, TRAIN, pool)
        print(f"start        fit={best_fit:.3f} wins={best_wins}/{len(TRAIN)} prog={best_prog:.3f}",
              flush=True)

        temp = 1.0
        for it in range(iters):
            cand = dict(best)
            for k in rng.sample(keys, rng.randint(1, 4)):
                cand[k] = round(cand[k] + rng.gauss(0, 2.0 * temp), 2)
            fit, wins, prog = evaluate(cand, scen, deck, villain_hp, TRAIN, pool)
            mark = ""
            if fit > best_fit:
                best, best_fit, best_wins, best_prog = cand, fit, wins, prog
                mark = "  <- kept"
            temp = max(0.35, temp * 0.97)
            print(f"iter {it:3d}    fit={fit:.3f} wins={wins} prog={prog:.3f}"
                  f"   best={best_fit:.3f}{mark}", flush=True)

        test_fit, test_wins, test_prog = evaluate(best, scen, deck, villain_hp, TEST, pool)
        base_fit, base_wins, base_prog = evaluate(DEFAULT_WEIGHTS, scen, deck, villain_hp, TEST, pool)

    out = os.path.join(HERE, "weights_tuned.json")
    with open(out, "w") as f:
        json.dump(best, f, indent=1, sort_keys=True)
    print(f"\nTRAIN best fit={best_fit:.3f} wins={best_wins}/{len(TRAIN)} prog={best_prog:.3f}")
    print(f"HELD-OUT tuned    wins={test_wins}/{len(TEST)} prog={test_prog:.3f} fit={test_fit:.3f}")
    print(f"HELD-OUT baseline wins={base_wins}/{len(TEST)} prog={base_prog:.3f} fit={base_fit:.3f}")
    print("weights ->", out)


main()
