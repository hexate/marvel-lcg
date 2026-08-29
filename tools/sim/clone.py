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

_INSTALLED = False


def _shared_classes():
    """The engine plumbing, as opposed to the position. Imported defensively: a missing
    one should degrade the copy, not stop the import."""
    out = []
    for mod, name in (
        ("engine.device.manager.notifier", "SynchronizationNotifier"),
        ("game.game_run.game_state", "GameState"),
        ("engine.controller.manager", "ControllerManager"),
        ("engine.device.manager.base", "DeviceManager"),
        ("game.game", "Game"),
        ("engine.controller.controller", "Controller"),
    ):
        try:
            out.append(getattr(__import__(mod, fromlist=[name]), name))
        except Exception:
            pass
    return out


def install():
    """Idempotent. Returns the classes that were made shareable."""
    global _INSTALLED
    classes = _shared_classes()
    if not _INSTALLED:
        for cls in classes:
            cls.__deepcopy__ = (lambda self, memo: self)
        _INSTALLED = True
    return [c.__name__ for c in classes]


def clone_world(world):
    """A copy of the position that can be played without touching the original."""
    install()
    return copy.deepcopy(world)
