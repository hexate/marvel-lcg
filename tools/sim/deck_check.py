"""Understand a deck before tuning it.

This exists because of a mistake. Ant-Man was tuned for twenty minutes before anyone
checked whether the policy could see his cards. It could not: his form-change payoffs
were never taken, his compounding upgrades were filed as generic board filler, and the
second ability on a two-ability card was invisible. The tuner did its job perfectly and
optimised a hero with his kit switched off, then correctly concluded he should stop
changing form, which is the opposite of how he is played.

So: run this first, on every new deck, and resolve what it flags before tuning. A
tuner cannot tell you that a card is invisible to it. It will just quietly route
around the card and hand you a confident set of weights.

Usage:
    .venv/bin/python tools/sim/deck_check.py <deck name>
    .venv/bin/python tools/sim/deck_check.py captain_america_stun_lock
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO)
os.chdir(REPO)

import engine  # noqa: F401,E402
from policy import (card_text, changes_form, deals_damage, disables,  # noqa: E402
                    defence_payoff, form_engine, protects, removes_threat)

# Mechanics the policy has no model of. A card carrying one of these is doing something
# the scorer cannot value, which is a blind spot whether or not the card looks minor.
UNMODELLED = [
    "retaliate", "overkill", "piercing", "guard", "quickstrike", "steady",
    "hinder", "surge", "setup", "uses (", "counter", "search your deck",
    "reduce the cost", "reduces the cost", "attach", "team-up", "restricted",
    "ally limit", "side scheme", "hand size", "draw",
]

# Playability conditions the scorer does not check, so it can rank a card it cannot cast.
CONDITIONS = [
    "play only if", "while you are in", "if you are in", "hero action", "alter-ego action",
]


def load_cards():
    cards = {}
    for f in ("data/cards.json", "data/cards_custom.json"):
        if not os.path.exists(f):
            continue
        for _s, entries in json.load(open(f)).items():
            if not isinstance(entries, list):
                continue
            for e in entries:
                if isinstance(e, dict) and "card_id" in e:
                    cards.setdefault(e["card_id"], e)
    return cards


def find_deck(name):
    for sub in ("custom", "starter", ""):
        p = os.path.join("deck", sub, name + ".json")
        if os.path.exists(p):
            return json.load(open(p))
    raise SystemExit("deck not found: " + name)


class Face:
    def __init__(self, cid):
        self.paper = type("P", (), {"card_id": cid})()


def category(face, ctype):
    if ctype == "Ally":
        return "ally"
    if form_engine(face) and ctype in ("Upgrade", "Support"):
        return "engine"
    if changes_form(face):
        return "reform"
    if disables(face):
        return "stun"
    if defence_payoff(face):
        return "defence"
    if protects(face):
        return "protect"
    if deals_damage(face) or removes_threat(face):
        return "damage"
    if ctype in ("Upgrade", "Support"):
        return "board"
    return "other"


def main():
    name = sys.argv[1]
    cards = load_cards()
    deck = find_deck(name)
    ids = deck.get("hero_deck", []) + deck.get("player_deck", [])
    counts = {}
    for cid in ids:
        counts[cid] = counts.get(cid, 0) + 1

    print("deck: %s   (%d cards)\n" % (deck.get("name", name), len(ids)))
    print("%-30s %-9s %4s %-8s %s" % ("card", "type", "n", "category", "flags"))
    junk, blind, conditional, unknown = [], [], [], []
    for cid in dict.fromkeys(ids):
        e = cards.get(cid)
        if e and e.get("full_link"):
            e = cards.get(e["full_link"], e)
        if not e:
            unknown.append(cid)
            continue
        ctype = e.get("type", "?")
        if ctype in ("Hero", "AlterEgo", "Obligation", "Treachery", "Minion",
                     "SideScheme", "Attachment", "Environment"):
            continue
        nm = e.get("name", cid)
        face = Face(cid)
        text = card_text(face)
        cat = category(face, ctype)
        flags = []
        hits = [k for k in UNMODELLED if k in text]
        if hits:
            flags.append("unmodelled: " + ",".join(hits[:3]))
            blind.append((nm, hits))
        conds = [k for k in CONDITIONS if k in text]
        if conds:
            flags.append("conditional")
            conditional.append((nm, conds))
        # "Hero Interrupt", "Forced Response", "Hero Response" all mean the card is
        # played at a window rather than on your turn
        window = "response" in text or "interrupt" in text
        if window:
            flags.append("played at a window")
        if cat == "other" and ctype != "Resource" and not window:
            flags.append("UNCLASSIFIED")
            junk.append(nm)
        print("%-30s %-9s %4d %-8s %s" % (nm[:30], ctype, counts[cid], cat,
                                          "; ".join(flags)))

    print("\n--- resolve before tuning ---")
    if unknown:
        print("  %d card ids not in the database: %s" % (len(unknown), ", ".join(unknown[:6])))
    if junk:
        print("  %d cards fall in the junk category, so the scorer ranks them last:" % len(junk))
        for n in junk:
            print("      %s" % n)
    if blind:
        print("  %d cards use mechanics the policy has no model of:" % len(blind))
        for n, h in blind:
            print("      %-28s %s" % (n[:28], ",".join(h[:4])))
    if conditional:
        print("  %d cards are conditionally playable; the scorer does not check the"
              " condition:" % len(conditional))
    if not (junk or blind or unknown):
        print("  nothing flagged: every card lands in a category the scorer values.")


main()
