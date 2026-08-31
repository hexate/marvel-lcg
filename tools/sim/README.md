# Headless play simulator

Plays complete games with no UI, so a strategy question can be answered by running a
few hundred games instead of arguing about it. Built on `unit_test/harness.py`, which
supplies an `InputDevice` that answers prompts from a Python callable.

A game takes about a second. A hundred games with ten workers takes about twelve.

## Which deck plays, and why it matters

**Pass the custom deck's basename as the hero name.** `captain_america_stun_lock`, not
`captain_america`.

`GameFixture` calls `SceneLoader.NewScene(scenario, None, hero_names, seed)`, and
`FindJsonPath('Hero', ...)` searches `DECK_FOLDERS` before `STARTER_DECK_FOLDER`. So a bare
`captain_america` silently resolves to `deck/starter/`, and nothing in the result line says which
deck played.

That silence has already cost a full session of results. Every number in one sweep was produced on
starter decks while the tuned weight files were named for custom decks, so weights tuned against
`deck/custom/captain_america_stun_lock.json` were being applied to the starter deck. It also
produced a wrong conclusion, that Ant-Man losing to Rhino was a deck-building problem, when the
deck under test was the starter deck and not the built one.

The starter decks are the weak case by construction. A strategy result measured on them says
almost nothing about a built deck, and the two are not comparable to each other.

Match the weights file to the deck. `weights_rhino_<deck>.json` is named after the deck it was
tuned on, and that name is the only thing recording the pairing.

`deck/custom/` is gitignored player data, so any number that depends on it cannot be reproduced
from a clean clone. Say which deck a number came from whenever you report one.

## What search is worth, and what budget to use

Measured on `captain_america_stun_lock` against Rhino, the deck in `deck/custom/` with its
matching tuned weights. Seeds 800-839, so 40 games an arm.

| arm | wins | mean damage | wall for 40 games |
| --- | --- | --- | --- |
| scorer alone | 1/40 | 20.85 | 2s |
| `search:<w>:20:1` | 13/40 | 25.18 | 170s |
| `search:<w>:40:1` | 15/40 | 25.82 | 421s |

**Use 20 variants.** Search itself is not marginal: 1 win against 15 is Fisher one-sided
p=0.00006, and it is worth about +5 damage a game against the 29 Rhino needs. But 40 variants is
not reliably better than 20 (paired damage better on 14 seeds, worse on 7, tied on 19, two-sided
sign p=0.189) and costs two and a half times as much. On an earlier run 60 variants won no more
games than 40. The curve is flat past 20.

**Tuning the weights further is finished on this deck, and the audit will lie to you about that.**
Three leads from `audit.py`, each looking like an obvious blind spot, all measured out at zero or
worse on 60 fresh seeds:

- Super-Soldier Serum played 0 times in 30 offers, on a deck whose stun payoffs need the physical
  resource it generates. Classifying it as an engine: 20.53 against 20.73, 45 of 60 games
  identical, sign p=1.000.
- Defending 1.35 times a game on a deck built around Counter-Punch and Indomitable. Forcing it to
  4.03: damage 20.53 down to 18.57.
- Changing form offered 120 times and taken 6. Forcing more flips: down to 16.77 at the extreme.

Those are not blind spots. They are the hill climber correctly declining actions that do not pay
against a villain this fast, and the weights sit at a local optimum where every direction is
worse. What moves the result is search, because it changes the plan mid-game in a way one fixed
weight vector cannot express. Read a high offered-versus-taken ratio as a hypothesis, never as a
bug, and check it on fresh seeds before believing it.

## Files

| File | What it does |
| --- | --- |
| `deck_check.py` | Reports how the policy classifies every card in a deck. **Run this first.** |
| `policy.py` | Prompt handling and card knowledge, shared by every policy. |
| `utility.py` | Scores each legal action as a weighted sum of board features. |
| `weights.py` | Default weights, no game imports. |
| `tune.py` | Hill-climbs the weights against the simulator. |
| `explain.py` | Reads a tuned weight set back out as rules a person can follow. |
| `audit.py` | Counts what the engine offered against what the policy took. |
| `run_game.py` | One game, one process, prints a JSON result. |
| `batch.py` | Runs many games in parallel and summarises. |
| `scenario_clock.py` | Each scenario's damage and threat budget, from card data. No simulation. |

## Onboarding a new deck

Do these in order. Steps 1 to 3 are not optional, and skipping them is how a tuning run
gets wasted.

**1. Understand every card.**

```sh
.venv/bin/python tools/sim/deck_check.py ant_man
```

It prints every card with the category the scorer assigns, and flags three things:

* `UNCLASSIFIED` — the card fell into the junk bin and is ranked below everything.
* `unmodelled: …` — the card uses a mechanic the scorer has no concept of.
* `conditional` — the card is only playable in some states, which the scorer does not
  check, so it can rank a card it cannot cast.

Resolve the unclassified ones before going further. The unmodelled list is a judgement
call: `draw` on a minor card can wait, `retaliate` on the hero's signature upgrade
cannot.

**2. Baseline ten games and read the telemetry.**

