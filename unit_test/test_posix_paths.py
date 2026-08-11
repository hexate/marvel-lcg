"""Three places that assume Windows path separators (tracker items A2, A3, A5).

Each one is a string comparison against a hardcoded backslash, so on macOS and Linux the comparison
simply never matches and the code silently takes the wrong branch. Nothing errors, which is why
they survived: the coverage report is empty rather than wrong, and the safety break does not fire
rather than firing late.

`game/` cannot be imported on its own because of a circular import, so `import engine` comes first.
"""
import os
import unittest

import engine  # noqa: F401  must precede any game import
from core.utility.func import ROOT_DIR
from engine.file import FileManager
from engine.profile.coverage import Coverage


def _fake_card_function(relative_path: str):
    """A stand-in for a card script function, with a real path under the repo root.

    `GetFuncLines` reads `__code__.co_filename` and makes it relative to ROOT_DIR, so the path has
    to actually sit under the root for the result to look like a card script.
    """
    class _Code:
        co_filename = os.path.join(ROOT_DIR, *relative_path.split("/"))
        co_firstlineno = 12

    class _Function:
        __code__ = _Code()

    return _Function()


class TestCoverageKeys(unittest.TestCase):
    """A2: `GetKeyName` matched `cards\\pack\\`, so no card counted on a POSIX machine."""

    def test_a_card_script_produces_a_coverage_key(self):
        key = Coverage.GetKeyName(_fake_card_function("cards/pack/core/spider_man.py"))

        self.assertTrue(key, "a card script produced no coverage key, so coverage counts nothing")
        self.assertIn("spider_man.py", key)

    def test_a_non_card_file_still_produces_no_key(self):
        """The filter has to keep filtering. Engine code is not card-script coverage."""
        self.assertEqual(Coverage.GetKeyName(_fake_card_function("engine/lib/random.py")), "")


class TestFormatPath(unittest.TestCase):
    """A5: `normalized_path[1]` assumed at least two characters, for a Windows drive letter."""

    def test_a_one_character_path_does_not_raise(self):
        self.assertEqual(FileManager.FormatPath("a"), "./a")

    def test_the_root_path_does_not_raise(self):
        self.assertEqual(FileManager.FormatPath("/"), "/")

    def test_an_absolute_path_is_left_alone(self):
        """Found by the test above returning './/'.

        The drive-letter check was standing in for "already rooted", so on POSIX an absolute path
        came back as "./Users/...", which points somewhere else entirely.
        """
        self.assertEqual(FileManager.FormatPath("/Users/someone/replays/x.json"),
                         "/Users/someone/replays/x.json")

    def test_a_windows_path_is_left_alone(self):
        self.assertEqual(FileManager.FormatPath("C:/games/x.json"), "C:/games/x.json")

    def test_ordinary_paths_are_unchanged(self):
        self.assertEqual(FileManager.FormatPath("./replays/x.json"), "./replays/x.json")
        self.assertEqual(FileManager.FormatPath("replays/x.json"), "./replays/x.json")


class TestUntrustedScenePath(unittest.TestCase):
    """A3: the downloaded-save break tested for `crashs\\dl`, which never appears on POSIX.

    It guards the `exec` of debug commands carried inside a scene, so failing to match means the
    break in front of that exec silently does not happen.
    """

    def test_a_downloaded_scene_is_recognised_on_posix(self):
        from game.world.cheat.cheat_cmd_helper import IsUntrustedScenePath

        self.assertTrue(IsUntrustedScenePath("./crashs/dl/some_crash.json"))

    def test_a_downloaded_scene_is_recognised_on_windows(self):
        from game.world.cheat.cheat_cmd_helper import IsUntrustedScenePath

        self.assertTrue(IsUntrustedScenePath(".\\crashs\\dl\\some_crash.json"))

    def test_an_ordinary_scene_is_not_flagged(self):
        from game.world.cheat.cheat_cmd_helper import IsUntrustedScenePath

        self.assertFalse(IsUntrustedScenePath("./replays/min_test/game.json"))
        self.assertFalse(IsUntrustedScenePath(""))


if __name__ == "__main__":
    unittest.main()
