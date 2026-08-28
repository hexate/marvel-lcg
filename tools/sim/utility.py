"""Utility-scoring policy.

The priority ladder in `policy.py` can only say "always do A before B". It cannot say
"A is worth 3.2 here and B is worth 3.4", which is what most real decisions are, and
tuning it meant hand-guessing an ordering for every new situation.

This scores every legal action with a weighted sum of board features and takes the
best one. The ordering becomes a consequence of numbers, and numbers can be tuned by
machine against the simulator instead of by hand. All the prompt handling that took
so long to get right (target counts, forced choices, response windows, interrupts,
typed resource costs, end-of-turn cycling) is inherited unchanged from Heuristic.

Weights live in a plain dict so `tune.py` can search them and so the tuned result can
be read back out as a human decision procedure.
"""
import json

from weights import DEFAULT_WEIGHTS
from policy import (Heuristic, _command, card_cost, changes_form, cost_of,
                    deals_damage, disables, form_engine, oid, protects,
                    removes_threat, summons_ally, type_of)

# Starting point. Roughly reproduces the hand-tuned ladder so the search begins
# somewhere sane rather than at random.

def load_weights(path):
    w = dict(DEFAULT_WEIGHTS)
    if path:
        with open(path) as f:
            w.update(json.load(f))
    return w


