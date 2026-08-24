from core import *

GAME_OVER_OUTCOME = Literal[
    "games_won_villain_defeated",
    "games_won_other",
    "games_lost_main_scheme",
    "games_lost_eliminated",
    "games_lost_encounter_deck",
    "games_lost_other",
]

@dataclass
class Statistics:
    version: str = field(default="")

    operation: int = field(default=0)

    # Old version name
    crc: str = field(default="")

    took_damage: int = field(default=0)
    dealt_damage: int = field(default=0)
    healed_damage: int = field(default=0)
    drawn_cards: int = field(default=0)
    removed_threats: int = field(default=0)

    maximum_single_damage: int = field(default=0)
    maximum_single_took_damage: int = field(default=0)
    maximum_single_healing: int = field(default=0)
    maximum_single_draw: int = field(default=0)

    game_won: int = field(default=0)
    game_lost: int = field(default=0)

    # New version name
    total_damage_taken: int = field(default=0)
    total_damage_dealt: int = field(default=0)
    total_damage_healed: int = field(default=0)
    total_cards_drawn: int = field(default=0)
    total_threats_removed: int = field(default=0)

    max_single_damage_dealt: int = field(default=0)
    max_single_damage_taken: int = field(default=0)
    max_single_damage_healed: int = field(default=0)
    max_single_cards_drawn: int = field(default=0)
    max_phase_kill: int = field(default=0)

    generate_resources_r: int = field(default=0)
    generate_resources_b: int = field(default=0)
    generate_resources_y: int = field(default=0)
    generate_resources_g: int = field(default=0)

    play_aspect_aggression: int = field(default=0)
    play_aspect_justice: int = field(default=0)
    play_aspect_leadership: int = field(default=0)
    play_aspect_protection: int = field(default=0)
    play_aspect_pool: int = field(default=0)
    play_basic_cards: int = field(default=0)
    play_identity_specific: int = field(default=0)

    engaged_minions: int = field(default=0)
    max_engaged_minions: int = field(default=0)

    run_out_of_deck: int = field(default=0)

    games_new: int = field(default=0)
    games_won: int = field(default=0)
    games_lost: int = field(default=0)

    achievement_first_blood: int = field(default=0)
    achievement_double_kill: int = field(default=0)
    achievement_triple_kill: int = field(default=0)
    achievement_ultra_kill: int = field(default=0)
    achievement_rampage: int = field(default=0)

    # Why the game ended, from `GAME_OVER_REASON` in game/world/game_over.py. `games_won` and
    # `games_lost` count the outcome; these keep the reason, which was reaching the statistics
    # hook on the message and being dropped there.
    games_won_villain_defeated: int = field(default=0)
    games_won_other: int = field(default=0)
    games_lost_main_scheme: int = field(default=0)
    games_lost_eliminated: int = field(default=0)
    games_lost_encounter_deck: int = field(default=0)
    games_lost_other: int = field(default=0)

    # <scenario>: {<outcome field above>: count}. Expert and challenge runs are keyed apart from
    # the standard ones, since they are not the same fight.
    scenarios: Dict[str, Dict[str, int]] = field(default_factory=lambda: {})

    data: Dict[str, Tuple[int, int, int]] = field(default_factory=lambda: {})

    def UpdateVersion(self):
        attributes = [
            ('game_won', 'games_won'),
            ('game_lost', 'games_lost'),
            ('took_damage', 'total_damage_taken'),
            ('dealt_damage', 'total_damage_dealt'),
            ('healed_damage', 'total_damage_healed'),
            ('drawn_cards', 'total_cards_drawn'),
            ('removed_threats', 'total_threats_removed'),
            ('maximum_single_damage', 'max_single_damage_dealt'),
            ('maximum_single_took_damage', 'max_single_damage_taken'),
            ('maximum_single_healing', 'max_single_damage_healed'),
            ('maximum_single_draw', 'max_single_cards_drawn')
        ]

        for attr, target in attributes:
            old_value = getattr(self, attr)
            if hasattr(self, attr) and old_value > 0:
                setattr(self, target, old_value)
            delattr(self, attr)
        
        crc = ""
        attr = 'crc'
        if hasattr(self, attr):
            crc = getattr(self, attr)
            delattr(self, attr)
        return crc

