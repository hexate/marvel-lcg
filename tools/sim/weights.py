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
    "play_reform": 6.0,     # Resize: change form and draw, for nothing
    "play_engine": 7.0,
    "play_allybuff": 6.0,   # keeps allies alive, and allies are the activation budget     # pays out on every future form change, so it compounds
    "play_damage": 5.0,
    "play_protect": 5.0,
    "play_board": 3.0,
    "play_other": 1.0,
    "play_build_x_early": 0.0,  # measured worse on 50 seeds; kept as a knob, off
    "play_x_cost": -0.8,            # cheaper is better, hand size is the budget
    # --- form
    "flip_ae": -2.0,
    "flip_ae_x_hurt": 6.0,
    "flip_ae_x_pressure": -6.0,
    "flip_hero": 1.0,
    # Multi-form heroes. Ant-Man's Giant is ATK 3 / DEF 3 but hand size 4, Tiny is
    # THW 2 with hand size 5, and each change pays out on arrival: Giant deals 1
    # damage, Tiny removes 1 threat. Scoring them as one "hero form" throws that away.
    "flip_giant": 1.0,
    "flip_giant_x_safe": 4.0,
    "flip_giant_x_hurt": -1.0,
    "flip_tiny": 1.0,
    "flip_tiny_x_pressure": 6.0,
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
    # Forecast-driven rules from how people describe playing. All default to zero: with
    # them on, average damage rose and wins fell by two thirds, because a safer game
    # raises the mean and removes the tail that actually closes. Left in as features the
    # tuner can switch on now that fitness rewards the tail.
    "def_x_incoming": 0.0,
    "def_x_lethal": 0.0,
    "def_ally_x_incoming": 0.0,
    "def_ally_x_lethal": 0.0,
    "flip_ae_x_lethal": 0.0,
    "flip_ae_x_scheme_lethal": 0.0,
    "flip_hero_x_scheme_lethal": 0.0,
    "play_stun_x_incoming": 0.0,      # a stun cancels the attack that is coming
    "play_protect_x_lethal": 0.0,
    "play_aoe_x_minions": 0.0,
    "play_aoe": 4.0,
    "atk_minion_x_guard": 0.0,       # the villain cannot be reached past a Guard minion
}
