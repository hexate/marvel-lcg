"""Search over turns, not over moves or over policies.

Two earlier searches are in the repository and both are bounded, for reasons that are measured
rather than argued.

`search.py` searches over *policies*: perturb the weights, play the rest of the game, keep what
finished best. It works, worth about +5 damage a game, and it plateaus. Measured: hand-written
coherent turn plans match random gaussian noise at the same candidate count, so it is sampling
rather than reasoning, and every knob is already at its optimum.

Searching over *moves* looked like the answer and is not. Once `World.ResumeGameLoop` made it
possible at all, evaluating every option at six consecutive decisions gave one distinct outcome
at five of them. The continuation is order-invariant: force any action first and the scorer still
plays the same set for the rest of the turn, so the forced choice is reordered, not changed.

What discriminates is committing to a whole turn, because that is the first unit that can say
what it will *not* do. At the same decision where move-level search found 1 distinct outcome
among 4 options, turn commitment found 5 among 10 candidates, and one of them reached 29 damage,
a win, where the scorer reached 17.
"""
import itertools

from clone import clone_world, install, rollout_isolation
from policy import _command
from utility import UtilityPolicy

install()

MAX_PAIRS = 5


def _enable_rng_undo():
    try:
        from engine.lib.random import ENABLE_RANDOM_UNDO
        ENABLE_RANDOM_UNDO.value = True
        return True
    except Exception:
        return False


_RNG_UNDO = _enable_rng_undo()


class _CloneFixture:
    def __init__(self, world):
        self.world = world
        self.game = self

    def player(self, index=0):
        return self.world.const_players[index]


class TurnScript(UtilityPolicy):
    """Take exactly these actions this turn, then end it. Play normally from the next turn on.

    The refusal is the point. A script that runs out ends the turn rather than handing the rest
    back to the scorer, because letting the scorer finish is what made every candidate collapse
    to the same game.
    """

    def __init__(self, mode, weights, script):
        super().__init__(mode, weights)
        self.script = list(script)
        self.i = 0
        self.spent = False
        self.taken = 0

    def turn(self, options):
        if self.spent:
            return super().turn(options)
        while self.i < len(self.script):
            want = self.script[self.i]
            self.i += 1
            for o in options:
                if (str(o.get("name")), o.get("bind_id")) == want:
                    self.taken += 1
                    return self.take(o, self.hand())
        self.spent = True
        return _command("0")


class _TurnRecorder(UtilityPolicy):
    """Play normally, remembering the actions taken before the first end-turn."""

    def __init__(self, mode, weights):
        super().__init__(mode, weights)
        self.turn_actions = []
        self._closed = False

    def turn(self, options):
        r = super().turn(options)
        if not self._closed:
            try:
                import json as _json
                cid = str(_json.loads(r).get("id"))
            except Exception:
                cid = None
            if cid == "0":
                self._closed = True
            else:
                for o in options:
                    if str(o.get("id")) == cid:
                        self.turn_actions.append((str(o.get("name")), o.get("bind_id")))
                        break
        return r


class CycleScript(UtilityPolicy):
    """Go down to alter-ego, heal, come back up, then play normally.

    The one plan the scorer provably cannot represent. It spans turns, and a policy that ranks
    single actions can only ever price the first step of it: flipping down scores badly on its own
    because the payoff arrives two turns later. Measured, that is exactly what happens. `flip_ae`
    tunes to -16.29 on `ant_man_multiple_man_protection` and the bot flips 0 times in 92 offers,
    and when flipping is forced anyway it strands itself, 4.83 of 5.9 rounds in alter-ego with
    `ae_action` at 0.00, because coming back up is priced as a lateral form switch.

    As a script the whole cycle is one decision, which the rollout can accept or reject on what it
    is worth at the end of the game rather than at the end of the turn.
    """

    def __init__(self, mode, weights, target_hp=0.85):
        super().__init__(mode, weights)
        self.target_hp = target_hp
        self.stage = "down"
        self.aborted = False

    def turn(self, options):
        if self.stage == "down":
            if not self.is_ae():
                for o in options:
                    if self.option_form(str(o.get("name"))) == "ae":
                        return self.take(o, self.hand())
                # nothing on offer takes us down; give up on the plan rather than stall
                self.stage = "done"
                self.aborted = True
            else:
                self.stage = "heal"

        if self.stage == "heal":
            if self.hp_frac() < self.target_hp:
                for o in options:
                    if str(o.get("name")) == "Recover":
                        return self.take(o, self.hand())
                return _command("0")      # nothing else to do down here; take the next turn
            self.stage = "up"

        if self.stage == "up":
            for o in options:
                if self.option_form(str(o.get("name"))) in ("giant", "tiny"):
                    self.stage = "done"
                    return self.take(o, self.hand())
            self.stage = "done"

        return super().turn(options)


