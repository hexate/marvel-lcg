"""Replay-independent test harness (tracker item I2).

The engine's only non-human input source is the replay log, which is why recorded games are
currently the only way to test. This module supplies the missing primitive: an `InputDevice`
that answers decisions from a policy instead of from `input()` or a replay file.

With that in place a test can build a `World` from a scenario + hero name, drive it with the
debug DSL in `game/world/cheat/cheat_cmd_helper.py` (`Gain`, `Play`, `Damage`, `CanTarget`, …),
and assert on state — with no fixture on disk and no dependence on replay determinism.

Usage:

    from unit_test.harness import GameFixture

    with GameFixture("rhino", ["spider_man"], seed=42) as fx:
        fx.cheat("Gain('Enhanced Reflexes')")
        assert fx.player(0).hand_cards.GetSize() == 1
"""
import json
from typing import Any, Callable, Dict, List, Optional, Sequence

from core import *
from engine.device.base.input import InputDevice
from engine.device.base.output import OutputDevice
from engine.device.manager.base import AskOptionPayload, DeviceManager

CATEGORY_NAME = "HARNESS"

# A policy receives the payload and the decoded option list, and returns the input JSON string.
Policy = Callable[[AskOptionPayload, List[Dict[str, Any]]], str]


def _command(effect_id: Any = "0", targets: Sequence[Any] = (), resources: Sequence[Any] = ()) -> str:
    """Build the JSON the controller parses as a `CommandDescriptor`."""
    return json.dumps({
        "id": str(effect_id),
        "targets": [str(t) for t in targets],
        "resources": [str(r) for r in resources],
    })


def decline_or_first(payload: AskOptionPayload, options: List[Dict[str, Any]]) -> str:
    """Default policy: decline whenever declining is legal, otherwise take the first option.

    Declining is how a human clicks "no thanks" past optional responses, so this walks a game
    to its next forced decision without making arbitrary strategic choices.
    """
    if payload.show_cancel or not options:
        return _command("0")

    option = options[0]
    target_range = option.get("target_num_range") or [0, 0]
    need = target_range[0] if target_range else 0

    # `id == 0` means "decline". `Controller.ChoiceOne` accepts it even for a forced prompt as
    # long as there is a single option needing no targets (engine/controller/controller.py:271).
    # The mulligan is exactly that shape — "you MAY discard any number" — and answering it with
    # the effect id plus an empty target list is not accepted, so the prompt repeats forever.
    if need == 0:
        return _command("0")

    legal = option.get("all_legal_targets") or []
    return _command(option.get("id", "0"), legal[:need])


class ScriptedInput(InputDevice):
    """Answers prompts from `manager.policy` instead of blocking on stdin."""

    @override
    def IsInputReady(self) -> bool:
        payload = self.manager.ask_options[self.player_id]
        options: List[Dict[str, Any]] = []
        if payload.options_json:
            try:
                decoded = json.loads(payload.options_json)
                if isinstance(decoded, list):
                    options = decoded
            except json.JSONDecodeError:
                options = []

        manager: Any = self.manager
        manager.prompt_log.append((self.player_id, payload.event_name, payload.prompt_text, len(options)))
        answer = manager.policy(payload, options)

        # Must go through `WhenInput`, not `payload.input_json = …`.
        #
        # `DoGetInput` appends the player to `manager.asking_players` before waiting, and on wake
        # returns **None** if the player is still in that list (engine/device/manager/base.py:113).
        # `Controller.ChoiceOne` maps a None input to `return None, True` — the "cheat" flag — and
        # `PlayerAction.ChooseEffects` loops forever on `cheat` (player_action.py:178).
        # `WhenInput` is what the web client calls: it removes the player from `asking_players`,
        # stores the answer, and notifies.
        #
        # `KeyInput` (engine/device/keyboard/key_input.py:9) sets `input_json` directly and so hits
        # exactly this bug — a second, independent reason the keyboard device cannot drive a game.
        manager.WhenInput(answer, self.player_id)
        return True

    @override
    def IsConnect(self) -> bool:
        return True


