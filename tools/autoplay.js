/* Auto-player for the Marvel LCG client.
 *
 * The client has several distinct decision modes and each needs a different gesture. Getting one
 * wrong looks identical to being stuck, which is what made this take several passes:
 *
 *   option buttons   click TOGGLES a choice; OK commits it
 *   card in a deck   first click only EXPANDS the deck; the second selects
 *   card elsewhere   first click selects; a second would toggle it back off
 *   reveal pause     the game halts until the centre preview is dismissed
 *   player turn      OK does nothing; the turn ends via #btn-end
 *
 * Rather than a fixed priority order, this fingerprints the screen and escalates: if an action
 * does not change the fingerprint, the next attempt tries the action after it. That way a mode I
 * have not anticipated degrades into "try the other things" instead of looping forever.
 *
 * Running it. This file is not served: `public/js/` is compiled TypeScript output and is
 * gitignored wholesale, so living there meant the auto-player was not in version control. Paste
 * the contents into the console on a board page, then:
 *
 *   __auto.start(600)     play up to 600 steps in the background
 *   __auto.log            what it did, one row per step, with overflow measurements
 *   __auto.result()       outcome and reason once the game is over
 *   __auto.stop = true    stop early
 *
 * Keep the tab in front. A hidden tab clamps timers to one second, so every wait costs 1000ms
 * whatever it asks for and a run crawls at about a step per 40 seconds with nothing wrong.
 */
