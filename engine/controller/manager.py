from core import *
from engine.controller import *
from engine.log import Notify
from engine.job import JobManager
from game.scene.replay import *
from engine.device import *
from game.world import *
from game.scene import *
from game.game_run.game_state import GameState
from game import *
from engine.controller.module.replay import InputModule
from engine.controller.module.skip import SkipModule
from engine.controller.module.undo import UndoModule
from engine.console import Console

class ControllerManager:

    def __init__(self, game: 'Game', device_manager: 'DeviceManager') -> None:
        self.total_players = 0

        self.controllers: List['Controller'] = []

        self.skip       = SkipModule()
        self.undo       = UndoModule(self)
        self.replay     = InputModule(self)
        self.console    = Console(self)

        self.device_manager = device_manager
        self.game = game

        self.last_turn_start_step_id: int = 0

        # Make sure at least one controller is existed
        self.Setup(1, 0, None, None)

    def Setup(self, total_players: int, max_timeout: float, scene: 'Scene|None', state: 'GameState.StartState|None'):
        self.console.Clean()
        self.total_players = total_players

        self.device_manager.timer.UpdateMaxTimeout(max_timeout)

        from engine.controller import Controller
        for i in range(total_players):
            if len(self.controllers) <= i:
                self.controllers.append(Controller(i, self.device_manager, self))

        self.controllers = self.controllers[:total_players]

        self.replay.Clean()

        if scene:
            inputs = scene.inputs
        else:
            inputs = []
        self.replay.SetReplayInputs(inputs)
        # self.skip.Clean()

        if state:
            by_undo = state.is_undo
        else:
            by_undo = False

        self.undo.Clean(by_undo)
        self.last_turn_start_step_id = 0

        if scene and state:
            self.InitializeSkip(scene, state)

    # Setup is_skipping and skip_to
    def InitializeSkip(self, scene: 'Scene', state: 'GameState.StartState'):
        if scene.is_puzzle:
            self.skip.SetSkipTo(len(scene.inputs))
            self.skip.SetIsSkipping(True)
        elif state.is_in_testing:
            self.skip.SetSkipTo(len(scene.inputs))
            self.skip.SetIsSkipping(True)
        elif state.is_undo:
            if self.skip.skip_to > 0:
                self.skip.SetIsSkipping(True)
        elif state.is_new:
            self.skip.SetIsSkipping(False)
        elif state.is_load:
            if self.skip.skip_to < 0:
                self.skip.SetSkipTo(len(scene.inputs) + 1 + self.skip.skip_to)
            if self.skip.skip_to != 0:
                self.skip.SetIsSkipping(True)
        elif state.is_replay:
            self.skip.SetIsSkipping(False)
            self.replay.SetIsReplay(True)
        else:
            assert False

    ################################################################################
    #
    def OnNewGame(self):
        self.device_manager.OnNewGame()

    def OnGameOver(self):
        self.skip.SetIsSkipping(False)
        self.console.Clean()
        self.skip.Clean()

    def OnRestart(self):
        self.device_manager.OnRestart()

    def OnShutdown(self):
        for controller in self.controllers:
            controller.render.Shutdown()
        self.device_manager.OnShutdown()

    ################################################################################
    #
    def IsAnyDisplaying(self) -> bool:
        """False only when every output device says it is not showing the game.

        Defaults to True when there are no controllers yet, so setup renders as it always
        did rather than depending on when this is asked.
        """
        if not self.controllers:
            return True
        return any(controller.render.IsDisplaying() for controller in self.controllers)

    def WaitConnect(self):
        def process(controller: 'Controller'):
            controller.input.WaitConnect()
        jobs = JobManager.RunProcesses(process, self.controllers, name="WaitConnect")
        JobManager.WaitForAllJobsToComplete(*jobs)

    def WaitSync(self, wait: bool):
        if wait:
            def process(controller: 'Controller'):
                controller.render.WaitSync()
            jobs = JobManager.RunProcesses(process, self.controllers, name="WaitSync")
            # JobManager.WaitForAnyJobToComplete(*jobs)
            JobManager.WaitForAllJobsToComplete(*jobs)

        Notify.Clean()
        self.device_manager.AfterSync()

    ################################################################################
    #
    def OnBeginRound(self):
        if self.skip.skip_to_next == "Round":
            self.skip.Clean()

    def OnBeginPhase(self):
        if self.skip.skip_to_next == "Phase":
            self.skip.Clean()

    def OnBeginTurn(self):
        if self.skip.skip_to_next == "Turn":
            self.skip.Clean()

    ################################################################################
    #
    def OnPlayerTurnStart(self):
        self.last_turn_start_step_id = self.replay.current_step_id