Ten losses out of ten is already enough signal to change a rule. Look for numbers that
contradict the deck's plan: a deck built on changing form that changes form once a
game, a hero with a thwart ability that thwarts 0.1 times a game.

**3. Audit offered against taken.**

```sh
.venv/bin/python tools/sim/audit.py rhino ant_man util:weights.json
```

A high offered count with a low taken count is a lead. Every large improvement in this
work came from this table, never from tuning a number.

**4. Only now tune.**

```sh
TRAIN_N=60 .venv/bin/python tools/sim/tune.py rhino ant_man 29 200
```

**5. Verify on seeds the tuner never saw**, in blocks of at least 100.

## Why step 1 is mandatory

Ant-Man was tuned for twenty minutes before anyone checked whether the policy could see
his cards. It could not. His form-change payoffs, `Giant_Nuisance` and `Puny_Pest`, were
offered 43 times across ten games and taken zero, because the response handler only
matched options named `Play`. His compounding upgrades were filed as generic board
filler and played 3 times in 49 chances. The second ability on a two-ability card was
invisible, because a card with two abilities numbers them `Hero_Action` and
`Hero_Action_1`. Four cards were reprint stubs carrying only a `full_link` to the real
card, so they had no text and no cost and landed in the junk bin.

The tuner did its job perfectly on that broken hero and concluded he should stop
changing form, which is the opposite of how Ant-Man is played. A tuner cannot tell you
a card is invisible to it. It quietly routes around the card and hands you a confident
set of weights.

After fixing those, he alternates Giant and Tiny across 88% of his turns, which is the
rhythm the deck is built for, and he won his first game.

## Measuring

Small evaluations mislead, and they have misled this work twice. A configuration that
won 1 game in 10 won 1 in 100 once the seeds changed. Later, a held-out set of 25 read
1 win and looked like total overfitting, and two fresh blocks of 100 disagreed with it.

Use 10 games to catch a broken rule. Use 100 fresh seeds before believing a number.
Train and test seeds must be disjoint, and picking them odd/even is not a real split.

Fitness is deliberately dense, because wins are far too rare at this level of play to
steer a search:

    fitness = mean(damage_done / villain_hp) + 1.0 * win_rate

That has one known failure: a damage-based score never punishes losing to the scheme, so
the tuner will race past the point of no return. `utility.py` carries a hard thwart
floor that weights cannot override, set at the villain's scheme value plus three,
because one villain phase moves threat by about four.

## Weights do not transfer

Tuned weights are per hero, per deck, per villain, which is why the files are named
`weights_<scenario>_<deck>.json`. Captain America's tuned strategy blocks every attack
from 70% health down; Ant-Man's never blocks at all. Both are correct. Cap's
"I Can Do This All Day!" readies him after a block so it costs nothing, and Ant-Man has
no such ability, so a block costs his whole next activation.

## Things that cost a day each, written down so they cost nobody else one

* **Cards ready at the END of the player phase** (`Faces.ReadyAll` in
  `game/player/element/player_phase.py:93`), before the villain phase. A hero who
  defends is still exhausted on its next turn and loses that activation entirely. A
  policy that defends every attack never attacks at all.
* **`End Phase` is the discard-and-redraw step** (`MayDiscardHandCardsAndDrawUpToMax`).
  Declining it leaves a dead hand dead for the rest of the game.
* **An Attack or Thwart can list legal targets while asking for none of them**
  (`target_num_range [0, 0]`). Supplying one is rejected and the prompt repeats until
  the turn is wasted.
* **A forced prompt accepts id 0 only when a single option needs no targets**
  (`engine/controller/controller.py:271`). On a two-option forced choice, declining
  loops.
* **Multi-form heroes never offer `Change_Form`.** Ant-Man uses
  `Change_To_AVENGER_GIANT` and friends, so matching the common name leaves him in
  alter-ego for the whole game.
* **Turn options are named by ACTION, not by card** (`Attack`, `Play`, `Thwart`). The
  card is `bind_id`, which is `face.card.object_id`.
* **A `Play` option's legal target is usually the player**, not the card's ability
  target, which is asked at a later prompt.
* **Costs are not always numbers.** A typed cost arrives as its resource letters, `RRR`
  for three physical, and `int()` on that raises.
* **Reprints are stub entries with only `full_link`**, so a lookup by the printed id
  returns no text and no cost.
* **`GameOverReason.players_won` is only a type annotation** until the game ends in a
  win or loss. Read it with `getattr`.
* **`Engine.SaveCrash` hard-codes `./crash.json`** and calls `exit(-1)`. `run_game.py`
  neuters it so a batch cannot clobber a real crash repro.
* **Statistics are off under `-test`**, so simulated games never touch
  `statistics.json`.
* **The policy catches its own exceptions**, so a NameError in scoring looks exactly
  like bad play: cards stop being played and the bot cycles its hand. `run_game.py`
  reports `policy_errors` and `first_error`; check them before believing a regression.
* Some scenarios are won by clearing threat, not by damage. Batroc resets when he would
  be defeated, and MaGog is decided on ratings counters.
