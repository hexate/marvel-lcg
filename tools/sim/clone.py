"""Make a game position copyable, which is what search needs and the engine does not offer.

`copy.deepcopy(world)` raises `cannot pickle '_thread.RLock'`, and the engine's undo is
not a rollback: `game_session.Undo` replays the game from the start. So there was no way
to ask "what happens if I do this" except by replaying a whole game, at about 0.91s.

The cause is not that game state holds a lock. It is that every game object carries a
back-reference to the engine, so a deep copy walks card -> player -> controller ->
controller manager -> device manager and tries to clone the device plumbing too. Four
`threading.Condition` objects live on that side, three on `SynchronizationNotifier` and
one on `GameState`, and they are what refuses to copy.

The fix is to stop the copy at that boundary. A cloned position wants its own cards and
its own board; it emphatically does not want its own device manager. Declaring those
classes shared makes them copy as themselves, so the walk stops and the game state
copies cleanly.

Measured: a mid-game clone takes about 0.05s and can be played to its own ending in
about 0.04s the first time, leaving the original untouched. Later clones in the same game are
not cheap: see J40, the graph a rollout leaves behind is copied by every clone after it. That
is roughly ten times cheaper than the
replay it replaces, and unlike the replay it is a real forward model.

This is deliberately a shim rather than an engine change. Nothing in the game calls
`deepcopy` on these classes today, so `install()` only affects code that asks for it.
The engine-side version of this is tracked as N21.
"""
import contextlib
import copy
import sys

_INSTALLED = False

# The position is a deep graph of effects and card faces, and `deepcopy` recurses once
# per level. The default limit of 1000 clears an opening position and then starts
# failing a few rounds in, once effect chains have built up, which showed up as 28
# rollouts in 30 returning nothing.
_RECURSION = 60000

# Anything the copiers below could not copy and had to share instead. Sharing is how a
# rollout corrupts the game it is predicting, so it must never be silent: J41 hid for as
# long as it did precisely because the fallback swallowed the reason. Callers can assert
# this is empty after a clone.
SHARE_FAILURES = []


def _fresh_sync(v):
    """A fresh synchronisation object of `v`'s kind, or None if `v` is not one.

    `GameState.condition` is `engine.task.condition.Condition`, which merely *wraps* a
    `threading.Condition`. The original check tested `isinstance(v, type(threading.Condition()))`,
    which never matched it, so the isolation below never once ran and `GameState` was
    shared with every rollout. See J41.
    """
    import threading
    if isinstance(v, (threading.Condition, type(threading.RLock()), type(threading.Lock()))):
        return threading.Condition()
    try:
        from engine.task.condition import Condition as EngineCondition
    except Exception:
        return None
    if isinstance(v, EngineCondition):
        return type(v)(getattr(v, "name", "State"))
    return None


def _shared_classes():
    """Device plumbing only. A clone should not get its own notifier: it notifies nobody,
    and the notifier owns three of the four Conditions that refuse to copy."""
    out = []
    for mod, name in (("engine.device.manager.notifier", "SynchronizationNotifier"),):
        try:
            out.append(getattr(__import__(mod, fromlist=[name]), name))
        except Exception:
            pass
    return out


def _best_effort_copy(cls):
    """Copy what can be copied, share what cannot.

    The engine boundary classes hold a mixture: mutable round and step state that a
    rollout must have its own of, and plumbing that refuses to copy at all. The refusal
    is not always reachable through attributes either, since a bound method drags its
    own object along, which is why hunting for the lock by walking `__dict__` found
    nothing while the copy still failed.

    So copy per attribute and fall back to sharing the ones that raise. The rollout gets
    its own counters and phase state, which is what it corrupts otherwise, and shares the
    parts it only ever reads through.
    """
    # `getattr` here would see the flag inherited from a base that was done first, so a
    # subclass would silently reuse the base's copier and come back as the wrong class.
    if cls.__dict__.get("_sim_besteffort"):
        return

    def __deepcopy__(self, memo):
        # type(self), not the captured class: a subclass inheriting this must copy as
        # itself, or a ScriptedDeviceManager clones into a plain DeviceManager.
        cls_ = type(self)
        new = cls_.__new__(cls_)
        memo[id(self)] = new
        for k, v in self.__dict__.items():
            try:
                new.__dict__[k] = copy.deepcopy(v, memo)
            except Exception as e:
                SHARE_FAILURES.append((cls_.__name__, k, type(v).__name__,
                                       "%s: %s" % (type(e).__name__, str(e)[:80])))
                new.__dict__[k] = v
        return new

    cls.__deepcopy__ = __deepcopy__
    cls._sim_besteffort = True


