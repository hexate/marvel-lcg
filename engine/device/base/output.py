from typing import final
from engine.device import *
from engine.log import Log

class OutputDevice(Device):

    @final
    def WaitSync(self) -> None:
        game = self.controller.game
        if not game.state.is_running:
            Log.DebugSilent("SYNC", f"WaitSync skip (Game is not running)")
            return
        return self.manager.DoWaitSync(self.player_id, self.IsSyncReady)

    def IsSyncReady(self) -> bool:
        ...

    def Render(self) -> None:
        ...

    def IsDisplaying(self) -> bool:
        """Whether anything will look at what `Render` is given.

        True by default, because a device that does not answer is assumed to be showing
        the game to somebody. A headless device says False, and the world then skips
        building display descriptors it would only discard. That work is 86% of the cost
        of running a game, so this is the difference between a simulated game costing a
        second and costing a sixth of one.

        Deliberately separate from `skip`, which already has an early return in
        `WorldRender.PresentInternal` but also makes `Controller.ChoiceOne` overwrite the
        device's answer with the replay's fallthrough input. "Do not draw" and "do not
        take my input" were the same switch, so anything driving a game by its own input
        had to pay for rendering.
        """
        return True