(() => {
const sleep = ms => new Promise(r => setTimeout(r, ms));
/** On screen AND willing to be clicked.
 *
 *  This used to test the bounding box alone, which is how a run burned 21 of its 33 steps clicking
 *  a greyed-out OK. A disabled button is drawn at full size, so by that test it looked available
 *  every time, and the ladder read the lack of response as the game being stuck rather than as the
 *  button saying no. `disabled` and the `disable` class are both used here, so check both. */
const vis = e => {
  if (!e || e.disabled || e.classList.contains('disable')) return false;
  const r = e.getBoundingClientRect();
  return r.width > 0 && r.height > 0;
};

class Auto {
  constructor() { this.log = []; this.ladder = 0; this.lastFp = ''; this.same = 0; }

  /** Enough state to tell "something happened" from "nothing happened". */
  fingerprint() {
    const sel = document.querySelectorAll('#scene .card.selected').length;
    const hl  = document.querySelectorAll('#scene .card.highlight-targets').length;
    const btn = document.querySelectorAll('#option-buttons button').length;
    return [document.body.className, this.prompt(), sel, hl, btn,
            document.querySelectorAll('#scene .card').length,
            document.querySelectorAll('#player-all-hand-cards .card').length].join('|');
  }

  prompt() {
    return (document.body.innerText.split('\n').map(s => s.trim())
      .find(l => /\(\d+~\d+\)/.test(l)) || '');
  }

  /** `(1~7)` means choose at least 1, at most 7. Drives how many targets to click. */
  need() {
    const m = this.prompt().match(/\((\d+)~(\d+)\)/);
    return m ? { min: +m[1], max: +m[2] } : null;
  }

  health() {
    const vw = innerWidth, vh = innerHeight;
    const cards = [...document.querySelectorAll('#scene .card')].filter(c => {
      const r = c.getBoundingClientRect();
      return r.width > 4 && c.parentElement.getBoundingClientRect().height > 2;
    });
    let R = 0, B = 0, L = 0, T = 0;
    cards.forEach(c => { const r = c.getBoundingClientRect();
      R = Math.max(R, r.right - vw); B = Math.max(B, r.bottom - vh);
      L = Math.max(L, -r.left);      T = Math.max(T, -r.top); });
    return { cards: cards.length, hand: document.querySelectorAll('#player-all-hand-cards .card').length,
             R: Math.round(Math.max(0, R)), B: Math.round(Math.max(0, B)),
             L: Math.round(Math.max(0, L)), T: Math.round(Math.max(0, T)) };
  }

  async unpause() {
    if (!document.body.classList.contains('pause')) return false;
    const c = document.querySelector('#image-preview-div-center .image-preview');
    if (c && !c.parentElement.classList.contains('hide')) { c.click(); await sleep(700); return 'unpause'; }
    const pb = document.querySelector('#pause-btn');
    if (vis(pb)) { pb.click(); await sleep(700); return 'unpause'; }
    return false;
  }

  async options() {
    const btns = [...document.querySelectorAll('#option-buttons button')]
      .filter(b => vis(b) && !b.classList.contains('disable'));
    if (!btns.length) return false;

    const b = this.board();
    const scored = btns.map(el => ({ el, label: (el.innerText || '').trim(), }))
      .map(o => ({ ...o, score: this.rankOption(o.label, b) }))
      .sort((x, y) => y.score - x.score);
    const best = scored[0];

    // Remember what we asked for. The targeting step that follows has no other way to know whether
    // these highlighted cards are things to hit or things to thwart.
    const l = best.label.toLowerCase();
    this.intent = /^attack/.test(l) ? 'attack' : /^thwart/.test(l) ? 'thwart' : null;

    if (!best.el.classList.contains('clicked')) best.el.click();
    await sleep(500);
    const ok = document.querySelector('#btn-ok');
    if (vis(ok)) ok.click();
    await sleep(700);
    return 'option:' + best.label.slice(0, 18);
  }

  /** Which highlighted card to click, given what we just asked to do.
   *
   *  Document order is not a plan. Attacking wants an engaged minion gone first, because a minion
   *  hits back every turn while the villain's health is a fixed pool; thwarting wants the main
   *  scheme, because that is the one with a limit that ends the game.
   */
  bestTarget() {
    const candidates = [...document.querySelectorAll('#scene .card.highlight-targets:not(.selected)')];
    if (!candidates.length) return null;
    const areaOf = c => (c.parentElement && c.parentElement.id) || '';
    const rank = c => {
      const a = areaOf(c);
      if (this.intent === 'attack') {
        return a.includes('engaged-minions') ? 0 : a.includes('villain') ? 1 : 2;
      }
      if (this.intent === 'thwart') {
        return a.includes('schemes-main') ? 0 : a.includes('schemes-side') ? 1 : 2;
      }
      return 2;
    };
    return candidates.sort((x, y) => rank(x) - rank(y))[0];
  }

  /** Select targets until the game is satisfied.
   *
   *  Two things were wrong here and they hid each other. The query had no `:not(.selected)`, so it
   *  kept handing back the same first card and every click toggled that one card on and then off
   *  again. And toggling changes the selected count, which is part of the fingerprint, so the run
   *  read its own oscillation as progress and never tripped the stall detector: one game spent 41
   *  of 57 steps doing this and advanced a single turn.
   *
   *  Selecting up to the minimum is also not enough on its own, because some prompts do not state
   *  a count. Enabling OK is the game's own signal that it has what it needs, so that is the thing
   *  to drive toward, with the stated minimum as a floor and the stated maximum as a ceiling.
   */
  async targets() {
    const want = this.need();
    const floor = want ? Math.max(1, want.min) : 1;
    const ceil = Math.min(want ? Math.max(want.max, floor) : 1, 8);
    const okEl = () => document.querySelector('#btn-ok');
    let picks = 0;
    for (let i = 0; i < ceil; i++) {
      let t = this.bestTarget();
      if (!t) break;
      // A card inside an unopened deck takes two clicks: one opens the deck, one takes the card.
      const inDeck = t.parentElement.classList.contains('deck')
                  && !t.parentElement.classList.contains('clicked');
      t.click(); await sleep(400); picks++;
      if (inDeck) {
        t = this.bestTarget();
        if (t) { t.click(); await sleep(400); }
      }
      if (picks >= floor && vis(okEl())) break;
    }
    if (!picks) return false;
    if (vis(okEl())) { okEl().click(); await sleep(700); }
    return 'target:' + picks;
  }

  async confirm() {
    const ok = document.querySelector('#btn-ok');
    if (!vis(ok)) return false;
    ok.click(); await sleep(700); return 'ok';
  }

  /** `#btn-end` is the SAME element for "End Turn" and "Cancel"; only the label changes with
   *  context. Clicking it blindly during a decision cancels the decision, which had this looping:
   *  advance, cancel, advance. Always read the label. */
  async endTurn() {
    const end = document.querySelector('#btn-end');
    if (!vis(end)) return false;
    if (!/end\s*turn/i.test(end.innerText || '')) return false;
    this.tried = new Set();   // abilities come back on a new turn
    end.click(); await sleep(900);
    const ok = document.querySelector('#btn-ok');
    if (vis(ok)) ok.click();
    await sleep(900); return 'endTurn';
  }

  /** Last resort: any other visible button that is not obviously destructive. */
  async anyButton() {
    // Never Cancel or Undo: both move the game backwards, and the ladder would then oscillate.
    const skip = /save|share|replay|quit|exit|undo|redo|load|cancel|pause|log/i;
    const b = [...document.querySelectorAll('button')].find(x =>
      vis(x) && !skip.test((x.innerText || '') + x.className) && !x.classList.contains('disable'));
    if (!b) return false;
    b.click(); await sleep(700); return 'button:' + (b.innerText || '').trim().slice(0, 14);
  }


  /** What the screen actually looks like, for when the ladder runs out of ideas.
   *
   *  A bare "STALLED" says nothing about which mode was not handled, so every stall cost a manual
   *  round trip through devtools to find out. This is that round trip, recorded automatically. */
  snapshot() {
    const btn = e => ({ id: e.id || null, label: (e.innerText || '').trim().slice(0, 24) });
    return {
      prompt: this.prompt() || '(none)',
      body: document.body.className,
      buttons: [...document.querySelectorAll('button')].filter(vis).map(btn),
      options: [...document.querySelectorAll('#option-buttons button')].filter(vis).map(btn),
      targets: document.querySelectorAll('#scene .card.highlight-targets').length,
      selected: document.querySelectorAll('#scene .card.selected').length,
      cards: document.querySelectorAll('#scene .card').length,
      hand: document.querySelectorAll('#player-all-hand-cards .card').length,
    };
  }

  /** Is there anything on screen the ladder could act on?
   *
   *  The one question worth asking before deciding a game is stuck. Cards settling down is not the
   *  same as the client being ready for input, and reading it that way is what made two runs give
   *  up during setup: the board paused mid-deal for longer than the stability window, so it looked
   *  finished while the hand had not been dealt and no buttons existed yet. Both times the board
   *  came up fine seconds after the run had already quit.
   */
  actionable() {
    return vis(document.querySelector('#btn-ok'))
        || vis(document.querySelector('#btn-end'))
        || !!document.querySelector('#scene .card.highlight-targets')
        || !!document.querySelector('#scene .card.highlight-pay')
        || !!document.querySelector('#option-buttons button')
        || !!this.prompt();
  }

  /** Wait for the game to want something from us.
   *
   *  A hidden tab has its timers clamped to one second, so every wait in here costs 1000ms whatever
   *  it asks for and a step that tries the whole ladder takes most of a minute. Nothing is wrong
   *  with the game when that happens, but the symptom is a run that crawls, which reads exactly
   *  like one. Recorded rather than worked around: the fix is to put the tab in front.
   */
  async ready(maxMs = 30000) {
    const throttled = document.hidden;
    const t0 = Date.now();
    while (Date.now() - t0 < maxMs) {
      if (this.actionable()) {
        return { ready: true, throttled, cards: document.querySelectorAll('#scene .card').length,
                 ms: Date.now() - t0 };
      }
      await sleep(600);
    }
    return { ready: false, throttled, cards: document.querySelectorAll('#scene .card').length,
             ms: Date.now() - t0 };
  }

  /** One long look before calling it stuck.
   *
   *  Every gesture waits a fixed few hundred ms, which is fine for a click but not for a turn that
   *  triggers a chain of animations and a server round trip. A slow response is indistinguishable
   *  from no response at that timescale, so the ladder can burn through its whole budget waiting on
   *  something that was always going to arrive. This gives it one honest chance to. */
  async settle(fp, ms = 5000) {
    const t0 = Date.now();
    while (Date.now() - t0 < ms) {
      await sleep(700);
      if (this.fingerprint() !== fp) return true;
    }
    return false;
  }


  /** Play something from hand.
   *
   *  The ordinary way a turn advances, and there was no gesture for it: hand cards do not carry
   *  `highlight-targets`, so `targets()` never saw them and the ladder had nothing to offer on a
   *  plain player turn. It got as far as it did by ending turns without ever playing a card.
   *
   *  The index rotates so an unaffordable card does not jam the run. The game refuses cards it
   *  cannot pay for by simply not responding, which is indistinguishable from a stall, so the only
   *  way through is to keep offering it different ones. */
  async playHand() {
    const hand = [...document.querySelectorAll('#player-all-hand-cards .card')];
    if (!hand.length) return false;
    this.handIx = ((this.handIx || 0) + 1) % hand.length;
    const c = hand[this.handIx];
    const size = hand.length;
    c.click(); await sleep(600);
    // A played card usually opens a decision: pay resources, pick a target. Let the next step
    // handle it, but confirm here when the game is already satisfied.
    const ok = document.querySelector('#btn-ok');
    if (vis(ok)) { ok.click(); await sleep(700); }
    // Success is the card leaving hand, not the screen changing. Selecting a card it cannot pay
    // for also changes the screen, and reading that as progress is how one game spent 54 steps and
    // 18 hand plays inside a single turn without the board moving.
    const after = document.querySelectorAll('#player-all-hand-cards .card').length;
    return after < size ? 'hand:' + this.handIx : false;
  }

  /** Back out of a decision that cannot be completed.
   *
   *  Cancel is excluded from `anyButton` on purpose: it moves the game backwards, and a ladder that
   *  is free to cancel will happily advance and cancel forever. But a decision where OK is disabled
   *  and nothing is selectable is a genuine dead end, and backing out is the only legal move left.
   *  Allowed once per stall, so it stays an escape hatch and cannot become the oscillation it was
   *  banned for. */
  async escape() {
    if (this.escaped) return false;
    const end = document.querySelector('#btn-end');
    if (!end || !/cancel/i.test(end.innerText || '')) return false;
    const ok = document.querySelector('#btn-ok');
    if (vis(ok) || document.querySelector('#scene .card.highlight-targets')) return false;
    this.escaped = true;
    end.click(); await sleep(900);
    return 'escape';
  }


  /** Pay for something.
   *
   *  A cost prompt is its own mode and nothing in the ladder spoke it. It does not use the
   *  `(min~max)` wording the target prompts use, so `need()` reads nothing from it, and OK stays
   *  disabled until enough is spent, so `confirm()` had nothing to click either. That combination
   *  is what a dead end looks like from the outside, and the run backed out of every card it tried
   *  to play.
   *
   *  The client marks what can be spent with `highlight-pay`, which is a better signal than
   *  guessing at the hand: resources can come from anywhere on the board, not just from hand, and
   *  the same marker covers both. Feed it one card at a time and stop the moment OK comes alive,
   *  so nothing is overspent. */
  async pay() {
    const ok = document.querySelector('#btn-ok');
    if (!ok || vis(ok)) return false;
    let spent = 0;
    for (let i = 0; i < 8; i++) {
      const c = document.querySelector('#scene .card.highlight-pay:not(.selected)');
      if (!c) break;
      c.click(); await sleep(450); spent++;
      if (vis(ok)) { ok.click(); await sleep(800); return 'pay:' + spent; }
    }
    return spent ? 'pay:' + spent : false;
  }


  /** Has the game ended?
   *
   *  This checked for a `game-over` class on `body`, which does not exist. Nothing ever matched, so
   *  a finished game read as a live one with nothing to click and the run spent the rest of its
   *  budget doing nothing: 18 of 28 steps in one run were after the result was already on screen.
   *  The client marks the end by activating the panel, so that is what to ask. */
  over() {
    const box = document.querySelector('#game-over-box');
    return !!box && box.classList.contains('active');
  }

  /** Won, lost, and why, read off the panel the client already filled in. */
  result() {
    const t = e => (document.querySelector(e)?.innerText || '').trim();
    return this.over() ? { outcome: t('#game-over-text'), reason: t('#game-over-text-2') } : null;
  }


  /** The board state a policy needs, read off the same elements a player looks at.
   *
   *  `.health` is the number printed on a card, `.target_threat` is "threat/limit" on the main
   *  scheme and is empty while the scheme is still at zero. The identity card carries its form as
   *  a class, which is what decides whether attacking is even legal.
   */
  board() {
    const num = el => { const m = ((el && el.textContent) || '').match(/\d+/); return m ? +m[0] : null; };
    // The hero area holds the identity AND every upgrade attached to it, so taking the first card
    // there gets whichever happens to be first in the DOM. Once an upgrade landed that was the
    // upgrade, which has no health and no form, so `heroHp` read null and `alterEgo` read false
    // forever after. An identity is the card in that area with a printed health.
    const identity = [...document.querySelectorAll('#player-all-area-hero .card')]
      .find(c => c.querySelector('.health'));
    // The scheme's "threat/limit" is generated content on `.info::after`, so it is invisible to
    // textContent and the first version of this read an empty string and concluded there was no
    // scheme pressure at all. That made the policy think attacking was always safe.
    const info = document.querySelector('#area-schemes-main .card .info');
    const threat = (info ? getComputedStyle(info, '::after').content : '').match(/(\d+)\s*\/\s*(\d+)/);
    return {
      villainHp: num(document.querySelector('#area-villain .card .health')),
      heroHp: num(identity && identity.querySelector('.health')),
      alterEgo: !!(identity && identity.classList.contains('type-alter-ego')),
      threat: threat ? +threat[1] : 0,
      threatLimit: threat ? +threat[2] : null,
      minions: document.querySelectorAll('#player-all-engaged-minions .card').length,
    };
  }

  /** How much we want a given ability, 0-100.
   *
   *  The reason the runs kept losing to the scheme was not that they played illegal moves, it was
   *  that `options()` clicked the first button every time. The first button is whatever the client
   *  happened to list first, so the choice between attacking and thwarting was effectively random,
   *  and a game is lost by ignoring the scheme long before it is won by hitting the villain.
   *
   *  Threat pressure decides it. Below half the limit there is room to attack; above it the scheme
   *  is the thing that ends the game and thwarting comes first.
   */
  rankOption(label, b) {
    const l = label.toLowerCase();
    const pressure = b.threatLimit ? b.threat / b.threatLimit : 0;
    // Attacking requires hero form, so getting out of alter-ego early is worth more than any single
    // action. Under real threat pressure the alter-ego side is the wrong place to be at all.
    if (/change form/.test(l)) return b.alterEgo ? (pressure < 0.7 ? 92 : 45) : 12;
    // Thwarting wins the right to keep playing; attacking is what eventually wins the game, and
    // in that order. Half the limit was far too patient: against a 7-threat scheme that ticks up
    // every villain phase, a single "when revealed" treachery took a comfortable 3 to a losing 7
    // between two of our turns, and the run had spent that turn attacking.
    if (/^thwart/.test(l))     return pressure >= 0.3 ? 100 : 70;
    if (/^attack/.test(l))     return pressure >= 0.3 ? 45 : 96;
    // Only worth a turn when the damage is actually dangerous; recovering at full health wastes it.
    if (/^recover/.test(l))    return (b.alterEgo && b.heroHp !== null && b.heroHp <= 5) ? 88 : 18;
    if (/^defense/.test(l))    return 32;
    if (/cancel/.test(l))      return -100;
    return 62;  // a card's own ability: usually why the card was played
  }


  /** Click a card that has an ability available, which is what puts the options on screen.
   *
   *  The missing rung. `options()` could only ever fire when `#option-buttons` already had buttons
   *  in it, but the client fills that div in response to clicking an activatable card: the whole
   *  Attack / Thwart / Change Form menu hangs off the identity card and does not exist until it is
   *  clicked. So a run could hold a full hand, a healthy hero and an untouched villain, and still
   *  have nothing to do but end the turn, which is exactly what the logs showed.
   *
   *  The identity card comes first because the basic actions live there and they are what actually
   *  moves a game toward winning; everything else in play is tried after it.
   */
  async useAbility() {
    const marked = [...document.querySelectorAll('#scene .card.highlight-effect')].filter(c => {
      const a = (c.parentElement && c.parentElement.id) || '';
      return !a.includes('hand-cards');   // playing from hand is its own gesture
    });
    if (!marked.length) return false;
    // A card whose ability led nowhere must not be clicked again, or the run spends the turn
    // opening and closing the same menu: one game logged ten `ability` steps in a row without the
    // board changing, because clicking toggles and the toggle itself moves the fingerprint.
    this.tried = this.tried || new Set();
    // Same reasoning as `board`: prefer the actual identity, which is where the basic actions live,
    // rather than anything that happens to sit in the hero area.
    const identityFirst = c => c.querySelector('.health') ? 0 : 1;
    const card = marked
      .filter(c => !this.tried.has(c.dataset.id))
      .sort((x, y) => identityFirst(x) - identityFirst(y))[0];
    if (!card) return false;

    this.tried.add(card.dataset.id);
    const before = this.fingerprint();
    card.click();
    await sleep(700);
    return this.fingerprint() === before ? false : 'ability';
  }

  /** Has anything that matters actually changed?
   *
   *  Deliberately coarser than `fingerprint`, which counts selections and highlights and so moves
   *  every time a card is merely clicked. This only moves when the game does.
   */
  progressMark() {
    const b = this.board();
    return [b.villainHp, b.threat, b.alterEgo, b.minions,
            document.querySelectorAll('#player-all-hand-cards .card').length].join('|');
  }

  async step() {
    // Ordered by how specific the gesture is. `ladder` rotates the starting point when the screen
    // stops responding, so an unrecognised mode still gets the other gestures tried against it.
    // A turn with nothing left to give should end rather than be picked at. Without this the
    // ladder keeps finding something clickable, and a single turn ran to 54 steps while the
    // villain sat at 11 health: every gesture "worked" and none of them did anything.
    const mark = this.progressMark();
    if (mark !== this.lastMark) {
      this.lastMark = mark;
      this.idle = 0;
      // Something happened, so abilities that were dead a moment ago may not be now. Holding the
      // list until end of turn left runs with a single marked card they had already tried and
      // nothing else to do.
      this.tried = new Set();
    } else {
      this.idle = (this.idle || 0) + 1;
    }
    if (this.idle > 8) {
      const ended = await this.endTurn();
      if (ended) { this.idle = 0; return ended; }
    }

    const acts = [
      () => this.unpause(), () => this.options(), () => this.pay(), () => this.targets(),
      () => this.useAbility(), () => this.playHand(), () => this.confirm(), () => this.endTurn(),
      () => this.escape(), () => this.anyButton(),
    ];
    for (let i = 0; i < acts.length; i++) {
      const r = await acts[(i + this.ladder) % acts.length]();
      if (r) return r;
    }
    return 'none';
  }

  async run(n) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const before = this.fingerprint();
      const act = await this.step();
      const after = this.fingerprint();
      if (before === after) { this.same++; this.ladder++; } else { this.same = 0; this.ladder = 0; this.escaped = false; }
      if (act === 'none') await this.ready(15000);
      const row = { act, ...this.health() };
      out.push(row); this.log.push(row);
      if (this.over()) { out.push({ act: 'GAME OVER', ...this.result() }); break; }
      if (this.same > 8) {
        if (await this.settle(after)) { this.same = 0; this.ladder = 0; continue; }
        out.push({ act: 'STALLED', diag: this.snapshot() }); break;
      }
    }
    return out;
  }
}
/** Fire-and-forget runner.
 *
 * A step takes a couple of seconds and the debugger's evaluate call times out at 45s, so awaiting
 * a long run from the console is not possible. This starts the loop and returns immediately; poll
 * `__auto.log` and `__auto.running` to follow it.
 */
Auto.prototype.start = function (n) {
  if (this.running) return 'already running';
  this.running = true; this.stop = false; this.target = n;
  (async () => {
    this.log.push({ act: 'ready', ...(await this.ready()) });
    for (let i = 0; i < n && !this.stop; i++) {
      const before = this.fingerprint();
      let act;
      try { act = await this.step(); } catch (e) { act = 'error:' + (e && e.message || e); }
      const after = this.fingerprint();
      if (before === after) { this.same++; this.ladder++; } else { this.same = 0; this.ladder = 0; this.escaped = false; }
      if (act === 'none') await this.ready(15000);
      this.log.push({ act, ...this.health(), ...this.board() });
      if (this.over()) { this.log.push({ act: 'GAME OVER', ...this.result() }); break; }
      if (this.same > 10) {
        if (await this.settle(after)) { this.same = 0; this.ladder = 0; continue; }
        this.log.push({ act: 'STALLED', diag: this.snapshot() }); break;
      }
    }
    this.running = false;
  })();
  return 'started';
};

window.__auto = new Auto();
return 'autoplay installed';
})()
