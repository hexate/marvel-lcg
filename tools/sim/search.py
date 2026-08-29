"""Rollout policy: decide by playing the future out instead of by scoring the present.

STATUS: the forward model is finished and correct. Action-level search on top of it is
blocked on one thing, described below.

What works, and is verified rather than assumed. A position clones in about 0.04s. The
clone has its own controller manager and its own device manager, so a rollout answers its
own prompts and never touches the prompt the outer game is blocked on. The global
generator position is recorded and restored around each rollout, so a rollout no longer
consumes the real game's draws. The check that matters: running with one candidate, so
the search evaluates only the action the scoring policy would have taken anyway,
reproduces the greedy game exactly, six rounds and the same ending. Before the generator
fix the same test ran seven rounds, which is what a leak looks like.

What blocks it. `World.OnGameLoop` is `while not is_game_over: game_round()`. It begins a
round; it does not resume a turn that is already in progress. A clone taken mid-decision
therefore replays from the round boundary, and the action being tested is consumed by
whichever prompt happens to come first, so every candidate returns the same value: 0.483
for all 24 rollouts in one measured game. The search runs, costs about 5s a game, and
discriminates nothing.

Two ways forward, neither attempted. Re-enter the phase machinery at the point the clone
was taken, which needs an entry point the engine does not currently expose. Or give up on
forcing a single action and search over policies instead, playing the rest of the round
under a varied scorer and keeping the variant that finishes better, which fits the
existing loop as it stands.

The fix is to give the rollout its own `ScriptedDeviceManager` and point the cloned
controllers at it, rather than sharing one and trying to undo the damage afterwards.
Until then this is not usable, and `search:` mode is here to be finished rather than run.

Everything before this scored one action at a time against hand-written features. That
was measured against a frontier it could not cross: nine strategy levers, the combo the
guides describe, and a whole Protection deck all traded rounds against damage per round
and left total output flat, because a greedy scorer cannot give up damage now for a
board that pays later.

Search does not need to be told that a board compounds. It plays the position out and
counts what happened. It needs a forward model, which `clone.py` now provides at about
0.04s a copy.

Cost control matters. A rollout is roughly 0.1s, so evaluating every candidate at every
prompt would be minutes per game. Instead only the first decision of each round is
searched, since that is where the shape of the turn is set, and only the top few
candidates by utility score are tried. Everything else falls through to the scoring
policy, which is also what plays out the rollouts.
"""
import copy
import json

from clone import clone_world, install
from utility import UtilityPolicy

install()


def _enable_rng_undo():
    """`Random.PushState` is a no-op unless `enable_random_undo` is configured, and
    `Undo` asserts on it, so recording the generator position silently did nothing and
    a rollout kept consuming the real game's draws. It is off by default because it
    copies the Mersenne buffer on every draw; a rollout policy is exactly the case that
    wants it."""
    try:
        from engine.lib.random import ENABLE_RANDOM_UNDO
        ENABLE_RANDOM_UNDO.value = True
        return True
    except Exception:
        return False


_RNG_UNDO = _enable_rng_undo()


class _CloneFixture:
    """Enough of a GameFixture for a policy to read state off a cloned world."""

    def __init__(self, world):
        self.world = world
        self.game = self          # only truthiness is used

    def player(self, index=0):
        return self.world.const_players[index]


