"""Default utility weights.

Kept free of game imports so `tune.py` can read them without booting the engine.
"""

DEFAULT_WEIGHTS = {
    # --- attacking
    "atk_villain": 5.0,
    "atk_villain_x_safe": 3.0,      # scaled by how much scheme headroom is left
    "atk_minion": 4.0,
    "atk_minion_x_count": 4.0,      # scaled by how many minions are engaged
    "atk_minion_x_hurt": 2.0,       # scaled by how hurt the hero is
    # --- thwarting
    "thwart": 2.0,
    "thwart_x_pressure": 9.0,       # scaled by fraction of scheme capacity used
    # --- playing cards
    "play_ally": 6.0,
    "play_stun": 6.5,
    "play_damage": 5.0,
    "play_protect": 5.0,
    "play_board": 3.0,
    "play_other": 1.0,
    "play_x_cost": -0.8,            # cheaper is better, hand size is the budget
    # --- form
    "flip_ae": -2.0,
    "flip_ae_x_hurt": 6.0,
    "flip_ae_x_pressure": -6.0,
    "flip_hero": 1.0,
    "flip_hero_x_healthy": 4.0,
    "flip_hero_x_pressure": 4.0,
    "recover": 1.0,
    "recover_x_hurt": 6.0,
    # --- misc actions
    "ready_self": 7.0,              # only scored when the hero is exhausted
    "hero_action": 1.5,
    "ae_action": 4.0,
    # --- the floor: anything scoring below this ends the turn
    "end_turn": 0.5,
    # --- defending (separate prompt)
    "def_hero": 3.0,
    "def_hero_x_hurt": 3.0,
    "def_ally": 1.0,
    "def_ally_x_hurt": 4.0,
    "def_decline": 1.5,
}
