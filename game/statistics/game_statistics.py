from typing import Final
from core import *
from game.card.face.card_face import CardFace
from game.player import *
from game.statistics.statistics import Statistics
from game.statistics.statistics import GAME_OVER_OUTCOME
from engine.lib import Json, Ver
from engine.log import Log, Notify
from engine.file import FileManager
from engine.config import ConfigVariables

CATEGORY_NAME = "STATISTICS"

GAME_STATISTICS_FILE    = ConfigVariables.File('game_statistics_file', "statistics.json")
STATISTICS              = ConfigVariables.Bool('statistics', True)

class GameStatistics:
    DATA_INFO: Final = "<card_id>: [<resolve>, <play>, <reveal>, <defeated>]"

    def __init__(self) -> None:
        self.content: Statistics
        self.content_copy: Statistics
        self.file_path: str
        self.completion_rate: float
        self.pause_internal: bool|Literal["WhenSkipping"] = False
        self.file_broken: bool = False
        if not STATISTICS.value:
            self.pause_internal = True
            def DoNothing(*args: Any, **kwargs: Any) -> None:
                pass
            def ReturnFalse(*args: Any, **kwargs: Any) -> bool:
                return False
            self.Copy = DoNothing
            self.Reset = DoNothing
            self.Save = DoNothing
            self.Load = DoNothing
            self.IsNew = ReturnFalse
            self.SetPause = DoNothing
            self.IsPause = ReturnFalse
            self.CanRegisterAbility = ReturnFalse
            self.content = Statistics()
            self.completion_rate = 0

    def Copy(self):
        import copy
        self.content_copy = copy.deepcopy(self.content)

    def Reset(self):
        import copy
        self.content = copy.deepcopy(self.content_copy)
        Log.Debug(CATEGORY_NAME, "GameStatistics reset")

    def Save(self):
        if self.pause_internal == True:
            return
        if self.file_path and not self.file_broken:
            self.Copy()
            Json.Save(self.content, self.file_path, ignore_check_sum=False)
            Log.Info(CATEGORY_NAME, f"Saved: {self.file_path}")

    def Load(self):
        self.file_path = GAME_STATISTICS_FILE.value
        need_created = True

        if FileManager.Exists(self.file_path):
            try:
                statistics = Json.LoadAs(self.file_path, Statistics, check_sum="Restrict")
                crc = statistics.UpdateVersion()
                # For old version 0.5.7.139
                def check_version(crc: str):
                    def crc_random(total_sum: int) -> str:
                        import hashlib
                        if total_sum == 0:
                            return ""

                        def custom_random(seed: int, a: int, b: int) -> int:
                            return a + seed % (b - a + 1)

                        total_sum = custom_random(total_sum, 0, 2**32)
                        # Hash the sum
                        hash_object = hashlib.sha256(str(total_sum).encode())
                        return hash_object.hexdigest()

                    def get_hash_v155(content: Statistics) -> str:
                        flat_list = [item for sublist in content.data.values() for item in sublist]

                        # Calculate the sum of the flattened list
                        total_sum = 0
                        total_sum += sum(flat_list)
                        total_sum += sum(getattr(content, f.name) for f in fields(Statistics) if f.type == int)

                        return crc_random(total_sum)

                    def get_hash_v139(content: Statistics, hack: bool=False) -> str:
                        flat_list = [item for sublist in content.data.values() for item in sublist]
                        keys_list = [item for sublist in content.data.keys() for item in sublist]

                        # Calculate the sum of the flattened list
                        total_sum = 0
                        total_sum += sum(flat_list)
                        total_sum += sum(int(key) for key in keys_list if key.isdigit())
                        total_sum += sum(getattr(content, f.name) for f in fields(Statistics) if f.type == int)

                        return crc_random(total_sum)

                    assert crc == get_hash_v155(statistics) or crc == get_hash_v139(statistics)

                if not Ver(statistics.version).IsChecksum() and crc:
                    check_version(crc)

                self.content = statistics
                need_created = False
                Log.Info(CATEGORY_NAME, f"{self.file_path} loaded")
            except:
                self.file_broken = True
                Log.Assert(CATEGORY_NAME, f"{self.file_path} file is broken. You can still play the game, but statistics will not be recorded. Alternatively, you can delete {self.file_path} to generate a new statistics file.")

        if need_created:
            if not self.file_broken:
                Log.Info(CATEGORY_NAME, f"{self.file_path} created")
            self.content = Statistics()
            self.content.UpdateVersion()
        self.Copy()

        from cards.database import CardsDB
        self.completion_rate = len(self.content.data) / len(CardsDB.papers)

    ################################################################################
    #
    def RecordAchievement(self, player: 'Player', name: Literal[
            'achievement_first_blood',
            'achievement_double_kill',
            'achievement_triple_kill',
            'achievement_ultra_kill',
            'achievement_rampage',
        ]):
        if self.IsPause():
            return

        setattr(self.content, name, getattr(self.content, name) + 1)
        text = f"Achievement: {name.lstrip('achievement_').upper()}"
        Notify.Statistics(text)

    def RecordValue(self, name: Literal[
        "operation",
        "total_damage_taken",
        "total_damage_dealt",
        "total_threats_removed",
        "total_damage_healed",
        "total_cards_drawn",
        "generate_resources_r",
        "generate_resources_b",
        "generate_resources_y",
        "generate_resources_g",
        'play_aspect_aggression',
        'play_aspect_justice',
        'play_aspect_leadership',
        'play_aspect_protection',
        'play_aspect_pool',
        'play_basic_cards',
        'play_identity_specific',
        'run_out_of_deck',
        'engaged_minions',
        "games_new",
        "games_won",
        "games_lost"]|GAME_OVER_OUTCOME, value: int):
        if self.IsPause():
            return

        setattr(self.content, name, getattr(self.content, name) + value)
        text = f"{name} -> {getattr(self.content, name)} (+{value})"
        if name != "operation":
            Notify.Statistics(text)

    def RecordGameOver(self, scenario: str, outcome: 'GAME_OVER_OUTCOME'):
        """Record why one finished game ended, once globally and once under its scenario.

        Only reached for a game the rules ended. Exit and Undo never send `WhenGameOver`.
        """
        if self.IsPause():
            return

        self.RecordValue(outcome, 1)

        counts = self.content.scenarios.setdefault(scenario, {})
        counts[outcome] = counts.get(outcome, 0) + 1
        self.content.scenarios = dict(sorted(self.content.scenarios.items()))

        Notify.Statistics(f"{scenario}: {outcome} x{counts[outcome]}")

    def RecordMaximum(self, name: Literal[
        "max_single_damage_dealt",
        "max_single_damage_taken",
        "max_single_damage_healed",
        "max_single_cards_drawn",
        "max_engaged_minions",
        "max_phase_kill"], value: int):
        if self.IsPause():
            return

        original_value = getattr(self.content, name)
        if original_value < value:
            setattr(self.content, name, value)
            text = f"{name} -> {value}"
            Notify.Statistics(text)

    def RecordCard(self, face: 'CardFace', method: Literal[
        "Resolve",
        "Play",
        "Resource",
        "Reveal",
        "PutIntoPlay",
        "Hero",
        "Attached",
        "Defeated",
        "Discard",
        "Cancel",
        "GameOver"
        ]):
        if self.IsPause():
            return

        card_id = face.paper.card_id

        if card_id not in self.content.data:
            self.content.data[card_id] = (0, 0, 0)
            self.content.data = dict(sorted(self.content.data.items()))

        index = -1
        if method == "Resolve":
            index = 0
        elif method in ["Play", "Resource", "Reveal", "PutIntoPlay", "Hero", "Attached"]:
            index = 1
        elif method in ["Defeated", "Discard", "Cancel", "GameOver"]:
            index = 2

        if index != -1:
            data = list(self.content.data[card_id])
            data[index] += 1
            self.content.data[card_id] = tuple(data)

            Notify.Statistics(f"{card_id} {method} x{data[index]}")

    def GetData(self, card_id: str) -> Tuple[int, int, int]:
        if card_id in self.content.data:
            return self.content.data[card_id]
        else:
            return (0, 0, 0)

    def IsNew(self, card_id: str) -> bool:
        if self.pause_internal == True:
            return False
        return card_id not in self.content.data

    ################################################################################
    #
    def SetPause(self, pause: Literal["WhenSkipping"]|bool):
        if self.pause_internal != pause:
            old_pause = self.pause_internal
            self.pause_internal = pause
            Log.Debug(CATEGORY_NAME, f"Pause: {old_pause} -> {pause}")

    def IsPause(self) -> bool:
        if isinstance(self.pause_internal, bool):
            return self.pause_internal
        from engine import Engine
        game = Engine.game
        if self.pause_internal == "WhenSkipping":
            return game.controller_manager.skip.is_skipping
        return self.pause_internal

    def CanRegisterAbility(self) -> bool:
        return self.pause_internal != True

