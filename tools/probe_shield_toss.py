"""Diagnostic probe for N10a: can Shield Toss's damage be observed from a test?

Answer so far: not through the cheat DSL's `Play()`. This script is the evidence, and is kept so
the next attempt starts from what is already ruled out rather than repeating it.

Run:  .venv/bin/python tools/probe_shield_toss.py [discard_count]

What it sets up
---------------
`GameFixture("rhino", ["captain_america"])` from the I2 harness builds a real game with no replay
file. Two things about that hero make it convenient: Captain America's Shield is put into play
during setup, which is a cost Shield Toss requires, and the starter deck holds two Shield Toss.

What it establishes
-------------------
1. The discard really is driven. Answering the `Pay_cost_Discard` prompt with N cards drops the
   hand by exactly N, confirmed at N = 0, 1 and 2. So the policy plumbing works.

2. The primary target selection never prompts, and it does not need to. `UpdateLegalTargets`
   gives `all_legal_targets = [Rhino]` and `target_range = (1, 1)`, because `GetTargetRange` caps
   the max by the number of legal faces. A forced single choice is taken without asking.

3. Despite that, `DealDamage` is NEVER called and `effect.targets` is empty after the play. The
   ability body does not run on this path. The costs do: the discard is taken and the hand
   shrinks.

So `Play()` in `game/world/cheat/cheat_cmd_helper.py` pays a card's costs without executing its
ability. Any test that measures a card's EFFECT through this cheat is measuring nothing, and will
report 0 for a working card and a broken one alike. That is what made the first attempt at N10a
unfalsifiable.

Next step
---------
Drive the card through the real turn flow instead, answering the `WhenPlayerChooseAbility` ask
that lists Shield Toss, rather than forcing it through the cheat.
"""
import sys

sys.path.insert(0, '.')
import engine  # noqa: F401  must precede any game import

from unit_test.harness import GameFixture, _command


def build_policy(discard_n: int, log: list):
    def policy(payload, options):
        log.append({
            "event": payload.event_name,
            "prompt": (payload.prompt_text or "")[:60],
            "options": [(o.get("name"), o.get("target_num_range")) for o in options],
        })
        for o in options:
            if o.get("name") == "Pay_cost_Discard":
                legal = o.get("all_legal_targets") or []
                return _command(o["id"], [str(t) for t in legal[:discard_n]])
        for o in options:
            if str(o.get("id")) == "0":
                return _command("0")
        return _command(options[0].get("id")) if options else _command("0")
    return policy


def main() -> int:
    discard_n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    log: list = []

    with GameFixture("rhino", ["captain_america"], seed=42,
                     policy=build_policy(discard_n, log)) as fx:
        fx.cheat("ChangeForm('Steve Rogers')")
        fx.cheat("Gain('Shield Toss')")

        player = fx.player(0)
        villain = fx.villain(0)
        face = [f for f in player.hand_cards.Get() if f.name == "Shield Toss"][0]
        effect = face.effect.Find(func_name="Play")[0]

        effect.context.initiator = player
        effect.checker.UpdateLegalTargets()
        legal = [str(x) for x in effect.context.all_legal_targets]
        target_range = effect.context.target_range

        seen: dict = {}
        face_cls = type(face)
        original = face_cls.DealDamage

        def spy(self, targets, amount, by_effect, *args, **kwargs):
            seen["targets"] = [str(t) for t in (targets or [])]
            seen["amount"] = amount
            return original(self, targets, amount, by_effect, *args, **kwargs)

        face_cls.DealDamage = spy
        hand_before = player.hand_cards.GetSize()
        damage_before = villain.GetLostHealth()
        try:
            fx.cheat("Play('Shield Toss')")
        finally:
            face_cls.DealDamage = original

        print(f"discard asked for      : {discard_n}")
        print(f"prompts raised         : {len(log)}  {[e['options'] for e in log]}")
        print(f"legal targets / range  : {legal} / {target_range}")
        print(f"hand size              : {hand_before} -> {player.hand_cards.GetSize()}")
        print(f"DealDamage             : {seen or 'NEVER CALLED'}")
        print(f"effect.targets after   : {[str(t) for t in effect.context.targets_internal]}")
        print(f"villain damage         : {damage_before} -> {villain.GetLostHealth()}")

        discarded = hand_before - player.hand_cards.GetSize()
        ok = discarded == discard_n
        print(f"\ndiscard plumbing works : {ok} (hand fell by {discarded})")
        print("ability body ran       : " + ("yes" if seen else "NO -- Play() pays costs "
                                             "without running the ability"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
