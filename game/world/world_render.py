from core import *
from core import *
from game.card.face import *
from game.card import *
from engine.lib import TransText
from engine.log import Log
from engine.profile import Profile
from game.world import *
from build import Build
from game.render.descriptor.world import WorldDescriptor
from game.render.to_descriptor import ToDescriptor
from engine.config import ConfigVariables

RENDER_ON_UNDO = ConfigVariables.Str('render_on_undo', "round")

CATEGORY_NAME = "RENDER"

class WorldRender:
    def __init__(self, world: 'World') -> None:
        self.world = world
        self.last_active_card_ids: List[int] = []
        self.prompt: str = ""
        self.last_prompt: str = ""
        self.last_render_id: int = 0

        self.debug_message: str = ""
        self.descriptor = WorldDescriptor()
        self.last_round_id: int = 0

    def PresentForceNoWait(self, is_update: bool=True) -> None:
        skip = self.world.controller_manager.skip.is_skipping
        assert skip == False # Call `controller_manager.skip.SetSkipTo(None)` first
        return self.PresentInternal(None, is_update=True, skip=False, wait=False)

    def Present(self, origin_info: TransText, sound_name: str, event_name: str, *faces: 'CardFace', code_info: str) -> None:
        skip = self.world.controller_manager.skip.is_skipping
        return self.PresentInternal(origin_info, sound_name, event_name, *faces, is_update=True, skip=skip, code_info=code_info)

    def ErrorOccurred(self, origin_info: str) -> None:
        from engine import Engine
        game = Engine.game
        if game.state.is_running and self.world:
            return self.PresentInternal("Error occurred:\n" + origin_info, "", "", is_update=True, skip=False, log_game_info=False)

    def PresentInternal(self, origin_info: TransText|str|None, sound_name: str='', event_name: str='',
                        *faces: 'CardFace',
                        code_info: str="",
                        is_update: bool=True,
                        skip: bool=False,
                        wait: bool=True,
                        log_game_info: bool=True) -> None:
        if is_update:
            self.last_render_id += 1
            self.last_active_card_ids = [x.card.object_id for x in faces]

        Log.DebugSilent("SYNC", f"-------- {self.last_render_id} ---------")

        # Comment out this to render the game while testing, but it is VERY slow
        if skip:
            from game.test import Test
            if Test.IsInTesting():
                return

            if RENDER_ON_UNDO.value == "round":
                if self.world.round_id == self.last_round_id:
                    return
            else:
                # undo_ui = int(UNDO_UI.value)
                # if undo_ui > 0 and \
                #     self.last_render_id % undo_ui != undo_ui - 1:
                #     return
                Log.DebugSilent("SYNC", f"Render world skip")
                return

        self.last_round_id = self.world.round_id

        Log.DebugSilent("SYNC", f"Render world start")

        if origin_info:

            if isinstance(origin_info, str):
                text_symbol = origin_info
                self.prompt = text_symbol
            else:
                text_symbol = origin_info.text_symbol
                self.prompt = origin_info.text_no_symbol

            if text_symbol and log_game_info and not skip:
                Log.PrintGameInfo(f"{text_symbol}", sound_name=sound_name, render_id=self.last_render_id, code_info=code_info)

            self.last_prompt = self.prompt
        else:
            self.prompt = ""

        # Everything above is bookkeeping the rest of the engine reads: the render id, the
        # prompt, and the game log line. Everything below draws. With no display attached
        # the drawing is discarded, and it is the bulk of the cost of running a game.
        if not self.world.controller_manager.IsAnyDisplaying():
            Log.DebugSilent("SYNC", "Render world skip (nothing is displaying)")
            return

        world = self.world
        self.descriptor = ToDescriptor.World(world, event_name, sound_name)

        from engine import Engine
        game = Engine.game

        if not Build.release:
            self.debug_message = f"""<div id='debug-render'>Render: {self.last_render_id}, Step: {game.controller_manager.replay.current_step_id}</div>
<div id='debug-effect'>{world.event_manager.debug_log_both.GetLog()}</div>
<div id='debug-effect'>{world.event_manager.debug_log_only_local.GetLog()}</div>
<div id='debug-effect'>{world.event_manager.debug_log_only_global.GetLog()}</div>
<div id='debug-effect'>{world.event_manager.debug_log.GetLog()}</div>
<div id='profile'>{Profile.GetDebugMessage()}</div>
"""
# <div id='debug-effect-paying'>Paying effects: {len(ObjectManager.paying_effect_dict)}</div>

        for player in world.const_seat_order_players:
            player.GetController().Render()

        # start_time = Time.GetTime()
        if not skip:
            Log.DebugSilent("SYNC", f"Render start")
            game.controller_manager.WaitSync(wait)

        # elapsed_time = Time.GetTime() - start_time
        # Log.DebugSilent(CATEGORY_NAME, f"Render time: {elapsed_time:.3}")
        Log.DebugSilent("SYNC", f"Render end")

    def CalculateCRC(self) -> List[str]:
        world = self.world
        infosets: List[Dict[int, int]] = [{}, {}, {}]
        for id in world.object_manager.card_dict:
            if id != 0:
                card = world.object_manager.card_dict[id]
                info = card.GetCRC(recalculate=True)
                if info != -1:
                    infosets[0] |= {id: info}
        return [str(x).replace(' ', '') for x in infosets]