class UtilityPolicy(Heuristic):

    def __init__(self, mode="balanced", weights=None):
        super().__init__(mode)
        self.w = dict(DEFAULT_WEIGHTS)
        if weights:
            self.w.update(weights)

    def danger_threat(self):
        sch = 0
        try:
            for f in self.world().scenario.area_villain.Get():
                sch = max(sch, int(getattr(f, "scheme", 0) or 0))
        except Exception:
            pass
        return sch + 3

    # ------------------------------------------------------------------ context
    def context(self):
        mins = self.minions()
        try:
            allies = self.fx.player(0).allies.GetSize()
        except Exception:
            allies = 0
        try:
            ident = self.hero_face()
            exhausted = not ident.IsReady()
        except Exception:
            exhausted = False
        return {
            "hp": self.hp_frac(),
            "hurt": 1.0 - self.hp_frac(),
            "press": self.threat_pressure(),
            "safe": 1.0 - self.threat_pressure(),
            "minions": min(1.0, len(mins) / 2.0),
            "has_minion": 1.0 if mins else 0.0,
            "allies": min(1.0, allies / 3.0),
            "exhausted": 1.0 if exhausted else 0.0,
        }

    def card_category(self, face):
        if face is None:
            return "other"
        t = type_of(face)
        if t == "Ally" or summons_ally(face):
            return "ally"
        # Only permanents. Moxie also pays out on a form change, but it is a Response
        # that belongs in the change-form window; treating it as a turn play wastes it.
        if form_engine(face) and t in ("Upgrade", "Support"):
            return "engine"
        if changes_form(face):
            return "reform"
        if disables(face):
            return "stun"
        if protects(face):
            return "protect"
        if deals_damage(face) or removes_threat(face):
            return "damage"
        if t in ("Upgrade", "Support"):
            return "board"
        return "other"

    # ------------------------------------------------------------------ scoring
    def score_option(self, o, hand, ctx):
        """Return (score, kind) for one legal option."""
        w = self.w
        name = str(o.get("name") or "")
        upper = name.upper().replace("_", "")

        if "CANDOTHISALLDAY" in upper or "READY" in upper:
            # only worth anything when the hero is actually exhausted
            return (w["ready_self"] * ctx["exhausted"], "ready")

        if name == "Play":
            face = hand.get(o.get("bind_id"))
            cat = self.card_category(face)
            base = w.get("play_" + cat, w["play_other"])
            return (base + w["play_x_cost"] * cost_of(o), "play")

        if name == "Attack":
            en = self.enemies()
            legal = list(o.get("all_legal_targets") or [])
            kinds = {en.get(t) for t in legal}
            if "villain" in kinds:
                return (w["atk_villain"] + w["atk_villain_x_safe"] * ctx["safe"], "attack")
            if "minion" in kinds:
                return (w["atk_minion"]
                        + w["atk_minion_x_count"] * ctx["minions"]
                        + w["atk_minion_x_hurt"] * ctx["hurt"], "attack_minion")
            return (w["atk_villain"], "attack")

        if name == "Thwart":
            return (w["thwart"] + w["thwart_x_pressure"] * ctx["press"], "thwart")

        if name == "Recover":
            return (w["recover"] + w["recover_x_hurt"] * ctx["hurt"], "recover")

        if name == "Alter-Ego_Action":
            return (w["ae_action"], "ae_action")

        # A card with two abilities numbers them: Hero_Action and Hero_Action_1. Matching
        # the bare name only left the second ability on Wrist Gauntlets unused 24 times
        # in ten games.
        if name.startswith("Action") or name.startswith("Hero_Action"):
            return (w["hero_action"], "action")

        form = self.option_form(name)
        if form is not None or name == "Change_Form":
            to_ae = (form == "ae") or (name == "Change_Form" and not self.is_ae())
            if to_ae:
                return (w["flip_ae"]
                        + w["flip_ae_x_hurt"] * ctx["hurt"]
                        + w["flip_ae_x_pressure"] * ctx["press"], "flip_ae")
            if form == "giant":
                return (w["flip_giant"]
                        + w["flip_giant_x_safe"] * ctx["safe"]
                        + w["flip_giant_x_hurt"] * ctx["hurt"], "flip_hero")
            if form == "tiny":
                return (w["flip_tiny"]
                        + w["flip_tiny_x_pressure"] * ctx["press"], "flip_hero")
            return (w["flip_hero"]
                    + w["flip_hero_x_healthy"] * ctx["hp"]
                    + w["flip_hero_x_pressure"] * ctx["press"], "flip_hero")

        return (w["play_other"], "other")

    # ------------------------------------------------------------------ turn
    def turn_inner(self, options):
        hand = self.hand()
        ctx = self.context()
        # Hard floor, not a weight. A dense damage fitness never punishes losing to the
        # scheme, so the tuner will happily race past the point of no return: 0.1 thwarts
        # a game while four losses in ten were the main scheme completing.
        # One villain phase can add acceleration plus the villain's scheme value plus a
        # boost card, so the scheme jumps by about four. Waiting until headroom is 2
        # means the floor never fires: threat goes 3 -> completed between decisions.
        if self.headroom() <= self.danger_threat():
            thw = [o for o in options if o.get("name") == "Thwart"]
            if thw:
                self.tel["thwart"] += 1
                return self.aimed(thw[0], hand, self.schemes(), ("main", "side"))
        best = None
        for o in options:
            score, kind = self.score_option(o, hand, ctx)
            if best is None or score > best[0]:
                best = (score, kind, o)
        if best is None or best[0] < self.w["end_turn"]:
            self.tel["end_turn"] += 1
            return _command("0")

        score, kind, o = best
        self.tel[{"attack": "attack", "attack_minion": "attack",
                  "thwart": "thwart", "play": "play", "ready": "ready_self",
                  "recover": "recover", "ae_action": "ae_action",
                  "action": "action", "flip_ae": "flip_ae",
                  "flip_hero": "flip_hero"}.get(kind, "action")] += 1
        if kind == "attack_minion":
            self.tel["attack_minion"] += 1

        if kind in ("flip_ae", "flip_hero"):
            if not self.can_flip():
                self.tel["end_turn"] += 1
                return _command("0")
            self.mark_flip()
            return self.take(o, hand)
        if kind == "attack":
            return self.aimed(o, hand, self.enemies(), ("villain", "minion"))
        if kind == "attack_minion":
            return self.aimed(o, hand, self.enemies(), ("minion", "villain"))
        if kind == "thwart":
            return self.aimed(o, hand, self.schemes(), ("main", "side"))
        if kind == "play":
            face = hand.get(o.get("bind_id"))
            rng = o.get("target_num_range") or [0, 0]
            if rng and rng[1] == 1 and (o.get("all_legal_targets") or []):
                if deals_damage(face):
                    return self.aimed(o, hand, self.enemies(), ("villain", "minion"))
                if removes_threat(face):
                    return self.aimed(o, hand, self.schemes(), ("main", "side"))
            self._played_round = getattr(self.world(), "round_id", -1)
            return self.take(o, hand)
        return self.take(o, hand)

    # ------------------------------------------------------------------ defence
    def defend(self, options, hand):
        defs = [o for o in options if o.get("name") == "Defense"]
        if not defs:
            return None
        w, ctx = self.w, self.context()
        try:
            ally_ids = {oid(f) for f in self.fx.player(0).allies.Get()}
        except Exception:
            ally_ids = set()
        hero_opts = [o for o in defs if o.get("bind_id") not in ally_ids]
        ally_opts = [o for o in defs if o.get("bind_id") in ally_ids]

        best = (w["def_decline"], None, None)
        if hero_opts:
            s = w["def_hero"] + w["def_hero_x_hurt"] * ctx["hurt"]
            if s > best[0]:
                best = (s, "hero", hero_opts[0])
        if ally_opts:
            s = w["def_ally"] + w["def_ally_x_hurt"] * ctx["hurt"]
            if s > best[0]:
                best = (s, "ally", ally_opts[0])
        if best[1] is None:
            return None
        self.tel["defend" if best[1] == "hero" else "defend_ally"] += 1
        return self.take(best[2], hand)
