"""Solo 'clock' for each scenario: how much threat lands per round vs how much you must
remove, and how much damage the villain needs. Straight from card data, no simulation."""
import json, os, sys, collections

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(REPO)

cards = {}
for f in ('data/cards.json', 'data/cards_custom.json'):
    try:
        db = json.load(open(f))
    except Exception:
        continue
    for s, entries in db.items():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if isinstance(e, dict) and 'card_id' in e:
                cards.setdefault(e['card_id'], e)


def num(v, default=0):
    if v is None:
        return default
    s = str(v).replace('*', '').strip()
    try:
        return int(s)
    except Exception:
        return default


def per_player(v):
    """'12*' means 12 per player; solo that is just 12."""
    return num(v)


def enc_cards(scen):
    ids = list(scen.get('encounters') or [])
    for group in ('encounter_sets', 'modular_sets'):
        for name in (scen.get(group) or []):
            p = f'data/encounter_sets/{name}.json'
            if os.path.exists(p):
                ids += json.load(open(p)).get('encounters', [])
    return ids


def analyse(name):
    scen = json.load(open(f'data/scenarios/{name}.json'))
    row = {'scenario': scen.get('name', name), 'file': name}

    stages = []
    for entry in scen.get('villain', []):
        best = None
        for cid in str(entry).split(','):
            e = cards.get(cid)
            if e and e.get('type') == 'Villain':
                best = e
                break
        if not best:
            continue
        d = best.get('desc', {})
        stages.append({'name': best['name'].lstrip('* '), 'hp': per_player(d.get('HP')),
                       'atk': num(d.get('ATK')), 'sch': num(d.get('SCH'))})
    row['stages'] = stages
    row['total_hp'] = sum(s['hp'] for s in stages)

    schemes = []
    for entry in scen.get('schemes', []):
        for cid in str(entry).split(','):
            e = cards.get(cid)
            if not e or e.get('type') != 'MainScheme':
                continue
            d = e.get('desc', {})
            if 'TargetThreat' not in d and 'StartingThreat' not in d:
                continue
            schemes.append({'name': e['name'], 'start': per_player(d.get('StartingThreat')),
                            'target': per_player(d.get('TargetThreat')),
                            'accel': per_player(d.get('EscalationThreat'))})
    row['schemes'] = schemes
    row['runway'] = sum(max(0, s['target'] - s['start']) for s in schemes)

    kinds = collections.Counter()
    for cid in enc_cards(scen):
        e = cards.get(cid)
        kinds[e.get('type') if e else '?'] += 1
    row['encounter'] = dict(kinds)
    row['deck_size'] = sum(kinds.values())
    row['minion_pct'] = round(100.0 * kinds.get('Minion', 0) / max(1, sum(kinds.values())), 0)

    # Threat per round with no thwarting at all: acceleration always, plus the villain's
    # scheme value on any round you spend in alter-ego.
    accel = schemes[0]['accel'] if schemes else 0
    sch = stages[0]['sch'] if stages else 0
    row['accel'] = accel
    row['villain_sch'] = sch
    row['idle_rounds'] = round(row['runway'] / accel, 1) if accel else None
    row['ae_rounds'] = round(row['runway'] / max(1, accel + sch), 1)
    return row


if __name__ == '__main__':
    names = sys.argv[1:]
    rows = [analyse(n) for n in names]
    json.dump(rows, open(os.path.join(REPO, 'out', 'scenario_clock.json'), 'w'), indent=1)
    N = 10   # a normal solo game length
    print(f"{'scenario':22s} {'HP':>4s} {'dmg/rd':>7s} {'runway':>7s} {'accel':>6s} {'SCH':>4s} "
          f"{'thw/rd':>7s} {'idle':>5s} {'min%':>5s}")
    for r in rows:
        # threat placed over N rounds assuming 1 round in 3 spent in alter-ego
        rate = r['accel'] + r['villain_sch'] / 3.0
        need = max(0.0, rate * N - r['runway'])
        r['dmg_per_round'] = round(r['total_hp'] / N, 1)
        r['thwart_per_round'] = round(need / N, 2)
        print(f"{r['scenario'][:22]:22s} {r['total_hp']:4d} {r['dmg_per_round']:7.1f} "
              f"{r['runway']:7d} {r['accel']:6d} {r['villain_sch']:4d} "
              f"{r['thwart_per_round']:7.2f} {str(r['idle_rounds']):>5s} {r['minion_pct']:5.0f}")
