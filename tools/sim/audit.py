"""Offered-versus-taken audit.

Every large improvement to the policy so far came from finding something the engine
offered that the policy never took: target counts answered wrong, forced choices
declined, the discard-and-redraw step skipped, form changes unrecognised, response
windows ignored. Tuning numbers moved results by tenths; each of those moved whole
points.

So rather than guess, count. This runs a set of seeds and reports, per
(event, option name) and per card, how often something was on offer and how often it
was chosen. A high offered count with a zero taken count is a lead.

Usage:
    .venv/bin/python tools/sim/audit.py <scenario> <deck> <mode> [seeds...]
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO)
os.chdir(REPO)

import engine  # noqa: F401  must precede any game import
from engine import Engine

Engine.SaveCrash = staticmethod(lambda: None)

from unit_test.harness import GameFixture  # noqa: E402
from policy import Heuristic, oid  # noqa: E402

offered = collections.Counter()
taken = collections.Counter()
card_offered = collections.Counter()
card_taken = collections.Counter()


class Auditing(Heuristic):

    def names_in_play(self):
        n = {}
        try:
            p = self.fx.player(0)
            areas = [p.hand_cards, p.allies, p.supports, p.area_hero]
            for a in areas:
                for f in a.Get():
                    n[oid(f)] = f.name
            for f in p.GetIdentity().GetInventoryDeck().Get():
                n[oid(f)] = f.name
        except Exception:
            pass
        return n

    def decide(self, payload, options):
        nm = self.names_in_play()
        cmd = super().decide(payload, options)
        try:
            chosen = json.loads(cmd).get("id")
        except Exception:
            chosen = None
        for o in options:
            key = (payload.event_name, str(o.get("name")))
            offered[key] += 1
            card = nm.get(o.get("bind_id"))
            if card:
                card_offered[(str(o.get("name")), card)] += 1
            if chosen and str(o.get("id")) == str(chosen):
                taken[key] += 1
                if card:
                    card_taken[(str(o.get("name")), card)] += 1
        return cmd


def main():
    scen, deck, mode = sys.argv[1], sys.argv[2], sys.argv[3]
    seeds = [int(x) for x in sys.argv[4:]] or [11, 23, 37, 49, 61, 73, 85, 97, 109, 121]
    for sd in seeds:
        pol = Auditing(mode)
        fx = GameFixture(scen, [deck], seed=sd, policy=pol)
        pol.fx = fx
        with fx:
            try:
                fx.game.GameLoop()
            except Exception:
                pass
    rows = []
    for k, n in offered.items():
        rows.append((n - taken.get(k, 0), n, taken.get(k, 0), k))
    rows.sort(reverse=True)
    out = {
        "by_option": [[list(k), n, t] for _gap, n, t, k in rows[:30]],
        "by_card": [[list(k), n, card_taken.get(k, 0)]
                    for k, n in card_offered.most_common(40)],
    }
    sys.__stdout__.write("@@@" + json.dumps(out) + "\n")
    sys.__stdout__.flush()
    os._exit(0)


main()