class CyclingPolicy(UtilityPolicy):
    """Greedy, but takes the alter-ego cycle when hurt and safe. No nested search.

    This exists to be a *rollout* policy. A search estimates a position by what its rollout policy
    achieves from there, so a greedy rollout makes every position needing setup look worthless,
    and the search inherits the myopia it was meant to fix. That is the ceiling behind the plateau:
    the estimator is biased, not noisy.

    Deliberately heuristic rather than the planner. `TurnPlanPolicy` inside a rollout would recurse
    into its own rollouts and cost exponentially, so the trigger is a rule instead of a search.
    """

    def __init__(self, mode="balanced", weights=None, hp_trigger=0.55, target_hp=0.85):
        super().__init__(mode, weights)
        self.hp_trigger = hp_trigger
        self.target_hp = target_hp
        self.runner = None

    def turn(self, options):
        if self.runner is not None:
            if self.runner.stage == "done":
                self.runner = None
            else:
                return self.runner.turn(options)
        try:
            hurt_enough = self.hp_frac() < self.hp_trigger
            safe = not self.minions() and self.threat_pressure() < 0.5
        except Exception:
            hurt_enough = safe = False
        if hurt_enough and safe and not self.is_ae():
            self.runner = CycleScript(self.mode, self.w, self.target_hp)
            self.runner.fx = self.fx
            return self.runner.turn(options)
        return super().turn(options)


