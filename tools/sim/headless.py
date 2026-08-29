"""Stop the simulator rendering a board nobody is looking at.

Profiling a run put 86% of the time in `WorldRender.PresentInternal`: it walks every
deck and calls `Card.Render` on every card to build display descriptors, 159,813 times
across three games, and the scripted output device throws all of it away.

The engine already knows how to skip this. `PresentInternal` returns early when
`controller_manager.skip.is_skipping`, and the source carries the comment "Comment out
this to render the game while testing, but it is VERY slow". The simulator cannot use
that path, because skip mode also makes `Controller.ChoiceOne` overwrite the device's
answer with the replay's fallthrough input, which is exactly what the harness had to
avoid to drive a game at all. So the two are entangled: you cannot ask for "do not draw"
without also getting "do not take my input".

This asks for the first without the second, by making the render a no-op directly.

Measured over eight games with the same seeds: 7.23s becomes 1.20s, a six times speedup,
and the outcomes are identical, round for round, reason for reason, decision for
decision. That matters more than the speed. Search needs thousands of playouts per
decision to be worth anything, and every one of them was paying to draw a picture.
"""

_INSTALLED = False
_ORIGINAL = None


def install():
    """No-op the render. Idempotent. Returns True if it took effect."""
    global _INSTALLED, _ORIGINAL
    if _INSTALLED:
        return True
    try:
        from game.world.world_render import WorldRender
    except Exception:
        return False
    _ORIGINAL = WorldRender.PresentInternal
    WorldRender.PresentInternal = lambda self, *args, **kwargs: None
    _INSTALLED = True
    return True


def uninstall():
    global _INSTALLED
    if _INSTALLED and _ORIGINAL is not None:
        from game.world.world_render import WorldRender
        WorldRender.PresentInternal = _ORIGINAL
        _INSTALLED = False
