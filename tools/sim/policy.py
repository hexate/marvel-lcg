"""Heuristic Marvel Champions policies.

Two modes so the strategy claims are testable against each other:

  aggro     hit the villain, thwart only at the brink, spend whatever is on top to pay.
            This is the pattern the user's statistics.json shows (4.2 damage per 1 threat).
  balanced  keep the main scheme low, build a board, kill minions, protect key cards
            from being burned as resources.

Both share every mechanic. Only the priorities differ, so a win-rate gap between them is
about the strategy and not about one bot being better engineered than the other.
"""
import os
import sys

from unit_test.harness import _command

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _data(name):
    return os.path.join(REPO_ROOT, 'data', name)

BOARD = ("Ally", "Upgrade", "Support")

_CARD_TEXT = {}


def card_text(face):
    """Printed text for a face, so the policy can tell a damage card from a filing cabinet."""
    if not _CARD_TEXT:
        import json, os
        for f in (_data('cards.json'), _data('cards_custom.json')):
            if not os.path.exists(f):
                continue
            try:
                db = json.load(open(f))
            except Exception:
                continue
            for _s, entries in db.items():
                if not isinstance(entries, list):
                    continue
                for e in entries:
                    if isinstance(e, dict) and 'card_id' in e:
                        _CARD_TEXT.setdefault(e['card_id'], (e.get('text') or '').lower())
    cid = getattr(getattr(face, 'paper', None), 'card_id', None)
    return _CARD_TEXT.get(cid, '')


_CARD_COST = {}


def card_cost(face):
    if not _CARD_COST:
        import json, os
        for f in (_data('cards.json'), _data('cards_custom.json')):
            if not os.path.exists(f):
                continue
            try:
                db = json.load(open(f))
            except Exception:
                continue
            for _s, entries in db.items():
                if not isinstance(entries, list):
                    continue
                for e in entries:
                    if isinstance(e, dict) and 'card_id' in e:
                        c = (e.get('desc') or {}).get('Cost')
                        try:
                            _CARD_COST.setdefault(e['card_id'], int(str(c)))
                        except Exception:
                            _CARD_COST.setdefault(e['card_id'], 0)
    cid = getattr(getattr(face, 'paper', None), 'card_id', None)
    return _CARD_COST.get(cid, 0)


def deals_damage(face):
    t = card_text(face)
    return 'damage to an enemy' in t or 'damage to the villain' in t or 'deal 1' in t \
        or 'deal 2' in t or 'deal 3' in t or 'deal 4' in t or 'deal 5' in t


def disables(face):
    """Stun eats the villain's next attack, confuse eats its next scheme. Both are worth
    more than a generic support, and the whole point of a stun-lock deck."""
    t = card_text(face)
    return 'stun' in t or 'confuse' in t


def boosts_offence(face):
    """Permanent +ATK or an extra ready is worth more than a one-shot, and compounds."""
    t = card_text(face)
    return '+1 atk' in t or '+2 atk' in t or '+3 atk' in t or 'ready ' in t


def removes_threat(face):
    t = card_text(face)
    return 'remove' in t and 'threat' in t


def oid(face):
    return getattr(getattr(face, "card", None), "object_id", None)


def type_of(face):
    if face is None:
        return "?"
    names = [c.__name__ for c in type(face).__mro__]
    for t in ("Ally", "Upgrade", "Support", "Event", "Resource"):
        if t in names:
            return t
    return names[0] if names else "?"


def pay_entries(o):
    """[(card_object_id, resource_letter)] this option could be paid with."""
    p = (o.get("target_payment") or {}).get("0") or {}
    out = []
    for e in (p.get("payment") or []):
        for k, v in e.items():
            out.append((int(k), v))
    return out


def cost_of(o):
    return int(((o.get("target_payment") or {}).get("0") or {}).get("cost") or 0)


