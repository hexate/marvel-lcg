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
import random

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
    """Search over ways of playing the round, not over single actions.

    Forcing one action does not work here: `OnGameLoop` begins a round rather than
    resuming a turn, so the action under test is consumed by whichever prompt comes
    first and every candidate scores the same. Playing the whole rest of the game under
    a different scorer is a question the loop can actually answer.

    So at the first decision of a round, take the current weights and a few perturbations
    of them, play each to the end of the game from this position, and adopt whichever
    finished best for the rest of the round. Because the generator position is restored
    around every rollout, all variants are compared against the identical future, which
    is the common-random-numbers trick and makes small differences readable rather than
    noise.
    """

    def __init__(self, mode="balanced", weights=None, variants=3, every=1,
                 sigma=2.0, villain_hp=29.0, seed=7):
        super().__init__(mode, weights)
        self.variants = variants
        self.every = every
        self.sigma = sigma
        self.villain_hp = villain_hp
        self.rng = random.Random(seed)
        self._searched_round = -1
        self.last_error = None
        self.tel["searched"] = 0
        self.tel["variant_adopted"] = 0
        self.tel["rollouts_ok"] = 0
        self.tel["rollouts_failed"] = 0
        self.spread = []

    # ---------------------------------------------------------------- scoring
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

    def playout(self, weights):
        """Play this position to the end under `weights`. Returns a value, or None."""
        from engine import Engine
        from engine.lib.random import Random
        world = self.world()
        if world is None:
            return None
        try:
            clone = clone_world(world)
        except Exception as e:
            self.last_error = "clone: %s: %s" % (type(e).__name__, str(e)[:100])
            return None

        try:
            clone_manager = clone.controller_manager.device_manager
        except Exception:
            return None
        if clone_manager is None or clone_manager is Engine.device_manager:
            return None

        inner = UtilityPolicy(self.mode, weights)
        inner.fx = _CloneFixture(clone)
        clone_manager.policy = inner

        session = Engine.game.session
        saved_world = session.world
        depth = len(Random.states)
        if _RNG_UNDO:
            Random.PushState()
        try:
            session.world = clone
            clone.OnGameLoop()
            return self.position_value(clone)
        except Exception as e:
            self.last_error = "loop: %s: %s" % (type(e).__name__, str(e)[:100])
            return None
        finally:
            session.world = saved_world
            if _RNG_UNDO:
                while len(Random.states) > depth + 1:
                    Random.states.pop()
                if len(Random.states) > depth:
                    Random.Undo()

    def perturb(self):
        cand = dict(self.w)
        for k in self.rng.sample(sorted(cand), self.rng.randint(2, 5)):
            cand[k] = round(cand[k] + self.rng.gauss(0, self.sigma), 2)
        return cand

    # ------------------------------------------------------------------ turn
    def turn_inner(self, options):
        world = self.world()
        rnd = getattr(world, "round_id", -1) if world is not None else -1
        if world is None or rnd == self._searched_round or rnd % self.every:
            return super().turn_inner(options)
        self._searched_round = rnd

        self.tel["searched"] += 1
        best_w, best_v = self.w, self.playout(self.w)
        if best_v is None:
            self.tel["rollouts_failed"] += 1
            return super().turn_inner(options)
        self.tel["rollouts_ok"] += 1
        self.spread.append(round(best_v, 3))

        for _ in range(max(0, self.variants - 1)):
            cand = self.perturb()
            v = self.playout(cand)
            if v is None:
                self.tel["rollouts_failed"] += 1
                continue
            self.tel["rollouts_ok"] += 1
            self.spread.append(round(v, 3))
            if v > best_v:
                best_v, best_w = v, cand
        if best_w is not self.w:
            self.w = best_w
            self.tel["variant_adopted"] += 1
        return super().turn_inner(options)
