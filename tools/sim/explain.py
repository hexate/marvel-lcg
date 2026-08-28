"""Read a tuned weight set back out as a decision procedure a person can follow.

The point of scoring actions by utility rather than by a fixed ladder is that the
ordering becomes a consequence of numbers. That cuts both ways: the numbers can be
tuned by machine, and they can be read back out. This evaluates every action type
across representative board states and prints what wins, which is the tuned policy
stated as rules.

Usage:
    .venv/bin/python tools/sim/explain.py [weights.json]
"""
import json, itertools, sys
W=json.load(open(sys.argv[1] if len(sys.argv)>1 else __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)),"weights_rhino_captain_america_stun_lock.json")))
def scores(hp, press, mins, exhausted, in_ae):
    hurt=1-hp; safe=1-press; m=min(1.0, mins/2.0)
    s={}
    if not in_ae:
        s['ATTACK villain']   = W['atk_villain'] + W['atk_villain_x_safe']*safe
        if mins:
            s['ATTACK minion'] = W['atk_minion'] + W['atk_minion_x_count']*m + W['atk_minion_x_hurt']*hurt
        s['THWART']           = W['thwart'] + W['thwart_x_pressure']*press
        s['flip to ALTER-EGO']= W['flip_ae'] + W['flip_ae_x_hurt']*hurt + W['flip_ae_x_pressure']*press
        s['switch to GIANT']  = W['flip_giant'] + W['flip_giant_x_safe']*safe + W['flip_giant_x_hurt']*hurt
        s['switch to TINY']   = W['flip_tiny'] + W['flip_tiny_x_pressure']*press
        if exhausted:
            s['READY self']   = W['ready_self']
    else:
        s['flip to HERO']     = W['flip_hero'] + W['flip_hero_x_healthy']*hp + W['flip_hero_x_pressure']*press
        # multi-form heroes leave alter-ego into a specific form
        s['flip to GIANT']    = W['flip_giant'] + W['flip_giant_x_safe']*safe + W['flip_giant_x_hurt']*hurt
        s['flip to TINY']     = W['flip_tiny'] + W['flip_tiny_x_pressure']*press
        s['RECOVER']          = W['recover'] + W['recover_x_hurt']*hurt
        s['alter-ego action'] = W['ae_action']
    for cat,cost in (('stun',2),('ally',3),('damage',3),('protect',1),('board',3)):
        s['PLAY '+cat] = W['play_'+cat] + W['play_x_cost']*cost
    s['END TURN'] = W['end_turn']
    return s

print("=== HERO FORM: best action by board state ===")
print(f"{'hero HP':>8} {'scheme':>8} {'minions':>8}  ranked actions")
for hp in (1.0,0.6,0.3):
    for press in (0.0,0.4,0.8):
        for mins in (0,2):
            s=scores(hp,press,mins,False,False)
            top=sorted(s.items(), key=lambda x:-x[1])[:3]
            hpl={1.0:'full',0.6:'60%',0.3:'30%'}[hp]
            pl={0.0:'empty',0.4:'40%',0.8:'80%'}[press]
            print(f"{hpl:>8} {pl:>8} {mins:>8}  " + " > ".join(f"{k} ({v:.1f})" for k,v in top))
print()
print("=== when the hero is EXHAUSTED (hero form) ===")
for hp in (1.0,0.4):
    s=scores(hp,0.3,0,True,False)
    top=sorted(s.items(), key=lambda x:-x[1])[:3]
    print(f"  hp={hp:.0%}: " + " > ".join(f"{k} ({v:.1f})" for k,v in top))
print()
print("=== ALTER-EGO FORM ===")
for hp in (0.3,0.6,0.9):
    for press in (0.0,0.6):
        s=scores(hp,press,0,False,True)
        top=sorted(s.items(), key=lambda x:-x[1])[:3]
        print(f"  hp={hp:.0%} scheme={press:.0%}: " + " > ".join(f"{k} ({v:.1f})" for k,v in top))
print()
print("=== DEFENDING (villain attacks you) ===")
for hp in (1.0,0.7,0.4,0.2):
    hurt=1-hp
    d={'hero blocks':W['def_hero']+W['def_hero_x_hurt']*hurt,
       'ally chumps':W['def_ally']+W['def_ally_x_hurt']*hurt,
       'take the hit':W['def_decline']}
    top=sorted(d.items(), key=lambda x:-x[1])
    print(f"  hp={hp:.0%}: " + " > ".join(f"{k} ({v:.1f})" for k,v in top))