class RolloutPolicy(UtilityPolicy):

    def __init__(self, mode="balanced", weights=None, candidates=3, rollouts=2,
                 per_round=True, villain_hp=29.0):
        super().__init__(mode, weights)
        self.candidates = candidates
        self.rollouts = rollouts
        self.per_round = per_round
        self.villain_hp = villain_hp
        self._searched_round = -1
        self.tel["searched"] = 0
        self.tel["search_changed_pick"] = 0
        self.tel["rollouts_ok"] = 0
        self.tel["rollouts_failed"] = 0
        self.spread = []
        self.last_error = None

    # ---------------------------------------------------------------- scoring
    def position_value(self, world):
        """How good did that turn out. A win is worth more than any amount of progress."""
        try:
            if getattr(world.game_over, "players_won", None) is True:
                return 2.0
        except Exception:
            pass
        try:
            vs = world.scenario.area_villain.Get()
            stage = vs[0].paper.card_id if vs else ""
            dmg = sum(f.GetLostHealth() for f in vs)
            if stage.endswith("5"):        # second stage of a two-stage villain
                dmg += 14
            return min(1.0, dmg / self.villain_hp)
        except Exception:
            return 0.0

    def rollout(self, forced_cmd):
        """Clone, force one action, play the rest with the scoring policy, return value."""
        from engine import Engine
        world = self.world()
        if world is None:
            return None
        try:
            clone = clone_world(world)
        except Exception as e:
            self.last_error = "clone: %s: %s" % (type(e).__name__, str(e)[:110])
            return None

        session = Engine.game.session
        saved_world = session.world

        inner = UtilityPolicy(self.mode, self.w)
        inner.fx = _CloneFixture(clone)
        pending = [forced_cmd]

        def rollout_policy(payload, options):
            if pending:
                return pending.pop()
            return inner(payload, options)

        # The clone has its own device manager now, so the rollout answers its own
        # prompts on its own object. Setting the policy on that instance shadows the
        # class attribute, which means the outer game's pending prompt is never touched.
        # Sharing one manager and repairing it afterwards corrupted the game one way and
        # deadlocked it the other.
        try:
            clone_manager = clone.controller_manager.device_manager
        except Exception:
            clone_manager = None
        if clone_manager is None or clone_manager is Engine.device_manager:
            return None
        clone_manager.policy = rollout_policy

        # The generator is global. A rollout draws its own encounter cards and boost
        # cards from it, which advances the position the real game will draw from, so
        # even a rollout that changes no decision changed the game: identical play ran
        # seven rounds instead of six. `Random.PushState` records the position and
        # `Undo` restores it.
        from engine.lib.random import Random
        depth = len(Random.states)
        Random.PushState()
        try:
            session.world = clone
            clone.OnGameLoop()
            return self.position_value(clone)
        except Exception as e:
            import traceback
            self.last_error = "loop: %s: %s | %s" % (
                type(e).__name__, str(e)[:90], traceback.format_exc()[-220:])
            return None
        finally:
            session.world = saved_world
            if _RNG_UNDO:
                while len(Random.states) > depth + 1:
                    Random.states.pop()        # drop what the rollout pushed
                if len(Random.states) > depth:
                    Random.Undo()              # restore the position we recorded

    # ------------------------------------------------------------------ turn
    def turn_inner(self, options):
        world = self.world()
        rnd = getattr(world, "round_id", -1) if world is not None else -1
        if self.per_round and rnd == self._searched_round:
            return super().turn_inner(options)
        if world is None or len(options) < 2:
            return super().turn_inner(options)
        self._searched_round = rnd

        hand = self.hand()
        ctx = self.context()
        ranked = sorted((self.score_option(o, hand, ctx) + (o,) for o in options),
                        key=lambda x: -x[0])[:self.candidates]
        greedy_cmd = super().turn_inner(options)

        best_cmd, best_val = greedy_cmd, None
        self.tel["searched"] += 1
        for _score, _kind, o in ranked:
            cmd = self.command_for(o, hand)
            raw = [self.rollout(cmd) for _ in range(self.rollouts)]
            vals = [v for v in raw if v is not None]
            self.tel["rollouts_ok"] += len(vals)
            self.tel["rollouts_failed"] += len(raw) - len(vals)
            if not vals:
                continue
            val = sum(vals) / len(vals)
            self.spread.append(round(val, 3))
            if best_val is None or val > best_val:
                best_val, best_cmd = val, cmd
        if best_val is not None and best_cmd != greedy_cmd:
            self.tel["search_changed_pick"] += 1
        return best_cmd

    def command_for(self, o, hand):
        """The command this option would produce, without executing it."""
        kind = self.score_option(o, hand, self.context())[1]
        if kind == "attack":
            return self.aimed(o, hand, self.enemies(), ("villain", "minion"))
        if kind == "attack_minion":
            return self.aimed(o, hand, self.enemies(), ("minion", "villain"))
        if kind == "thwart":
            return self.aimed(o, hand, self.schemes(), ("main", "side"))
        return self.take(o, hand)