class TurnPlanPolicy(UtilityPolicy):
    """At the first decision of each turn, pick the turn to play by playing each candidate out."""

    def __init__(self, mode="balanced", weights=None, width=6, pairs=MAX_PAIRS,
                 villain_hp=29.0, steps=3, cycle=True):
        super().__init__(mode, weights)
        self.width = width
        self.pairs = pairs
        self.steps = max(1, steps)
        self.cycle = cycle
        self.villain_hp = villain_hp
        self._planned_round = -1
        self._script = None
        self._cycle = False
        self._runner = None
        self._cursor = 0
        self._spent = False
        self.last_error = None
        self.tel["planned"] = 0
        self.tel["plan_rollouts"] = 0
        self.tel["plan_failed"] = 0
        self.tel["plan_committed"] = 0
        self.tel["cycle_committed"] = 0

    # -------------------------------------------------------------- evaluation
    def position_value(self, world):
        try:
            if getattr(world.game_over, "players_won", None) is True:
                return 2.0
        except Exception:
            pass
        try:
            vs = world.scenario.area_villain.Get()
            stage = vs[0].paper.card_id if vs else ""
            dmg = sum(f.GetLostHealth() for f in vs)
            if stage.endswith("5"):
                dmg += 14
            return min(1.0, dmg / self.villain_hp)
        except Exception:
            return 0.0

    def _rollout(self, world, script, record=False):
        from engine import Engine
        from engine.lib.random import Random

        guard = rollout_isolation(world)
        guard.__enter__()
        depth = len(Random.states)
        if _RNG_UNDO:
            Random.PushState()
        try:
            clone = clone_world(world)
            manager = clone.controller_manager.device_manager
            if manager is None or manager is Engine.device_manager:
                return (None, None) if record else None
            if script is None:
                inner = _TurnRecorder(self.mode, self.w) if record else UtilityPolicy(self.mode, self.w)
            elif script == "CYCLE":
                inner = CycleScript(self.mode, self.w)
            else:
                inner = TurnScript(self.mode, self.w, script)
            inner.fx = _CloneFixture(clone)
            manager.policy = inner

            session = Engine.game.session
            saved_world = session.world
            try:
                session.world = clone
                clone.ResumeGameLoop()
                value = self.position_value(clone)
                return (value, getattr(inner, "turn_actions", None)) if record else value
            finally:
                session.world = saved_world
        except Exception as e:
            self.last_error = "%s: %s" % (type(e).__name__, str(e)[:90])
            return (None, None) if record else None
        finally:
            guard.__exit__(None, None, None)
            if _RNG_UNDO:
                while len(Random.states) > depth + 1:
                    Random.states.pop()
                if len(Random.states) > depth:
                    Random.Undo()

    def _candidates(self, options, natural):
        """Turns one action away from the one the scorer plays for itself.

        Truncating to one or two actions and ending was the first attempt and it is far less
        than a real turn, so it lost to the scorer more often than it beat it. What the probe
        actually showed is that candidates differ when they *refuse* something, so the useful
        neighbourhood is the scorer's own turn with one action dropped, or one it declined added.
        """
        offered = [(str(o.get("name")), o.get("bind_id")) for o in options[:self.width]]
        out = []
        if natural:
            for i in range(len(natural)):
                out.append(natural[:i] + natural[i + 1:])
        for a in offered:
            if a not in natural:
                out.append(list(natural) + [a])
        out.append([])
        seen, uniq = set(), []
        for c in out:
            k = tuple(c)
            if k not in seen:
                seen.add(k)
                uniq.append(c)
        return uniq[:self.width + self.pairs + 2]

    # ------------------------------------------------------------------ turn
    def turn(self, options):
        world = self.world()
        rnd = getattr(world, "round_id", -1) if world is not None else -1

        if (world is not None and rnd != self._planned_round and len(options) >= 2
                and self._runner is None):
            self._planned_round = rnd
            self._script = None
            self._cursor = 0
            self._spent = False
            self.tel["planned"] += 1

            # The baseline is what the scorer achieves playing the turn its own way, not the
            # value of the position as it stands. Comparing against a static number made every
            # turn commit to one or two actions and end, which is far less than the scorer plays
            # and is strictly worse.
            best_v, natural = self._rollout(world, None, record=True)
            best = None
            if best_v is None:
                best_v = self.position_value(world)
            else:
                self.tel["plan_rollouts"] += 1

            # Hill-climb the turn. One pass over the plus-or-minus-one neighbourhood is a single
            # step; re-searching from whatever it found lets a turn move several actions away
            # from the one the scorer would have played, which one pass cannot reach.
            # The alter-ego cycle, offered as one candidate. It is not a list of this turn's
            # actions like the others, so it is evaluated separately and adopted by setting a
            # policy rather than a script.
            self._cycle = False
            if self.cycle:
                v = self._rollout(world, "CYCLE")
                if v is not None:
                    self.tel["plan_rollouts"] += 1
                    if v > best_v:
                        best_v, best, self._cycle = v, None, True
                else:
                    self.tel["plan_failed"] += 1

            current = list(natural or [])
            for _ in range(self.steps):
                improved = False
                for script in self._candidates(options, current):
                    v = self._rollout(world, script)
                    if v is None:
                        self.tel["plan_failed"] += 1
                        continue
                    self.tel["plan_rollouts"] += 1
                    if v > best_v:
                        best_v, best = v, script
                        improved = True
                if not improved:
                    break
                current = list(best)
            if self._cycle:
                self._runner = CycleScript(self.mode, self.w)
                self._runner.fx = self.fx
                self.tel["cycle_committed"] += 1
            elif best:
                self._script = best
                self.tel["plan_committed"] += 1

        if self._runner is not None:
            if self._runner.stage == "done":
                self._runner = None
            else:
                return self._runner.turn(options)

        if self._script is not None and not self._spent:
            while self._cursor < len(self._script):
                want = self._script[self._cursor]
                self._cursor += 1
                for o in options:
                    if (str(o.get("name")), o.get("bind_id")) == want:
                        return self.take(o, self.hand())
            self._spent = True
            return _command("0")

        return super().turn(options)
