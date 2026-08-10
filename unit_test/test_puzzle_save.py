"""Saving a puzzle must not damage the live replay log.

Scene.UpdateInputs assigns the replay's history list by reference, and PrepareSave then strips
step, event and crc off each entry when the scene is a puzzle. Those are the same objects the
running game is still appending to.

OperationDescriptor is a dataclass with plain defaults, so the class still carries them. The first
strip removes the instance attribute and the class default silently takes over, and a second strip
raises because there is no instance attribute left.

Scene.Save returns early for puzzles, but GameSession.DumpSave calls PrepareSave directly and
bypasses that guard.
"""
import unittest

import engine  # noqa: F401  must precede any game import
from game.scene import Scene
from game.scene.replay.operation import OperationDescriptor


class _Replay:
    def __init__(self, inputs):
        self.history_inputs = inputs


class _ControllerManager:
    def __init__(self, inputs):
        self.replay = _Replay(inputs)


class _Game:
    def __init__(self, inputs):
        self.controller_manager = _ControllerManager(inputs)


def _puzzle_scene(inputs):
    from engine.user.user_info import UserInfo
    UserInfo.Initialize()
    scene = Scene()
    scene.SetMetadataBool("is_puzzle", True)
    return scene, _Game(inputs)


class TestPuzzleSave(unittest.TestCase):

    def test_live_replay_log_is_not_stripped(self):
        live = [OperationDescriptor(step=7, event="ev", crc="abc")]
        scene, game = _puzzle_scene(live)

        scene.PrepareSave(game, playtime=None)

        self.assertEqual(live[0].step, 7, "the running game's input log lost its step")
        self.assertEqual(live[0].event, "ev")
        self.assertEqual(live[0].crc, "abc")

    def test_saving_a_puzzle_twice_does_not_raise(self):
        live = [OperationDescriptor(step=7, event="ev", crc="abc")]
        scene, game = _puzzle_scene(live)

        scene.PrepareSave(game, playtime=None)
        scene.PrepareSave(game, playtime=None)  # must not raise

    def test_the_saved_copy_is_still_stripped(self):
        """The size saving the strip exists for has to survive the fix."""
        live = [OperationDescriptor(step=7, event="ev", crc="abc")]
        scene, game = _puzzle_scene(live)

        scene.PrepareSave(game, playtime=None)

        saved = scene.inputs[0]
        self.assertNotIn("step", saved.__dict__)
        self.assertNotIn("event", saved.__dict__)
        self.assertNotIn("crc", saved.__dict__)

    def test_a_normal_scene_keeps_everything(self):
        live = [OperationDescriptor(step=7, event="ev", crc="abc")]
        from engine.user.user_info import UserInfo
        UserInfo.Initialize()
        scene = Scene()
        game = _Game(live)

        scene.PrepareSave(game, playtime=None)

        self.assertEqual(scene.inputs[0].step, 7)


if __name__ == "__main__":
    unittest.main()