class Heuristic:

    def __init__(self, mode="balanced"):
        """Mode grammar:
             balanced / aggro / brawl      base policies
             g<NN> / t<NN>                 balanced, prefer Giant / Tiny form,
                                           hero defends at NN% health
             w<NN>                         thwart-to-win scenarios (Batroc, Magog):
                                           always clear the main scheme
           Suffix `+a` lets allies chump-block; without it they stay alive and swing.
        """
        self.raw_mode = mode
        self.prefer_form = "giant"
        self.always_thwart = False
        self.hero_def_at = 0.45
        self.ally_def_at = 0.35
        self.ae_at = 0.40   # duck to alter-ego below this fraction of health

        m = mode
        self.cycle = True
        if m.endswith("+nc"):
            self.cycle = False
            m = m[:-3]
        self.ally_def_at = 0.60 if m in ("balanced", "b60") else self.ally_def_at
        if m == "b60":
            m = "balanced"
        # h<NN>a<MM>: hero defends below NN% health, allies chump below MM%
        import re as _re
        _m = _re.fullmatch(r"h(\d+)a(\d+)(?:e(\d+))?", m or "")
        if _m:
            self.hero_def_at = int(_m.group(1)) / 100.0
            self.ally_def_at = int(_m.group(2)) / 100.0
            if _m.group(3) is not None:
                self.ae_at = int(_m.group(3)) / 100.0
            m = "balanced"
        allow_chump = m.endswith("+a")
        if allow_chump:
            m = m[:-2]
        if m and m[0] in "gtwd" and m[1:].isdigit():
            self.hero_def_at = int(m[1:]) / 100.0
            if m[0] == "t":
                self.prefer_form = "tiny"
            elif m[0] == "w":
                self.prefer_form = "tiny"
                self.always_thwart = True
            self.ally_def_at = 0.35 if allow_chump else 0.0
            m = "balanced"
        self.mode = m

        self.tel = {"play": 0, "play_ally": 0, "play_board": 0, "play_event": 0,
                    "attack": 0, "attack_minion": 0, "thwart": 0, "defend": 0,
                    "flip_hero": 0, "flip_ae": 0, "recover": 0, "end_turn": 0,
                    "burned_ally": 0, "burned_total": 0, "defend_ally": 0,
                    "play_dmg_aimed": 0, "rounds_hero": 0, "rounds_ae": 0,
                    "form_giant": 0, "form_tiny": 0, "form_ae": 0, "mulligan": 0, "cycled": 0, "prompt_giveup": 0, "action": 0,
                    "ready_self": 0, "forced_choice": 0}

        self.fx = None
        self.steps = 0
        self.errors = 0
        self.first_error = None
        self.flipped_round = -1
        self.last_sig = None
        self.repeat = 0
        self.stalls = {}
        self._form_rounds = set()
        self._played_round = -1
        self._last_prompt = None
        self._prompt_repeat = 0
        self._thwart_round = -1
        self._thwarts_this_round = 0

    # ------------------------------------------------------------------ state
    def world(self):
        return self.fx.world if (self.fx and self.fx.game) else None

    def main(self):
        w = self.world()
        if w is None:
            return None
        s = w.area_schemes_main.Get()
        return s[0] if s else None

    def headroom(self):
        ms = self.main()
        if ms is None or ms.target_threat is None:
            return 99
        return max(0, ms.target_threat - ms.threat)

    def threat_pressure(self):
        """Fraction of the CURRENT stage's capacity already used.

        An absolute headroom threshold is wrong: 'thwart when 4 from the end' never fires
        early on an 11-threat scheme, and by the time it does the encounter deck has
        already dumped more threat than one turn can clear.
        """
        ms = self.main()
        if ms is None or not ms.target_threat:
            return 0.0
        return float(ms.threat) / float(ms.target_threat)

    def side_threat(self):
        try:
            return sum(1 for _ in self.world().area_schemes_side.Get())
        except Exception:
            return 0

    def hero_face(self):
        return self.fx.player(0).GetIdentity() if self.world() is not None else None

    def hp_frac(self):
        h = self.hero_face()
        try:
            return h.health / max(1, h.max_health)
        except Exception:
            return 1.0

    def is_ae(self):
        try:
            if self.world() is None:
                return False
            return bool(self.fx.player(0).IsAlterEgo())
        except Exception:
            return False

    def minions(self):
        try:
            if self.world() is None:
                return []
            return list(self.fx.player(0).GetEngagedMinions())
        except Exception:
            return []

    def hand(self):
        if self.world() is None:
            return {}
        return {oid(f): f for f in self.fx.player(0).hand_cards.Get()}

    def enemy_health(self):
        h = {}
        try:
            for f in self.minions():
                h[oid(f)] = getattr(f, "health", 99)
        except Exception:
            pass
        return h

    def enemies(self):
        m = {}
        if self.world() is None:
            return m
        try:
            for f in self.world().scenario.area_villain.Get():
                m[oid(f)] = "villain"
        except Exception:
            pass
        for f in self.minions():
            m[oid(f)] = "minion"
        return m

    def schemes(self):
        m = {}
        if self.world() is None:
            return m
        ms = self.main()
        if ms is not None:
            m[oid(ms)] = "main"
        try:
            for f in self.world().area_schemes_side.Get():
                m[oid(f)] = "side"
        except Exception:
            pass
        return m

    # -------------------------------------------------------------- resources
    def resources(self, o, hand):
        """Pick which cards to burn. aggro takes what is on top; balanced protects the board."""
        n = cost_of(o)
        entries = pay_entries(o)
        if n <= 0 or not entries:
            return []
        if self.mode == "aggro":
            picks = entries[:n]
        else:
            def burn_cost(item):
                cid, _letter = item
                face = hand.get(cid)
                if face is None:
                    return 0          # the identity itself: free resource, always use first
                t = type_of(face)
                return {"Resource": 1, "Event": 3, "Upgrade": 4, "Support": 4, "Ally": 6}.get(t, 3)
            picks = sorted(entries, key=burn_cost)[:n]
        for cid, _ in picks:
            face = hand.get(cid)
            if face is not None:
                self.tel["burned_total"] += 1
                if type_of(face) == "Ally":
                    self.tel["burned_ally"] += 1
        return [str(cid) for cid, _ in picks]

    # ------------------------------------------------------------------ pick
    def rank_targets(self, legal):
        """Order legal targets so damage lands on the villain and thwart on the main scheme.

        Every prompt that asks for a target used to get `legal[:n]`, which pointed
        3-damage events at whatever happened to be first in the list.
        """
        en, sc = self.enemies(), self.schemes()
        order = {"villain": 0, "main": 1, "minion": 2, "side": 3}

        hp = self.enemy_health()

        def key(t):
            kind = en.get(t) or sc.get(t)
            # among minions, finish the weakest first: a minion left at 1 HP still
            # attacks every villain phase, so spread damage buys nothing.
            return (order.get(kind, 4), hp.get(t, 0))
        return sorted(legal, key=key)

    def take(self, o, hand, targets=None):
        rng = o.get("target_num_range") or [0, 0]
        legal_raw = list(o.get("all_legal_targets") or [])
        if targets is None:
            n = rng[1] if rng and rng[1] else 0
            want = [str(t) for t in self.rank_targets(legal_raw)[:n]]
        else:
            want = targets
        return _command(o["id"], want, self.resources(o, hand))

    def owner_ids(self):
        try:
            allies = {oid(f) for f in self.fx.player(0).allies.Get()}
        except Exception:
            allies = set()
        try:
            heroes = {oid(f) for f in self.fx.player(0).area_hero.Get()}
        except Exception:
            heroes = set()
        return allies, heroes

    def by_owner(self, opts, want):
        allies, heroes = self.owner_ids()
        pool = allies if want == "ally" else heroes
        return [o for o in opts if o.get("bind_id") in pool]

    def aimed(self, o, hand, id_kind, prefer):
        legal = list(o.get("all_legal_targets") or [])
        hp = self.enemy_health()
        chosen = None
        for kind in prefer:
            cands = [t for t in legal if id_kind.get(t) == kind]
            if cands:
                chosen = min(cands, key=lambda t: hp.get(t, 0)) if kind == "minion" else cands[0]
                break
        if chosen is None and legal:
            chosen = legal[0]
        # Respect the option's own target count. An Attack or Thwart can list legal targets
        # while asking for none of them (target_num_range [0, 0]); handing it one is rejected,
        # the prompt repeats, and the whole turn is spent re-offering the same illegal answer.
        rng = o.get("target_num_range") or [0, 0]
        want_max = rng[1] if len(rng) > 1 else 0
        if want_max <= 0 or chosen is None:
            return self.take(o, hand, [])
        return self.take(o, hand, [str(chosen)])

    @staticmethod
    def option_form(name):
        """Multi-form heroes do not use `Change_Form`. Ant-Man offers
        `Change_To_AVENGER_GIANT`, `Change_To_AVENGER_TINY` and `Change_To_Scott_Lang`,
        so a policy matching only on `Change_Form` never changes form at all."""
        n = (name or "").upper()
        if not n.startswith("CHANGE_TO"):
            return None
        if "GIANT" in n:
            return "giant"
        if "TINY" in n:
            return "tiny"
        return "ae"

    def current_form(self):
        if self.is_ae():
            return "ae"
        f = self.hero_face()
        atk = getattr(f, "attack", 0) or 0
        thw = getattr(f, "thwart", 0) or 0
        return "giant" if atk > thw else "tiny"

    def desired_form(self, hp, mins):
        press = self.threat_pressure()
        # duck out only when it is safe: nothing engaged, scheme not close
        if hp <= 0.35 and not mins and press < 0.45:
            return "ae"
        if self.always_thwart:
            return "tiny"
        if press >= 0.40:
            return "tiny"     # THW 2, and the change itself removes 1 threat
        return self.prefer_form

    def multi_form_move(self, by, hand, hp, mins):
        forms = {}
        for name, opts in by.items():
            f = self.option_form(name)
            if f and f not in forms:
                forms[f] = opts[0]
        if not forms:
            return None
        cur = self.current_form()
        want = self.desired_form(hp, mins)
        if cur == "ae" and want == "ae":
            want = "tiny" if self.threat_pressure() >= 0.40 else self.prefer_form
            if hp < 0.6 and self.threat_pressure() < 0.5 and by.get("Recover"):
                self.tel["recover"] += 1
                return self.take(by["Recover"][0], hand)
            if hp < 0.6 and self.threat_pressure() < 0.5:
                return None
        if want != cur and want in forms and self.can_flip():
            self.mark_flip()
            self.tel["form_" + want] += 1
            return self.take(forms[want], hand)
        return None

    def can_flip(self):
        w = self.world()
        return w is None or w.round_id != self.flipped_round

    def mark_flip(self):
        w = self.world()
        if w is not None:
            self.flipped_round = w.round_id

    def signature(self):
        """Enough state to tell 'the turn moved on' from 'nothing happened'."""
        w = self.world()
        if w is None:
            return None
        p = self.fx.player(0)
        ms = self.main()
        try:
            villain_dmg = sum(f.GetLostHealth() for f in w.scenario.area_villain.Get())
        except Exception:
            villain_dmg = 0
        try:
            ready = sum(1 for f in list(p.allies.Get()) + list(p.area_hero.Get())
                        if f.IsReady())
        except Exception:
            ready = 0
        return (w.round_id, getattr(ms, "threat", None), villain_dmg,
                p.hand_cards.GetSize(), p.allies.GetSize(), ready)

    # ------------------------------------------------------------------ turn
    def turn(self, options):
        try:
            w = self.world()
            key = (w.round_id, self.fx.player(0).IsHero())
            if key not in self._form_rounds:
                self._form_rounds.add(key)
                self.tel["rounds_hero" if key[1] else "rounds_ae"] += 1
        except Exception:
            pass
        sig = self.signature()
        if sig is not None and sig == self.last_sig:
            self.repeat += 1
        else:
            self.repeat = 0
            self.last_sig = sig
        if self.repeat > 5:
            # Something on offer is not executing. Stop re-picking it and end the turn.
            names = ",".join(sorted({str(o.get("name")) for o in options}))
            self.stalls[names] = self.stalls.get(names, 0) + 1
            self.repeat = 0
            self.tel["end_turn"] += 1
            return _command("0")
        return self.turn_inner(options)

    def turn_inner(self, options):
        by = {}
        for o in options:
            by.setdefault(o.get("name"), []).append(o)
        hand = self.hand()
        head, hp, mins, ae = self.headroom(), self.hp_frac(), self.minions(), self.is_ae()

        # --- form management
        mf = self.multi_form_move(by, hand, hp, mins)
        if mf is not None:
            return mf
        if ae:
            # Take the heal first. Flipping down and straight back up without recovering
            # is the worst of both: you gave the villain a scheme and healed nothing.
            if hp < 0.6 and self.threat_pressure() < 0.5 and by.get("Recover"):
                self.tel["recover"] += 1
                return self.take(by["Recover"][0], hand)
            if (hp >= 0.6 or head <= 2 or self.threat_pressure() >= 0.5) \
                    and by.get("Change_Form") and self.can_flip():
                self.mark_flip()
                self.tel["flip_hero"] += 1
                return self.take(by["Change_Form"][0], hand)
        else:
            if self.mode in ("balanced", "brawl") and hp <= self.ae_at and not mins \
                    and self.threat_pressure() <= 0.4 \
                    and by.get("Change_Form") and self.can_flip():
                self.mark_flip()
                self.tel["flip_ae"] += 1
                return self.take(by["Change_Form"][0], hand)

        # --- self-ready. Cap's signature ability turns one activation into two, which is
        # the whole answer to defending costing your next turn.
        ready_opts = [o for oname, opts in by.items() for o in opts
                      if "CANDOTHISALLDAY" in (oname or "").upper().replace("_", "")
                      or "READY" in (oname or "").upper().replace("_", "")]
        if ready_opts and len(hand) >= 1:
            try:
                exhausted = not self.fx.player(0).GetIdentity().IsReady()
            except Exception:
                exhausted = False
            if exhausted:
                self.tel["ready_self"] += 1
                return self.take(ready_opts[0], hand)

        # --- deploy
        plays = [o for o in by.get("Play", []) if o.get("bind_id") in hand]
        if plays:
            def rank(o):
                face = hand.get(o.get("bind_id"))
                t = type_of(face)
                if self.mode not in ("balanced", "brawl"):
                    return (0, cost_of(o))
                if t == "Ally":
                    return (0, cost_of(o))
                # a card that actually does something to the board state beats a filing cabinet
                if disables(face):
                    return (0, cost_of(o))
                if boosts_offence(face):
                    return (1, cost_of(o))
                if deals_damage(face) or removes_threat(face):
                    return (1, cost_of(o))
                if t in ("Upgrade", "Support"):
                    return (2, cost_of(o))
                return (3, cost_of(o))
            plays.sort(key=rank)
            afford = [o for o in plays if cost_of(o) <= max(0, len(hand) - 2)]
            if afford:
                plays = afford
            o = plays[0]
            face = hand.get(o.get("bind_id"))
            t = type_of(face)
            self.tel["play"] += 1
            try:
                self._played_round = self.world().round_id
            except Exception:
                pass
            self.tel["play_ally"] += (t == "Ally")
            self.tel["play_board"] += (t in BOARD)
            self.tel["play_event"] += (t == "Event")
            # A damage card that takes "an enemy" will happily be pointed at a 1 HP minion
            # if you just hand it the first legal target. Aim it.
            rng = o.get("target_num_range") or [0, 0]
            if rng and rng[1] == 1 and (o.get("all_legal_targets") or []):
                if deals_damage(face):
                    self.tel["play_dmg_aimed"] += 1
                    return self.aimed(o, hand, self.enemies(), ("villain", "minion"))
                if removes_threat(face):
                    return self.aimed(o, hand, self.schemes(), ("main", "side"))
            return self.take(o, hand)

        # --- activations (hero and every ally that can still act)
        atk, thw = by.get("Attack", []), by.get("Thwart", [])
        en, sc = self.enemies(), self.schemes()
        if self.mode in ("balanced", "brawl"):
            # allies thwart first, so the hero's activation stays on the villain
            ms_threat = getattr(self.main(), "threat", 0) or 0
            # Thwarting past what the clock demands is activations not spent on the villain.
            # One clear per round keeps pace with acceleration; more only when it is urgent.
            rnd = getattr(self.world(), "round_id", -1)
            thw_used = self._thwarts_this_round if self._thwart_round == rnd else 0
            thwart_budget = 99 if head <= 2 else 1
            if thw and thw_used < thwart_budget and (
                    self.always_thwart and ms_threat > 0
                    or head <= 4 or self.threat_pressure() >= 0.35):
                pick = (self.by_owner(thw, "ally") or thw)[0]
                self.tel["thwart"] += 1
                self._thwart_round, self._thwarts_this_round = rnd, thw_used + 1
                return self.aimed(pick, hand, sc, ("main",))
            # only spend damage on minions when they are actually the threat
            # An engaged minion attacks every single villain phase. Ignoring one to "save
            # damage for the villain" costs more health than the minion costs damage.
            if atk and mins:
                pick = (self.by_owner(atk, "ally") or atk)[0]
                self.tel["attack"] += 1
                self.tel["attack_minion"] += 1
                return self.aimed(pick, hand, en, ("minion",))
            if atk:
                want = "hero" if self.mode == "brawl" else "ally"
                pick = (self.by_owner(atk, want) or atk)[0]
                self.tel["attack"] += 1
                return self.aimed(pick, hand, en, ("villain", "minion"))
            if thw and head <= 6:
                self.tel["thwart"] += 1
                return self.aimed(thw[0], hand, sc, ("main", "side"))
        else:
            if atk:
                self.tel["attack"] += 1
                return self.aimed(atk[0], hand, en, ("villain", "minion"))
            if head <= 1 and thw:
                self.tel["thwart"] += 1
                return self.aimed(thw[0], hand, sc, ("main",))

        for bucket in ("Action", "Hero_Action"):
            if by.get(bucket):
                self.tel["action"] += 1
                return self.take(by[bucket][0], hand)
        self.tel["end_turn"] += 1
        return _command("0")

    def lethal_threat(self):
        """Roughly how much the biggest attacker can put through this villain phase."""
        best = 0
        try:
            for f in self.world().scenario.area_villain.Get():
                best = max(best, int(getattr(f, "attack", 0) or 0))
        except Exception:
            pass
        for f in self.minions():
            best = max(best, int(getattr(f, "attack", 0) or 0))
        return best + 2   # boost cards add roughly this much

    def defend(self, options, hand):
        """Defending exhausts the defender, and `Faces.ReadyAll` runs at the END of the player
        phase (game/player/element/player_phase.py:93). A hero who defends in the villain phase
        is therefore still exhausted on its next turn and loses that whole activation. So:
        chump-block with an ally, and only spend the hero when the health is what matters."""
        defs = [o for o in options if o.get("name") == "Defense"]
        if not defs:
            return None
        try:
            ally_ids = {oid(f) for f in self.fx.player(0).allies.Get()}
        except Exception:
            ally_ids = set()
        hp = self.hp_frac()
        if self.mode == "aggro":
            if hp <= 0.5:
                self.tel["defend"] += 1
                return self.take(defs[0], hand)
            return None
        if self.mode == "brawl":
            # keep the hero ready to swing; spend an ally only when the hero is in danger
            ally_opts = [o for o in defs if o.get("bind_id") in ally_ids]
            if hp <= 0.5 and ally_opts:
                self.tel["defend_ally"] += 1
                return self.take(ally_opts[0], hand)
            hero_opts = [o for o in defs if o.get("bind_id") not in ally_ids]
            if hp <= 0.25 and hero_opts:
                self.tel["defend"] += 1
                return self.take(hero_opts[0], hand)
            return None
        hero_opts = [o for o in defs if o.get("bind_id") not in ally_ids]
        ally_opts = [o for o in defs if o.get("bind_id") in ally_ids]
        # A hero that defends is exhausted on its next turn and contributes nothing to the
        # damage race, which it cannot afford. Spend allies, keep the hero swinging.
        try:
            cur_hp = int(getattr(self.hero_face(), "health", 99))
        except Exception:
            cur_hp = 99
        in_danger = cur_hp <= self.lethal_threat()
        if (in_danger or hp <= self.ally_def_at) and ally_opts:
            self.tel["defend_ally"] += 1
            return self.take(ally_opts[0], hand)
        if hp <= self.hero_def_at and hero_opts:
            self.tel["defend"] += 1
            return self.take(hero_opts[0], hand)
        return None

    # ---------------------------------------------------------------- policy
    def __call__(self, payload, options):
        try:
            return self.decide(payload, options)
        except Exception as e:
            self.errors += 1
            if self.first_error is None:
                import traceback
                self.first_error = traceback.format_exc()[-500:]
            return _command("0")

    def decide(self, payload, options):
        self.steps += 1
        # Global repeat guard. The engine gives up after 1000 rejected inputs in a row
        # ("Input rejected ... Giving up rather than spinning"), which kills the run. If the
        # same prompt keeps coming back, our answer is not usable: stop offering it.
        sig = (payload.event_name, payload.prompt_text, len(options))
        if sig == self._last_prompt:
            self._prompt_repeat += 1
        else:
            self._last_prompt = sig
            self._prompt_repeat = 0
        self._thwart_round = -1
        self._thwarts_this_round = 0
        if self._prompt_repeat > 25:
            self.tel["prompt_giveup"] += 1
            if self._prompt_repeat > 60 and options:
                o = options[min(self._prompt_repeat - 61, len(options) - 1)]
                rng = o.get("target_num_range") or [0, 0]
                legal = [str(t) for t in (o.get("all_legal_targets") or [])]
                return _command(o["id"], legal[:rng[1] if rng and rng[1] else 0])
            return _command("0")
        if self.steps > 20000:
            self.world().game_over.SetExit()
            return _command("0")
        if not options:
            return _command("0")

        ev = payload.event_name
        if ev == "WhenPlayerInTurn":
            return self.turn(options)

        hand = self.hand()

        # End of turn: discard what you cannot use, then draw back up to hand size.
        # `MayDiscardHandCardsAndDrawUpToMax` (game/player/element/player_phase.py:82) is the
        # real card-selection step of the game. Declining it every turn leaves a dead hand
        # dead for the rest of the game.
        for o in options:
            if o.get("name") == "End Phase" and self.cycle:
                legal = list(o.get("all_legal_targets") or [])
                played_this_round = self._played_round == getattr(self.world(), "round_id", -1)
                toss = []
                for t in legal:
                    face = hand.get(t)
                    if face is None:
                        continue
                    c = card_cost(face)
                    if c >= 4 or (not played_this_round and type_of(face) != "Resource"):
                        toss.append(t)
                rng = o.get("target_num_range") or [0, 0]
                toss = toss[:rng[1] if rng and rng[1] else len(toss)]
                self.tel["cycled"] += len(toss)
                if not toss:
                    return _command("0")
                return _command(o["id"], [str(t) for t in toss])

        # Mulligan. Declining it keeps a hand full of cards too expensive to cast in the
        # rounds that decide the game.
        for o in options:
            if o.get("name") == "Resolve Mulligans":
                legal = list(o.get("all_legal_targets") or [])
                toss = []
                for t in legal:
                    face = hand.get(t)
                    if face is None:
                        continue
                    if card_cost(face) >= 4:
                        toss.append(t)
                toss = toss[:3]
                self.tel["mulligan"] += len(toss)
                if not toss:
                    return _command("0")
                return _command(o["id"], [str(t) for t in toss])

        # Free triggered value: always take it.
        for o in options:
            if o.get("name") in ("Finesse", "Precision", "Response"):
                return self.take(o, hand)

        if ev == "WhenUnitBeingAttack":
            d = self.defend(options, hand)
            if d is not None:
                return d
            return _command("0")

        if payload.show_cancel:
            return _command("0")
        # A forced prompt accepts id 0 only when there is a single option needing no targets
        # (engine/controller/controller.py:271). With two, declining is rejected and the
        # prompt repeats until the stall guard burns the turn. Pick a real option instead,
        # preferring the one that declines the optional effect.
        if len(options) > 1 and all(not (o.get("target_num_range") or [0, 0])[0] for o in options):
            cancel = [o for o in options if str(o.get("name")).lower().startswith("cancel")]
            pick = (cancel or options)[0]
            self.tel["forced_choice"] += 1
            return _command(pick["id"])
        o = options[0]
        rng = o.get("target_num_range") or [0, 0]
        need = rng[0] if rng else 0
        if need == 0:
            return _command("0")
        legal = [str(t) for t in self.rank_targets(list(o.get("all_legal_targets") or []))]
        return _command(o["id"], legal[:need], self.resources(o, hand))
