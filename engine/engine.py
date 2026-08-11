from core import *
from engine.device.manager import DeviceManager

from game import *
from game.statistics.game_statistics import GameStatistics
from build import Build
from engine.log import Log
from engine.lib import TransText, ImageCreator, Ver
from engine.user.user_info import UserInfo
from engine.task import TaskManager
from engine.job import JobManager
from engine.device.manager.base import DeviceManager
from engine.lib.check_new_version import CheckForNewVersion
from engine.config import ConfigVariables

CATEGORY_NAME = "ENGINE"

CHECK_FOR_NEW_VERSION_ON_STARTUP    = ConfigVariables.Bool('check_for_new_version_on_startup', False)
PRINT_MY_USER_FINGERPRINT           = ConfigVariables.Bool('print_my_user_fingerprint', False)

DEVICE              = ConfigVariables.Str('device', "web")

PROFILE_FOLDER      = ConfigVariables.Folder('profile_folder')
TEST_ALL            = ConfigVariables.Bool('test_all', False)
EDITOR              = ConfigVariables.Bool('editor', True)

ConfigVariables.SetGroupArgs('test', "-device -no_editor -no_statistics -test_result_file test_results.txt -hidden_log_categories CONTROLLER WEB VERSION STATISTICS")

class Engine:

    device_manager: 'DeviceManager'

    game: 'Game'
    statistics: 'GameStatistics'

    has_crashed = False
    in_unit_test = False

    @staticmethod
    def CheckAssertionsEnabled(assertions_enabled: bool = __debug__) -> None:
        """Refuse to run with assertions stripped.

        Around 619 `assert` statements across core/, engine/, game/ and cards/ carry the game
        rules, not merely internal invariants: legal targets, timing windows, resource costs.
        `python -O` deletes all of them, and the result is not a game that crashes but a game that
        walks past illegal plays without noticing. Refusing to start is the honest response.

        The parameter exists so this is testable; nothing should pass it in production.
        """
        if assertions_enabled:
            return
        raise RuntimeError(
            "Started with assertions disabled (python -O). The rules of the game are enforced by "
            "assert statements, and -O removes every one of them, so this build would allow "
            "illegal plays instead of stopping on them. Run without -O."
        )

    @staticmethod
    def Initialize() -> bool:
        Engine.CheckAssertionsEnabled()
        Ver.Initialize()
        game_name = f'Marvel LCG {Ver.ui_version_str}'
        System.SetTitle(game_name)

        # ConfigVariables.Test()

        def initialize() -> bool:
            Log.Info(CATEGORY_NAME, game_name)

            ConfigVariables.Initialize()

            JobManager.Initialize()
            TaskManager.Initialize()

            if CHECK_FOR_NEW_VERSION_ON_STARTUP.value:
                async def check_new_version() -> None:
                    CheckForNewVersion.Check()

                job = JobManager.AddJob(check_new_version, name="Check Version")

                if CHECK_FOR_NEW_VERSION_ON_STARTUP.is_from_command_line:
                    JobManager.WaitForAllJobsToComplete(job)
                    return False

            UserInfo.Initialize()
            if PRINT_MY_USER_FINGERPRINT.value:
                Log.Info(CATEGORY_NAME, f"{UserInfo.fingerprint=}")
                if PRINT_MY_USER_FINGERPRINT.is_from_command_line:
                    return False

            TransText.Initialize()
            ImageCreator.Initialize()

            from cards.database import CardsDB
            CardsDB.Initialize()

            if Build.release:
                EDITOR.value = False

            if EDITOR.value:
                from editor.editor import Editor
                Editor.Initialize()

            # for x in range(50020, 50033):
            #     y = CardsDB.papers[str(x)]
            #     text = y.text
            #     text = text.replace("\r", "")
            #     text = text.replace("\n", "\\n")
            #     text = text.replace('"', '\\"')
            #     print(f'"{x}": "{text}",')

            Engine.statistics = GameStatistics()
            Engine.statistics.Load()

            device = DeviceManager
            if DEVICE.value == "web":
                from engine.device.manager.web.manager import WebDeviceManager
                device = WebDeviceManager
            else:
                from engine.device.manager.key.manager import KeyDeviceManager
                device = KeyDeviceManager

            Engine.device_manager = device()
            Engine.game = Game(Engine.statistics, Engine.device_manager)
            return True

        if Build.release:
            try:
                return initialize()
            except Exception as exc:
                Log.OnCrash(CATEGORY_NAME, exc, "", None)
                return False
        else:
            return initialize()

    @staticmethod
    def EngineRun() -> None:
        if Build.release:
            try:
                Engine.game.GameRun()
            except Exception as exc:
                Log.OnCrash(CATEGORY_NAME, exc, "", None)
                Log.SaveCrashLog()
        else:
            if TEST_ALL.value:
                from unit_test.entry import TestEntry
                from unit_test.runner import TestRunner
                TestRunner.Execute(TestEntry.Test, True)
                return
            elif PROFILE_FOLDER.is_initialized and PROFILE_FOLDER.value:
                from unit_test.entry import TestEntry
                from unit_test.runner import TestRunner
                TestRunner.Execute(TestEntry.Test, PROFILE_FOLDER.value, True)
                return

            if EDITOR.value:
                from editor.editor import Editor
                Editor.EditorRun()
            Engine.game.GameRun()

    @staticmethod
    def Shutdown():
        Log.Print("\n--- Engine Shutdown ---")
        Engine.game.Shutdown()

        if EDITOR.value:
            from editor.editor import Editor
            Editor.Shutdown()

        JobManager.Shutdown()
        TaskManager.Shutdown()

        # System.Pause()
        return

    ################################################################################
    #
    @staticmethod
    def SaveCrash():
        if not Engine.has_crashed:
            # Engine.game is not assigned until the end of Initialize, so a failure before that
            # point reaches here with nothing to save. Touching it raised AttributeError, which
            # then replaced the real exception as the error the user saw.
            if getattr(Engine, 'game', None) != None:
                Engine.game.session.SaveScene(f'./crash.json', delete_old=False)
            else:
                Log.Warn(CATEGORY_NAME, "Crashed before the game existed, no scene to save")
            Engine.has_crashed = True
        if Engine.in_unit_test:
            exit(-1)

import builtins
setattr(builtins, "DebugBreak", lambda: Debug.DebugBreak(True))
# You can call `DebugBreak()` any where without import

