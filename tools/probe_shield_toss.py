"""Reproduce N10a: Shield Toss deals damage to nothing when you discard fewer cards than targets.

Run:  .venv/bin/python tools/probe_shield_toss.py [discard_count]

    discard 0 -> DealDamage(targets=[], amount=4)          villain takes 0   <- the reported bug
    discard 1 -> DealDamage(targets=[Rhino], amount=4)      villain takes 4
    discard 2 -> DealDamage(targets=[Rhino], amount=4)      villain takes 4

At discard 0 the card still forces you to pick an enemy: the play option comes with
`target_range = [1, 1]` and `all_legal_targets = [Rhino]`. You choose Rhino, the card resolves,
and `effect.targets[:0]` is empty, so nothing happens and nothing says why.

Why this is driven through the turn flow
----------------------------------------
The obvious route, the cheat DSL's `Play()`, cannot test this. It pays a card's costs without
executing its ability: the discard is taken and the hand shrinks, but `DealDamage` is never called
and `effect.targets` stays empty. A test written on that route reports 0 for a working card and a
broken one alike, so it can only ever produce a false pass. This probe answers the real
`WhenPlayerInTurn` ask instead.

Things that cost a run each, kept so they cost nobody else one
--------------------------------------------------------------
* `WhenPlayerInTurn` options are named by ACTION, not by card: Attack, Change_Form, Play, Play.
  A card is identified by `bind_id`, which is `face.card.object_id`. A face has no `object_id` of
  its own. Matching on a card name in that list never fires.
* Shield Toss needs Captain America's Shield IN PLAY, as a `ReturnToHand` cost. At setup the Shield
  is in hand, not on the table; the setup log line "were placed on table" is the deck search
  putting it into hand, which reads like the opposite. The Shield must be played first or Shield
  Toss never appears as a legal option.
* A policy must answer selection prompts, not decline them. Declining unknown prompts is what made
  three earlier probes silently select nothing and report a confident zero.
* Declining the turn ask does not advance the game: a decline-everything policy spins on
  `WhenPlayerInTurn` forever and `GameLoop()` never returns. Cap exploratory runs.
* Raising out of the policy is caught by the engine's crash handler and writes `crash.json`
  (gitignored). Use `os._exit` after printing.

Disproven: binding the targets to the discard via `SetTarget2`
--------------------------------------------------------------
The plan was to leave the discard as the cost and move the enemies to `SetTarget2` with
`range=(discarded_num, discarded_num)`, so the two could not disagree. It does not work, and this
probe is what showed it rather than another round of reading.

Two separate problems. A selector range is evaluated whenever legal targets are recomputed, which
includes building the turn's action list long before any cost is paid, so
`cost_func.Get(CostFunc.Discard)` asserts and crashes the game while merely deciding whether the
card is playable (`Has` instead of `Get` avoids that). And with that fixed, `targets2` is simply
never asked: the play option reports `target_range = [0, 0]`, no enemy prompt is ever raised even
when the policy answers every prompt it sees, and `DealDamage` gets empty targets at every discard
count. So the change makes Shield Toss deal 0 damage always, which is worse than the bug.

Note this contradicts `ability.py:61` ("Only use the first one, the others are used to check if it
has the legal target") only partly: `effect_context.py:59` really does call `AskChooseSelect` for
`targets2`, but on this ability it is not reached. Anyone retrying should find out why before
rebuilding the card around it.
"""
import os
import sys

sys.path.insert(0, '.')
import engine  # noqa: F401  must precede any game import

from unit_test.harness import GameFixture, _command


def object_id(face):
    return getattr(getattr(face, "card", None), "object_id", None)


def hand_map(fixture):
    return {object_id(f): f.name for f in fixture.player(0).hand_cards.Get()}


def resources_for(option, count):
    payment = (option.get("target_payment") or {}).get("0") or {}
    pool = [list(entry.keys())[0] for entry in (payment.get("payment") or [])]
    return pool[:count]


def cost_of(option):
    return int(((option.get("target_payment") or {}).get("0") or {}).get("cost") or 0)


def run(discard_n: int) -> None:
    state = {"fx": None, "shield": False, "toss": False, "damage": None, "log": [], "n": 0}

    def report():
        villain = state["fx"].villain(0)
        print(f"\n### discard = {discard_n}")
        for line in state["log"]:
            print("   ", line)
        print("    DealDamage      :", state["damage"] or "NEVER CALLED")
        print("    villain damage  :", villain.GetLostHealth())
        sys.stdout.flush()
        os._exit(0)

    def policy(payload, options):
        fx = state["fx"]
        state["n"] += 1
        if state["n"] > 200:
            state["log"].append("CAPPED")
            report()

        for o in options:
            if o.get("name") == "Pay_cost_Discard":
                legal = o.get("all_legal_targets") or []
                picks = [str(t) for t in legal[:discard_n]]
                state["log"].append(f"discard prompt range={o['target_num_range']} "
                                    f"answering {len(picks)}")
                return _command(o["id"], picks)

        if payload.event_name == "WhenPlayerInTurn":
            hand = hand_map(fx)
            shield = next((k for k, v in hand.items() if v == "Captain America's Shield"), None)
            toss = next((k for k, v in hand.items() if v == "Shield Toss"), None)
            if not state["shield"] and shield is not None:
                for o in options:
                    if o.get("name") == "Play" and o.get("bind_id") == shield:
                        state["shield"] = True
                        state["log"].append("playing Captain America's Shield")
                        return _command(o["id"],
                                        [str(t) for t in (o.get("all_legal_targets") or [])[:1]],
                                        resources_for(o, cost_of(o)))
            if not state["toss"] and toss is not None:
                for o in options:
                    if o.get("name") == "Play" and o.get("bind_id") == toss:
                        state["toss"] = True
                        rng = o.get("target_num_range")
                        state["log"].append(f"playing Shield Toss target_range={rng} "
                                            f"legal={o.get('all_legal_targets')}")
                        return _command(o["id"],
                                        [str(t) for t in (o.get("all_legal_targets") or [])[:rng[1]]],
                                        resources_for(o, cost_of(o)))
            if state["toss"]:
                report()

        # Answer every selection prompt; declining them is what produced false zeroes before.
        for o in options:
            rng, legal = o.get("target_num_range"), o.get("all_legal_targets")
            if rng and legal and rng[1] > 0 and str(o.get("id")) != "0":
                return _command(o["id"], [str(t) for t in legal[:rng[1]]])
        for o in options:
            if str(o.get("id")) == "0":
                return _command("0")
        return _command(options[0]["id"]) if options else _command("0")

    with GameFixture("rhino", ["captain_america"], seed=42, policy=policy) as fx:
        state["fx"] = fx
        fx.cheat("ChangeForm('Steve Rogers')")   # into hero form; Shield Toss is a Hero Action
        fx.cheat("Gain('Shield Toss')")
        for face in fx.player(0).hand_cards.Get():
            cls = type(face)
            if hasattr(cls, "DealDamage") and not getattr(cls, "_probe_spied", False):
                original = cls.DealDamage

                def spy(self, targets, amount, by_effect, *args, _o=original, **kwargs):
                    state["damage"] = {"targets": [str(t) for t in (targets or [])],
                                       "amount": amount}
                    return _o(self, targets, amount, by_effect, *args, **kwargs)

                cls.DealDamage = spy
                cls._probe_spied = True
        fx.game.GameLoop()
    report()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
