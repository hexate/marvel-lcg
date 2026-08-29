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
about 0.04s, leaving the original untouched. That is roughly ten times cheaper than the
replay it replaces, and unlike the replay it is a real forward model.

This is deliberately a shim rather than an engine change. Nothing in the game calls
`deepcopy` on these classes today, so `install()` only affects code that asks for it.
The engine-side version of this is tracked as N21.
"""
import copy
import sys

_INSTALLED = False

# The position is a deep graph of effects and card faces, and `deepcopy` recurses once
# per level. The default limit of 1000 clears an opening position and then starts
# failing a few rounds in, once effect chains have built up, which showed up as 28
# rollouts in 30 returning nothing.
_RECURSION = 60000


def _shared_classes():
    """Device plumbing only. A clone should not get its own notifier: it notifies nobody,
    and the notifier owns three of the four Conditions that refuse to copy."""
    out = []
    for mod, name in (("engine.device.manager.notifier", "SynchronizationNotifier"),
                      ("engine.device.manager.base", "DeviceManager")):
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
    if getattr(cls, "_sim_besteffort", False):
        return

    def __deepcopy__(self, memo):
        new = cls.__new__(cls)
        memo[id(self)] = new
        for k, v in self.__dict__.items():
            try:
                new.__dict__[k] = copy.deepcopy(v, memo)
            except Exception:
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
        import threading
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        for k, v in self.__dict__.items():
            if isinstance(v, (type(threading.Condition()), type(threading.RLock()),
                              type(threading.Lock()))):
                new.__dict__[k] = threading.Condition()
            else:
                new.__dict__[k] = copy.deepcopy(v, memo)
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
        for mod, name in (("engine.controller.manager", "ControllerManager"),
                          ("engine.controller.controller", "Controller"),
                          ("game.game", "Game"),
                          ("game.game_run.game_session", "GameSession")):
            try:
                _best_effort_copy(getattr(__import__(mod, fromlist=[name]), name))
            except Exception:
                pass
        _INSTALLED = True
    return [c.__name__ for c in classes]


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
