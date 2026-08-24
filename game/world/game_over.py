from typing import Final
from core import *
from game.world import *
from game.effect import *
from game.statistics.statistics import GAME_OVER_OUTCOME

GAME_OVER_REASON_RULE = Literal[
    "There were no cards in either the encounter deck or the encounter discard pile",
    "All players were eliminated",
    "The Final Stage of the Villain was Defeated",
    "The Final Stage of the Main Scheme was Completed",
    "The Main Scheme was Completed",
]

GAME_OVER_REASON_SIMPLE = Literal[
    "Players Won",
    "Players Lost",
]

GAME_OVER_REASON_EXIT = Literal[
    "Exit",
    "Undo",
]

GAME_OVER_REASON = GAME_OVER_REASON_RULE|GAME_OVER_REASON_SIMPLE|GAME_OVER_REASON_EXIT

GAME_OVER_OUTCOME_MAP: Dict[GAME_OVER_REASON, 'GAME_OVER_OUTCOME|None'] = {
    "There were no cards in either the encounter deck or the encounter discard pile": "games_lost_encounter_deck",
    "All players were eliminated": "games_lost_eliminated",
    "The Final Stage of the Villain was Defeated": "games_won_villain_defeated",
    "The Final Stage of the Main Scheme was Completed": "games_lost_main_scheme",
    # A non-final stage that ends the game when it completes, which a few scenarios have.
    "The Main Scheme was Completed": "games_lost_main_scheme",
    # A card or a scenario script calling the game rather than a rule, so the reason is only
    # the outcome. Kept separate instead of folded into the rows above, which would claim to
    # know something the game never said.
    "Players Won": "games_won_other",
    "Players Lost": "games_lost_other",
    # Neither is a finished game.
    "Exit": None,
    "Undo": None,
}

# The same map keyed by the plain string a game-over message carries, with the two non-outcomes
# dropped, so a caller holding a `str` does not have to prove it is a `GAME_OVER_REASON` first.
GAME_OVER_OUTCOME_BY_REASON: Dict[str, 'GAME_OVER_OUTCOME'] = {
    reason: outcome
    for reason, outcome in GAME_OVER_OUTCOME_MAP.items()
    if outcome != None
}

GAME_OVER_REASON_MAP: Dict[GAME_OVER_REASON, bool|None] = {
    "There were no cards in either the encounter deck or the encounter discard pile": False,
    "All players were eliminated": False,
    "The Final Stage of the Villain was Defeated": True,
    "The Final Stage of the Main Scheme was Completed": False,
    "The Main Scheme was Completed": False,
    "Players Won": True,
    "Players Lost": False,
    "Exit": None,
    "Undo": None,
}

class GameOverReason:

    def __init__(self, world: 'World') -> None:
        self.players_won: bool
        self.by_effect: 'Effect'
        self.reason: str|None = None

        self.world: Final = world

    def SetGameOver(self, reason: 'GAME_OVER_REASON', by_effect: 'Effect|None'):
        if not self.is_game_over:
            from engine import Engine
            game = Engine.game
            from game.message import Message

            players_won = None

            if reason == "Exit":
                game.state.SetExitStatus("Exit")
                Engine.statistics.Reset()
            elif reason == "Undo":
                game.state.SetExitStatus("Undo")
            else:
                game.state.SetExitStatus("")

            players_won = GAME_OVER_REASON_MAP[reason]

            if players_won != None:
                assert by_effect != None
                message = Message.WhenGameOver(players_won, reason, by_effect)
                message.Send()

                self.players_won = message.players_won
                self.by_effect = message.by_effect
                self.reason = message.reason
            else:
                self.reason = reason

    def SetPlayersWon(self, player_won: bool, by_effect: 'Effect'):
        if player_won:
            reason = "Players Won"
        else:
            reason = "Players Lost"
        return self.SetGameOver(reason, by_effect)

    def SetGameOverByRule(self, reason: 'GAME_OVER_REASON_RULE'):
        from game.effect.rule import GameRule
        from game.operate.worlds import Worlds
        scheme = Worlds.GetAllMainSchemes(self.world)[0]
        effect = GameRule(scheme, display_name=reason)
        return self.SetGameOver(reason, effect)

    def SetUndo(self):
        return self.SetGameOver("Undo", None)

    def SetExit(self):
        return self.SetGameOver("Exit", None)

    @property
    def is_game_over(self) -> bool:
        return self.reason != None

    @property
    def is_game_exit_or_undo(self) -> bool:
        return self.reason in ["Exit", "Undo"]

    @property
    def is_exit(self) -> bool:
        return self.reason == "Exit"

