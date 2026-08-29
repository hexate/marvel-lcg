"""Rollout policy: decide by playing the future out instead of by scoring the present.

STATUS: the forward model works, this does not yet. Cloning a position and playing it to
its own ending is verified and cheap (`clone.py`, about 0.04s a copy). Driving a rollout
from inside a live game is the unfinished half: the clone shares the device manager, so a
rollout answers dozens of prompts through the same object the outer game is blocked on,
and the outer game resumes into a corrupted position. Games that should last five rounds
end in two. Saving and restoring that prompt state deadlocks instead.

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
        manager = Engine.device_manager
        saved_world = session.world
        saved_policy = type(manager).policy
        # The device manager is shared with the clone, and it holds the prompt the outer
        # game is currently blocked on. A rollout answers dozens of its own prompts
        # through the same object, which overwrites that state and leaves the real game
        # resuming into someone else's question.
        saved_ask = dict(getattr(manager, "ask_options", {}) or {})
        saved_asking = list(getattr(manager, "asking_players", []) or [])
        inner = UtilityPolicy(self.mode, self.w)
        inner.fx = _CloneFixture(clone)
        pending = [forced_cmd]

        def rollout_policy(payload, options):
            if pending:
                return pending.pop()
            return inner(payload, options)

        try:
            session.world = clone
            type(manager).policy = staticmethod(rollout_policy)
            clone.OnGameLoop()
            return self.position_value(clone)
        except Exception as e:
            import traceback
            self.last_error = "loop: %s: %s | %s" % (
                type(e).__name__, str(e)[:90], traceback.format_exc()[-220:])
            return None
        finally:
            session.world = saved_world
            type(manager).policy = saved_policy
            # Restoring these here deadlocks the outer game, so it is left out: the
            # remaining isolation problem is written up at the top of this file.
            _ = (saved_ask, saved_asking)

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
