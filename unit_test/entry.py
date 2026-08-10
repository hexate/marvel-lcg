from core import *
from engine import Engine
from engine.log import Log
from engine.profile import Profile
from engine.file import FileManager
from build import Build
from game.test.test_run import TestRun
from game.test import Test

class TestEntry:

    @staticmethod
    def GetFolderTestCase(folder: str) -> List[str]:
        all_cases: List[str] = FileManager.ListFiles(folder)
        all_cases = [case for case in all_cases if case.endswith(".json")]
        return all_cases

    @staticmethod
    def Test(folder: str|None, do_profile: bool=False):
        # Log.Print(f"{folder=} {do_profile=}")

        if folder == None:
            all_cases = Test.GetTestCases(None)
        else:
            all_cases = TestEntry.GetFolderTestCase(folder)

        # Without this the run finishes "--- Test End --- (0/0)" and then dies on `assert world`
        # forty lines later, because no case ever built one. That reads as an engine fault rather
        # than an empty folder, and it is the first thing a new contributor hits: the replays are
        # player data, so they are not in the repository and nothing says so.
        assert all_cases, (
            f"No replay files found in {folder if folder else 'the configured test folders'}. "
            f"The test corpus is recorded games, which are not shipped with the source, so this "
            f"folder is empty on a fresh clone. Play a game and it saves to ./replays/, then copy "
            f"one in. A scene only works here if the game asks nothing more after its last "
            f"recorded input, so record until the game ends rather than saving mid-turn."
        )

        Test.is_in_test = True # We do need this

        if do_profile:
            assert Build.release == False

        game = Engine.game

        if do_profile:
            Profile.Run(
                TestRun.Run,
                game, all_cases,
                profile_name="Test", profile_category="Test")
            profiler = Profile.Get("Test", category="Test")
            Log.Print(profiler.Print())
        else:
            TestRun.Run(game, all_cases)

        TestRun.RunEnd(game, True, True)

        Log.Print(Tracker.PrintStats())
        world = game.world
        assert world
        Log.Print(f"{len(world.object_manager.card_dict)=}")
        Log.Print(f"{len(world.object_manager.effect_dict)=}")