def _isolate_gamestate():
    """`GameState` must be copied, not shared: a rollout advances phase and step state,
    and sharing it let the rollout corrupt the game it was supposed to be predicting.
    Sharing everything reachable was the quick way to make the copy succeed and the wrong
    way to make it correct. Copy it, and give the copy its own Condition."""
    try:
        from game.game_run.game_state import GameState
    except Exception:
        return
    if getattr(GameState, "_sim_isolated", False):
        return

    def __deepcopy__(self, memo):
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        for k, v in self.__dict__.items():
            fresh = _fresh_sync(v)
            if fresh is not None:
                new.__dict__[k] = fresh
                continue
            try:
                new.__dict__[k] = copy.deepcopy(v, memo)
            except Exception as e:
                SHARE_FAILURES.append(("GameState", k, type(v).__name__,
                                       "%s: %s" % (type(e).__name__, str(e)[:80])))
                new.__dict__[k] = v
        return new

    GameState.__deepcopy__ = __deepcopy__
    GameState._sim_isolated = True


def install():
    """Idempotent. Returns the classes that were made shareable."""
    global _INSTALLED
    classes = _shared_classes()
    if not _INSTALLED:
        for cls in classes:
            cls.__deepcopy__ = (lambda self, memo: self)
        _isolate_gamestate()
        for mod, name in (("engine.device.manager.base", "DeviceManager"),
                          ("unit_test.harness", "ScriptedDeviceManager"),
                          ("engine.controller.manager", "ControllerManager"),
                          ("engine.controller.controller", "Controller"),
                          ("game.game", "Game"),
                          ("game.game_run.game_session", "GameSession")):
            try:
                _best_effort_copy(getattr(__import__(mod, fromlist=[name]), name))
            except Exception:
                pass
        _INSTALLED = True
    return [c.__name__ for c in classes]


def _position_objects(root):
    """Game-layer objects the rollout can reach and mutate, from every root that has one.

    Scoped to `game.` and no wider. Restoring `engine.` state as well put back
    `replay_inputs` mid-game and failed as `IndexError` in `GetReplayOperation`, and the
    device plumbing is shared with the clone on purpose.

    Scoping it *narrower* than `game.` was the mistake that cost the most time here. Limiting
    the sweep to `game.ability` fixed the cost functions and left the curve climbing, because
    the next thing to accumulate was `FailureReason.reasons` in `game.effect.effect_failure`:
    eight entries per rollout, each dragging a whole rollout graph, which is the +42,000
    copied objects per rollout that the memo count showed.
    """
    import gc
    roots = [root]
    # The position is not the only root. Abilities are built once per card and kept in
    # `CardsDB.ability_cache`, and some of their cost functions are not reachable from the
    # current world at all: measured, 3 of the 5 `CostFunc.Discard` instances in the cache were
    # world-reachable and 2 were not. The rollout still shares and mutates those two, and a walk
    # that starts only at the world never restores them, which left variants=1 disagreeing with
    # greedy on 8 of 20 seeds when it should reproduce it exactly.
    try:
        from cards.database import CardsDB
        roots.append(CardsDB.ability_cache)
    except Exception:
        pass
    seen, out, stack = set(), [], list(roots)
    while stack:
        o = stack.pop()
        i = id(o)
        if i in seen:
            continue
        seen.add(i)
        if isinstance(o, type):
            continue
        mod = getattr(type(o), "__module__", "") or ""
        if mod.startswith("game.") and getattr(o, "__dict__", None):
            out.append(o)
        stack.extend(gc.get_referents(o))
    return out


def _nested_containers(value, depth, out, seen):
    """Every container inside `value`, down to `depth`.

    A shallow snapshot of an object's own attributes is not enough. Keywords live two levels
    down: `GainKeyword` stores `self.keywords[keyword][face] = diff` (`card_face.py:231`), so
    restoring the outer `keywords` dict puts back the same inner dict the rollout mutated. That
    is what left Captain America's Shield without its Retaliate after a rollout, and the missing
    "deal 1 damage to Rhino" is exactly where a variants=1 game first diverges from the scorer's.
    """
    if depth < 0:
        return
    i = id(value)
    if i in seen:
        return
    if isinstance(value, dict):
        seen.add(i)
        out.append(value)
        for k, v in list(value.items()):
            _nested_containers(k, depth - 1, out, seen)
            _nested_containers(v, depth - 1, out, seen)
    elif isinstance(value, (list, set)):
        seen.add(i)
        out.append(value)
        for v in list(value):
            _nested_containers(v, depth - 1, out, seen)


