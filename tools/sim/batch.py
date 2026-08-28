"""Run many games as isolated subprocesses, in parallel, and summarise."""
import sys, os, json, subprocess, collections, concurrent.futures as cf

S = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(S))
PY_BIN = os.path.join(REPO, '.venv', 'bin', 'python')
# A game takes about 2s. Anything past this is a stuck policy, not a long game.
TIMEOUT_S = 45
if not os.path.exists(PY_BIN):
    PY_BIN = sys.executable


def one(args):
    scen, hero, seed, mode = args
    try:
        p = subprocess.run([PY_BIN, os.path.join(S, 'run_game.py'), scen, hero, str(seed), mode],
                           capture_output=True, text=True, timeout=TIMEOUT_S)
        line = (p.stdout or '').strip().splitlines()
        if not line:
            return {"scenario": scen, "hero": hero, "seed": seed, "mode": mode,
                    "won": False, "reason": f"NO_OUTPUT(rc={p.returncode})", "rounds": -1}
        return json.loads(line[-1])
    except subprocess.TimeoutExpired:
        return {"scenario": scen, "hero": hero, "seed": seed, "mode": mode,
                "won": False, "reason": "TIMEOUT", "rounds": -1}


def run(jobs, workers=8):
    out = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, jobs):
            out.append(r)
    return out


def summarise(rows):
    key = lambda r: (r["scenario"], r["hero"], r["mode"])
    g = collections.defaultdict(list)
    for r in rows:
        g[key(r)].append(r)
    table = []
    for k, v in sorted(g.items()):
        wins = sum(bool(x["won"]) for x in v)
        rounds = [x["rounds"] for x in v if x["rounds"] > 0]
        table.append({
            "scenario": k[0], "hero": k[1], "mode": k[2], "n": len(v), "wins": wins,
            "win_pct": round(100.0 * wins / max(1, len(v)), 1),
            "avg_rounds": round(sum(rounds) / max(1, len(rounds)), 1) if rounds else None,
            "reasons": dict(collections.Counter(x["reason"] for x in v).most_common(5)),
        })
    return table


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    jobs = [(s, h, seed, m)
            for s in cfg["scenarios"] for h in cfg["heroes"]
            for m in cfg["modes"] for seed in cfg["seeds"]]
    rows = run(jobs, cfg.get("workers", 8))
    json.dump(rows, open(os.path.join(S, cfg["out"] + ".raw.json"), "w"))
    tbl = summarise(rows)
    json.dump(tbl, open(os.path.join(S, cfg["out"] + ".json"), "w"), indent=1)
    for t in tbl:
        print(f'{t["scenario"]:22s} {t["hero"]:16s} {t["mode"]:9s} '
              f'{t["wins"]:3d}/{t["n"]:3d} = {t["win_pct"]:5.1f}%  rounds={t["avg_rounds"]}  {t["reasons"]}')
