"""Play exactly one game and print a JSON result line. One game per process, on purpose:
a policy bug then kills that game only, and no state leaks between games."""
import sys, os, io, json, contextlib, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO)
os.chdir(REPO)

import engine  # noqa: F401
from engine import Engine

# `Engine.SaveCrash` hardcodes './crash.json' (engine/engine.py:184) and then exit(-1).
# Both are wrong for a batch run: it clobbers the user's crash repro and kills the process.
Engine.SaveCrash = staticmethod(lambda: None)

from unit_test.harness import GameFixture, decline_or_first
from policy import Heuristic
from utility import UtilityPolicy, load_weights


def main():
    scen, hero, seed, mode = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    out = {"scenario": scen, "hero": hero, "seed": seed, "mode": mode,
           "won": False, "reason": "NO_RESULT", "rounds": -1, "err": None}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            if mode == "nothing":
                pol, holder = decline_or_first, None
            elif mode.startswith("search"):
                # "search:<weights.json>[:<candidates>:<rollouts>]"
                from search import RolloutPolicy
                parts = mode.split(":")
                wpath = parts[1] if len(parts) > 1 and parts[1] else None
                variants = int(parts[2]) if len(parts) > 2 else 3
                every = int(parts[3]) if len(parts) > 3 else 1
                rp = parts[4] if len(parts) > 4 else "greedy"
                pol = RolloutPolicy("balanced", load_weights(wpath),
                                    variants=variants, every=every,
                                    rollout_policy=rp); holder = pol
            elif mode.startswith("turnplan"):
                # "turnplan:<weights.json>[:<width>:<pairs>]"
                from turnplan import TurnPlanPolicy
                parts = mode.split(":")
                wpath = parts[1] if len(parts) > 1 and parts[1] else None
                width = int(parts[2]) if len(parts) > 2 else 6
                pairs = int(parts[3]) if len(parts) > 3 else 5
                steps = int(parts[4]) if len(parts) > 4 else 3
                cycle = (parts[5] != "0") if len(parts) > 5 else True
                pol = TurnPlanPolicy("balanced", load_weights(wpath),
                                     width=width, pairs=pairs, steps=steps,
                                     cycle=cycle); holder = pol
            elif mode.startswith("util"):
                # "util" or "util:<weights.json>[:<base mode>]"
                parts = mode.split(":")
                wpath = parts[1] if len(parts) > 1 and parts[1] else None
                base = parts[2] if len(parts) > 2 else "balanced"
                pol = UtilityPolicy(base, load_weights(wpath)); holder = pol
            else:
                pol = Heuristic(mode); holder = pol
            fixture = GameFixture(scen, [hero], seed=seed, policy=pol)
            if holder is not None:
                holder.fx = fixture
            with fixture as fx:
                fx.game.GameLoop()
                w = fx.world
                won = getattr(w.game_over, "players_won", None)
                out.update(won=bool(won) if won is not None else False,
                           reason=str(getattr(w.game_over, "reason", None)) if won is not None
                                  else "ENDED_WITHOUT_OUTCOME:" + str(getattr(w.game_over, "reason", None)),
                           rounds=int(w.round_id))
                if holder is not None:
                    out["steps"] = holder.steps
                    out["policy_errors"] = holder.errors
                    out["tel"] = holder.tel
                    out["first_error"] = holder.first_error
                    out["stalls"] = holder.stalls
                    if hasattr(holder, "last_error"):
                        out["rollout_error"] = holder.last_error
                    if hasattr(holder, "spread"):
                        out["rollout_values"] = holder.spread[:24]
                    try:
                        vs = w.scenario.area_villain.Get()
                        out["villain_stage"] = [f.paper.card_id for f in vs]
                        out["villain_dmg"] = sum(f.GetLostHealth() for f in vs)
                        out["villain_hp"] = sum(f.health for f in vs)
                        st = out["villain_stage"][0] if out["villain_stage"] else ""
                        out["total_villain_dmg"] = out["villain_dmg"] + (14 if st == "01095" else 0)
                    except Exception:
                        pass
                    out["end_threat"] = getattr(holder.main(), "threat", None)
                    out["end_hp"] = round(holder.hp_frac(), 2)
    except BaseException as e:
        out["err"] = f"{type(e).__name__}: {e}"[:200]
        out["trace"] = traceback.format_exc()[-400:]
    sys.__stdout__.write(json.dumps(out) + "\n")
    sys.__stdout__.flush()
    os._exit(0)


main()