@contextlib.contextmanager
def rollout_isolation(world):
    """Leave the live position exactly as the rollout found it.

    A rollout must not change the live position at all, and the engine gives it many ways to
    try. Cost functions keep per-call state and are shared with the clone
    (`CostFunc.Discard.__init__` sets `return_original_area: Dict[CardFace, Deck]`, rewritten
    by `on_call`, `game/ability/cost_func.py:689`). Worse, a live `Effect`'s `EffectContext`
    picks up a message the rollout created, and messages carry a `world` back-reference, so a
    single stale attribute drags the clone's entire position into the live graph. Measured: a
    rollout added 228,410 newly-reachable objects to the live world that way.

    That is why this restores whole `__dict__`s rather than just the mutable containers. The
    container-only version fixed the cost functions and left the curve climbing, because the
    reference that mattered was a plain attribute. Scope stays at `game.`: restoring `engine.`
    state as well put back `replay_inputs` mid-game and failed as `IndexError` in
    `GetReplayOperation`, and the device plumbing is shared with the clone deliberately.

    Safe because the live game does not run while a rollout does, so the only writer during
    the window is the rollout itself.
    """
    targets = list(_position_objects(world))

    # The live controller modules as well, and only these. A rollout does not own them and does
    # not share them (measured: the clone gets its own `ControllerManager`, `replay`, `undo`,
    # `skip`, controllers and device manager), but something in the clone's game-over handling
    # reaches the global `Engine.game` and resets them: after one rollout the live `InputModule`
    # came back with `current_step_id` and `replay_step_id` at 0 and `history_inputs` emptied,
    # and `UndoModule.next_step` at 0. That is what made variants=1 disagree with greedy on 8 of
    # 20 seeds when it performs no perturbation and should reproduce it exactly.
    #
    # Named explicitly rather than swept: restoring `engine.` state through a wide walk put back
    # `replay_inputs` at a moment the step ids had moved past it, and failed as `IndexError` in
    # `GetReplayOperation`.
    try:
        from engine import Engine
        cm = Engine.game.controller_manager
        targets.append(cm)
        for attr in ("replay", "undo", "skip"):
            m = getattr(cm, attr, None)
            if m is not None and getattr(m, "__dict__", None):
                targets.append(m)
    except Exception:
        pass

    # The ability cache is keyed by card id and hands back shared `Ability` objects. A rollout
    # plays cards the live game has not reached yet, which builds and caches their abilities
    # (measured: 57 entries to 58 across one rollout). The live game then reuses objects that
    # were constructed inside the rollout, and that is what made variants=1 diverge from greedy
    # while every other piece of state came back identical. Evict what the rollout added so the
    # live game builds its own.
    cache = None
    cache_keys = ()
    try:
        from cards.database import CardsDB
        cache = CardsDB.ability_cache
        cache_keys = frozenset(cache)
    except Exception:
        cache = None

    saved = []
    for o in targets:
        d = o.__dict__
        # Both halves are needed. Restoring only the containers leaves a rebound attribute
        # pointing at the rollout (a live `EffectContext` holding a clone message, which drags
        # the clone's whole `World` in behind it). Restoring only `__dict__` leaves in-place
        # mutation intact, because the copy is shallow and hands back the same list.
        found, seen_c = [], set()
        for v in d.values():
            _nested_containers(v, 3, found, seen_c)
        conts = [(c, copy.copy(c)) for c in found]
        saved.append((o, d.copy(), conts))
    try:
        yield
    finally:
        if cache is not None:
            for k in [k for k in cache if k not in cache_keys]:
                cache.pop(k, None)
        for o, binds, conts in saved:
            try:
                o.__dict__.clear()
                o.__dict__.update(binds)
                # In place, not by rebinding: other live objects may hold the same container.
                for c, snap in conts:
                    if isinstance(c, list):
                        c[:] = snap
                    else:
                        c.clear()
                        c.update(snap)
            except Exception:
                pass


def clone_world(world):
    """A copy of the position that can be played without touching the original."""
    install()
    previous = sys.getrecursionlimit()
    if previous < _RECURSION:
        sys.setrecursionlimit(_RECURSION)
    try:
        return copy.deepcopy(world)
    finally:
        sys.setrecursionlimit(previous)