import json, itertools, sys
W=json.load(open(sys.argv[1] if len(sys.argv)>1 else __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)),"weights_rhino_captain_america_stun_lock.json")))
def scores(hp, press, mins, exhausted, in_ae):
    hurt=1-hp; safe=1-press; m=min(1.0, mins/2.0)
    s={}
    if not in_ae:
        s['ATTACK villain']   = W['atk_villain'] + W['atk_villain_x_safe']*safe
        if mins:
            s['ATTACK minion'] = W['atk_minion'] + W['atk_minion_x_count']*m + W['atk_minion_x_hurt']*hurt
        s['THWART']           = W['thwart'] + W['thwart_x_pressure']*press
        s['flip to ALTER-EGO']= W['flip_ae'] + W['flip_ae_x_hurt']*hurt + W['flip_ae_x_pressure']*press
        s['switch to GIANT']  = W['flip_giant'] + W['flip_giant_x_safe']*safe + W['flip_giant_x_hurt']*hurt
        s['switch to TINY']   = W['flip_tiny'] + W['flip_tiny_x_pressure']*press
        if exhausted:
            s['READY self']   = W['ready_self']
    else:
        s['flip to HERO']     = W['flip_hero'] + W['flip_hero_x_healthy']*hp + W['flip_hero_x_pressure']*press
        # multi-form heroes leave alter-ego into a specific form
        s['flip to GIANT']    = W['flip_giant'] + W['flip_giant_x_safe']*safe + W['flip_giant_x_hurt']*hurt
        s['flip to TINY']     = W['flip_tiny'] + W['flip_tiny_x_pressure']*press
        s['RECOVER']          = W['recover'] + W['recover_x_hurt']*hurt
        s['alter-ego action'] = W['ae_action']
    for cat,cost in (('stun',2),('ally',3),('damage',3),('protect',1),('board',3)):
        s['PLAY '+cat] = W['play_'+cat] + W['play_x_cost']*cost
    s['END TURN'] = W['end_turn']
    return s

print("=== HERO FORM: best action by board state ===")
print(f"{'hero HP':>8} {'scheme':>8} {'minions':>8}  ranked actions")
for hp in (1.0,0.6,0.3):
    for press in (0.0,0.4,0.8):
        for mins in (0,2):
            s=scores(hp,press,mins,False,False)
            top=sorted(s.items(), key=lambda x:-x[1])[:3]
            hpl={1.0:'full',0.6:'60%',0.3:'30%'}[hp]
            pl={0.0:'empty',0.4:'40%',0.8:'80%'}[press]
            print(f"{hpl:>8} {pl:>8} {mins:>8}  " + " > ".join(f"{k} ({v:.1f})" for k,v in top))
print()
print("=== when the hero is EXHAUSTED (hero form) ===")
for hp in (1.0,0.4):
    s=scores(hp,0.3,0,True,False)
    top=sorted(s.items(), key=lambda x:-x[1])[:3]
    print(f"  hp={hp:.0%}: " + " > ".join(f"{k} ({v:.1f})" for k,v in top))
print()
print("=== ALTER-EGO FORM ===")
for hp in (0.3,0.6,0.9):
    for press in (0.0,0.6):
        s=scores(hp,press,0,False,True)
        top=sorted(s.items(), key=lambda x:-x[1])[:3]
        print(f"  hp={hp:.0%} scheme={press:.0%}: " + " > ".join(f"{k} ({v:.1f})" for k,v in top))
print()
print("=== DEFENDING (villain attacks you) ===")
for hp in (1.0,0.7,0.4,0.2):
    hurt=1-hp
    d={'hero blocks':W['def_hero']+W['def_hero_x_hurt']*hurt,
       'ally chumps':W['def_ally']+W['def_ally_x_hurt']*hurt,
       'take the hit':W['def_decline']}
    top=sorted(d.items(), key=lambda x:-x[1])
    print(f"  hp={hp:.0%}: " + " > ".join(f"{k} ({v:.1f})" for k,v in top))