class ScriptedOutput(OutputDevice):
    """Headless output that always reports itself synchronised.

    `ConsoleDevice` does not implement `IsSyncReady`, so it inherits the abstract stub in
    `engine/device/base/output.py:17`, which returns `None`. `DoWaitSync` waits on that with
    `timeout=None`, so the first `Present()` in a live game deadlocks: the main thread blocks in
    `JobManager.WaitForAllJobsToComplete` while the render job blocks in `DoWaitSync`.

    Only the web device implements the handshake (`engine/device/web/web_device.py:36`), which is
    why the console/keyboard device works in the replay harness — there `game.state.is_running`
    is False and `WaitSync` early-returns — but cannot drive a real game.
    """

    @override
    def Render(self) -> None:
        pass

    @override
    def IsSyncReady(self) -> bool:
        return True

    @override
    def IsDisplaying(self) -> bool:
        """Nothing is watching, so the world need not build descriptors for it."""
        return False


class ScriptedDeviceManager(DeviceManager):
    """DeviceManager whose input comes from a policy and whose output is headless."""

    policy: Policy = staticmethod(decline_or_first)

    def __init__(self) -> None:
        super().__init__()
        self.prompt_log: List[tuple] = []

    @override
    def CreateDevices(self, controller: 'Controller') -> Any:
        return ScriptedOutput(controller, self), ScriptedInput(controller, self)


_engine_ready = False


def EnsureEngine() -> None:
    """Boot the engine once per process with a scripted device manager.

    `Engine.Initialize` hard-codes the device to `web` or `key` (`engine/engine.py:96-103`), so
    the manager is swapped afterwards. Upstreaming this would be cleaner as a third branch there.
    """
    global _engine_ready
    if _engine_ready:
        return

    import sys
    from build import Build

    Build.release = True
    if '-config_files' not in sys.argv:
        sys.argv += ['-config_files', 'launch.json']
    if '-test' not in sys.argv:
        sys.argv += ['-test']

    from engine import Engine
    from game.game import Game

    assert Engine.Initialize(), "Engine.Initialize() failed"

    Engine.device_manager = ScriptedDeviceManager()
    Engine.game = Game(Engine.statistics, Engine.device_manager)
    Engine.in_unit_test = True
    _engine_ready = True


class GameFixture:
    """Builds a live `World` from a scenario + hero names, with no replay file involved."""

    def __init__(self, scenario: str, heroes: Sequence[str], *, seed: int = 42,
                 policy: Optional[Policy] = None) -> None:
        self.scenario_name = scenario
        self.hero_names = list(heroes)
        self.seed = seed
        self.policy = policy or decline_or_first
        self.game: Any = None
        self.scene: Any = None

    # ------------------------------------------------------------------ setup
    def __enter__(self) -> 'GameFixture':
        self.Start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.Stop()

    def Start(self) -> 'GameFixture':
        from engine import Engine
        from game.scene import SceneLoader
        from game.test import Test

        EnsureEngine()
        ScriptedDeviceManager.policy = staticmethod(self.policy)  # type: ignore[assignment]

        Engine.in_unit_test = True

        # Start state MUST be 'New', not 'InTesting'.
        #
        # `ControllerManager.InitializeSkip` turns skip mode ON for 'InTesting'
        # (engine/controller/manager.py:74-77). With skip on, `Controller.ChoiceOne`
        # overwrites the device's answer with `convert_fallthrough_input`
        # (engine/controller/controller.py:158-159), which is "{}" when there are no replay
        # inputs — so every scripted answer is discarded and the same prompt repeats forever.
        # 'New' takes the `state.is_new` branch and leaves skipping off.
        Test.is_in_test = False
        self.scene = SceneLoader.NewScene(self.scenario_name, None, self.hero_names, self.seed)
        self.game = Engine.game
        self.game.session.SetScene(self.scene, 'New')
        self.game.GameSetup()
        return self

    def Stop(self) -> None:
        world = self.world
        if world and not world.is_game_over:
            world.game_over.SetExit()

    # ------------------------------------------------------------------ access
    @property
    def world(self) -> Any:
        return self.game.world if self.game else None

    def player(self, index: int = 0) -> Any:
        return self.world.const_players[index]

    def villain(self, index: int = 0) -> Any:
        return self.world.scenario.area_villain.Get()[index]

    def main_scheme(self, index: int = 0) -> Any:
        return self.world.area_schemes_main.Get()[index]

    # ------------------------------------------------------------------ drive
    def cheat(self, *commands: str, player_id: int = 0) -> None:
        """Run debug-DSL commands against the live world.

        The DSL lives in `game/world/cheat/cheat_cmd_helper.py` — `Gain`, `Play`, `Damage`,
        `Threat`, `Reveal`, `CanTarget`, `CannotTarget`, and ~35 others.
        """
        from game.world.cheat.cheat_cmd_helper import RunCheat
        RunCheat(self.world, list(commands), player_id)
