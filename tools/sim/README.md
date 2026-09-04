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

## Turn-level search (`turnplan.py`): doubles the scorer, still loses to policy search

Built on `ResumeGameLoop`, and the first thing tried that discriminates at all. Where evaluating
single moves gave one distinct outcome at five of six decisions, committing to a whole turn gave
five distinct outcomes among ten candidates at the same decision, one of them reaching 29 damage,
a win, where the scorer reached 17. The unit that carries information is a turn, because it is the
first one that can say what it will *not* do.

Measured on `captain_america_stun_lock` against Rhino, 60 seeds:

| policy | wins | damage | wall |
| --- | --- | --- | --- |
| scorer alone | 6/60 | 20.35 | 2s |
| `turnplan` | 12/60 | 22.72 | 147s |
| `search:...:20:1` | 20/60 | 25.15 | 260s |

So it doubles the scorer and loses to the policy search that already existed. Two ways of giving
it more were measured and neither helps: hill-climbing the turn over three passes instead of one
gives 12/60 at 206s, and widening the candidate set to 93 rollouts a game gives 11/60 at 253s. One
pass over the neighbourhood already exhausts it.

Design notes worth keeping, because the first two versions were worse than the third:

- **Compare against a rollout, not against the current position.** Scoring candidates against the
  static value of the position made every turn commit to one or two actions and end, which is far
  less than the scorer plays and strictly worse. The baseline has to be the scorer playing the
  turn its own way.
- **Perturb the scorer's turn, do not enumerate short ones.** Truncating to one or two actions
  scored 9/60. Taking the turn the scorer plays and trying it with one action dropped or one
  declined action added scored 12/60.
- The `TurnScript` ends the turn when its script runs out rather than handing the rest back to the
  scorer. Handing it back is what made move-level candidates collapse to the same game.

**Combining them was tried and does not help.** They work at different levels, policy search
choosing the weights for the whole continuation and turn planning choosing which actions this turn
contains, so composing them looked like the obvious win. Order matters and was respected: weights
first, then the turn planned against the continuation that will actually follow it.

On seeds 900-959 it looked like one, 22 wins in 60 against policy search's 20. On fresh seeds
1000-1059 it reversed: 13 in 60 against 15, paired damage better on 12 seeds and worse on 18, tie
on 30, two-sided sign p=0.36. The first result was noise and the fresh-seed check is the only
reason it was not reported as an improvement. The code was reverted.

So `search:...:20:1` remains the best configuration measured, and turn planning is a second,
independent way to beat the plain scorer rather than an addition to the first.

## Action-level search: the engine now allows it, and it still does not discriminate

`World.ResumeGameLoop` (N21) removed the blocker that stopped a search evaluating a single move:
a position captured mid-turn can now be continued from where it was, instead of having a fresh
round begun on top of it. The machinery is verified. Forcing the action the plain policy would
have taken anyway reproduces its game exactly, rounds, damage and step count all identical, which
is the control that says forcing works.

It buys almost nothing, and the measurement says why. Evaluating every option at six consecutive
decision points on `captain_america_stun_lock`:

| decision | options | distinct outcomes |
| --- | --- | --- |
| 1 | 4 | 1 |
| 2 | 6 | 1 |
| 3 | 6 | 1 |
| 4 | 5 | 1 |
| 5 | 4 | 1 |
| 6 | 6 | 2 |

At five of six decisions every option leads to the identical final game. The continuation policy is
order-invariant: force any action first and it still plays the same set of actions for the rest of
the turn, so the forced choice is reordered rather than changed. That is also why policy-level
search helps and this does not. Changing the weights changes the whole continuation; changing one
action changes something the continuation immediately undoes.

**So the useful unit is a turn, not a move.** To get signal, a candidate has to commit to *which
actions are taken and which are not* for the whole turn, and the continuation has to respect that
rather than re-deriving it. That is buildable on `ResumeGameLoop` and is the remaining piece.

Two traps to know before building it. Forcing an action by option id cannot survive a resume,
because `ObjectManager` allocates effect ids afresh every time options are offered, so an id from
the original prompt names a different effect in the clone; use a stable identity such as name plus
`bind_id`. And `player_action.py:258` does `game = Engine.game`, so a rollout drives the clone's
board while using the *live* game's replay module, which is how a rollout empties the live
`history_inputs` and makes a later `Pop` raise `IndexError`. That is the likely mechanism behind
J42.

## The policy-space search is at its ceiling, and here is the measurement that says so

Worth reading before trying to improve the searching bot, because the obvious next ideas have all
been run.

The search proposes candidate weight sets, plays each to the end of the game, and keeps the best.
The natural theory of why it helps is that it finds *plans*. It does not. Measured on
`captain_america_stun_lock` against Rhino, 60 seeds:

| candidates | what they are | wins | damage |
| --- | --- | --- | --- |
| 7 | random gaussian noise on 2-5 of 52 weights | 13/60 | 23.62 |
| 7 | six hand-written turn plans (aggro, combo, defend, build, control, regroup) | 14/60 | 23.68 |
| 20 | random noise | 20/60 | 25.15 |

Hand-written coherent plans, each a coordinated move across the weights that a person would
describe in words, match random noise exactly at the same candidate count. What buys wins is the
*number* of candidates, not their quality, and that number plateaus: 20 variants and 40 variants
are not reliably different, and 60 wins no more than 40.

So the search is not reasoning about plans, it is sampling. Sampling more helps until it does not,
and every knob governing the sampling is already at its optimum: variants past 20, sigma at 2.0,
and search frequency at once per round were each measured flat or worse.

**What this rules out.** Better proposals, more proposals, and better settings. All three are done.

**What is left.** Evaluating the actual move rather than a policy that would tend to make it. That
is action-level search, and it is blocked by `World.OnGameLoop` being `while not is_game_over:
game_round()`: it begins a round rather than resuming a turn in progress, so a clone taken
mid-decision replays from the round boundary and every candidate scores the same. Giving the
engine an entry point that re-enters the phase machinery where the clone was taken is the one
remaining change with real headroom behind it, and it is a `game/` change rather than a simulator
one.

## Keeping the forward model honest, and how to debug it when it is not

A rollout must not change the game it is predicting. That invariant has been broken three
separate times, each time silently: the games still finish, the numbers still look plausible, and
nothing raises. Everything measured while it is broken is measured against a different game from
the one being played.

**Check it with one command, after touching anything a rollout drives.**

    .venv/bin/python tools/sim/check_isolation.py rhino captain_america_stun_lock

`search:<w>:1:1` perturbs nothing and adopts nothing, so it must replay `util:<w>` exactly. Any
disagreement is a leak. It was 17 of 60 seeds before the nested-container fix and is 6 of 60 now.
Zero has never been reached, so treat the number as a ratchet: never let it rise.

**When it is non-zero, diff the logs, not the state.** This matters because state diffing failed
repeatedly and convincingly. A content-aware fingerprint of everything reachable from `Engine.game`
reported that nothing had changed, across every rollout, while the games demonstrably diverged. The
fingerprints could not see it.

What works: run both arms, suppress the rollout's own output by saving and restoring
`Log.all_log_text` around `playout`, and diff the results. The two logs agree for hundreds of lines
and then one contains an event the other lacks, which names the mechanism outright. That is how
Retaliate was found going missing, from three lines of "Captain America would deal 1 damage to
Rhino" present in one game and absent in the other.

**Four traps, each of which looks like a correct fix and is not:**

1. *A shallow snapshot is not enough.* Keywords live two levels down,
   `self.keywords[keyword][face] = diff` (`card_face.py:231`), so restoring an object's own
   attributes hands back the very inner dict the rollout mutated. Restore containers recursively.
   Depth 3 is enough; 5 and 8 change nothing.
2. *Restoring bindings and restoring contents are different things.* `__dict__.copy()` is shallow,
   so it puts attribute references back while leaving in-place mutation intact. Both are needed.
3. *Engine code reaches state through `Engine.game`, not through the world.* `player_action.py:258`
   does `game = Engine.game`, so a rollout drives the clone's board with the live replay module.
   That is a genuine cross-contamination and it was **not** the cause of J42: swapping it left the
   count at exactly 17. Fix it for its own sake, not as a theory about this.
4. *Identical results across a code change mean the change did not run.* Twice. Once a predicate
   matched `physical resource` against text reading `[physical] resource`, once a search arm came
   back matching baseline to two decimals. Neither was a null result.

## The alter-ego cycle as a turn plan: the fix that works

Going down to alter-ego, healing, and coming back up is the one plan the scorer provably cannot
represent. It spans turns, so a policy that ranks single actions can only price the first step,
and flipping down looks terrible on its own because the payoff arrives two turns later. That is
why `flip_ae` tunes to -16.29 and the bot flips 0 times in 92 offers.

`CycleScript` in `turnplan.py` makes the whole cycle one decision: flip down, recover until healthy,
flip back up, then hand control to the scorer. `TurnPlanPolicy` offers it as one candidate among the
turn scripts, so the rollout accepts or rejects it on end-of-game value rather than turn-end value.

Measured on `ant_man_multiple_man_protection`, identical settings, cycle the only difference:

| seeds | arm | wins | mean damage | cycles/game | alter-ego rounds |
| --- | --- | --- | --- | --- | --- |
| 2000-2099 | off | 2/100 | 18.66 | 0.00 | 0.32 |
| 2000-2099 | on | 6/100 | 20.56 | 0.42 | 0.83 |
| 2200-2299 | off | 2/100 | 18.61 | 0.00 | 0.25 |
| 2200-2299 | on | 7/100 | 20.81 | 0.46 | 0.87 |

Paired damage: better on 50 seeds against 16 in the first block, 53 against 10 in the second, sign
test p<0.0001 both times. **It replicates**, which almost nothing else in this simulator's history
has done on a first fresh-seed check.

Three implementation details, each of which would have made it silently useless:

- The plan must **survive the per-round replan**, or the planner re-decides every round and the
  cycle never finishes.
- It must be able to **abort**, so that if nothing on offer goes downstairs it gives up rather than
  stalling into the turn-burn guard.
- It is **one candidate among the others**, not an override. The rollout declines it often, which
  is the point: on the first smoke test it evaluated the cycle and chose two ordinary turn plans.

Note also what this says about the earlier failure. Giving the trip home a flat `flip_up` weight
made things worse, because the value of the cycle is in *knowing when* to take it, not in having it
priced. As a scored action it is noise; as a plan chosen by playing the game out, it is worth about
two damage a game.

## Deck hints help only as complete lines, and only if the line is worth something

Tested on the strongest available hint, from someone who plays the deck: Ant-Man in Tiny form uses
Army of Ants for damage. The card is "Hero Action: if you are in [[Tiny]] hero form, exhaust Army
of Ants -> deal 1 damage", three copies, and it exhausts the *support* rather than the hero, so it
is free damage. The audit backed the hint up: offered 74 times and taken 30, roughly seven damage a
game unclaimed on a deck averaging 17 of the 29 it needs.

Three versions were measured on `ant_man_multiple_man_protection`, 100 seeds, against turn planning
with the cycle alone at 6/100 and 20.56 damage:

| version | wins | damage |
| --- | --- | --- |
| no hint | 6/100 | 20.56 |
| raise the generic `hero_action` weight | 3/200-scale, worse | 17.16 to 16.39 |
| half the line: reach Tiny, spend the ants, stop | 3/100 | 20.18 |
| the whole line: ants, then Resize into Giant, then attack | 5/100 | 20.35 |

Paired damage for the whole line against no hint: better on 25 seeds, worse on 25, p=1.0000.
**Exactly neutral.** All of it was reverted.

Three things this establishes, and the first two are worth more than the null result:

- **A hint cannot be a weight.** Raising `hero_action` made things worse, the same way a flat
  `flip_up` weight did. Pricing an action does not create a plan.
- **A half-line is worse than no line.** Stopping after the ants pays for a form change to collect
  1-damage triggers and leaves the hero in Tiny where he hits weakly: 20.18 against 20.56 for not
  bothering. Completing the line recovers most of that, 20.35, and attacks more, 2.75 against 2.41.
- **Being right about the mechanism is not enough.** The line is real, the planner chooses it 0.72
  times a game, and it still does not beat the alternative. Three ant triggers are worth about 3
  damage; the tempo and the weak Tiny attack cost about the same.

Contrast with the alter-ego cycle, which is the same shape and does pay, +2 damage a game,
replicated on two fresh seed blocks. The difference is size: healing changes whether the hero
survives to keep attacking, and 1-damage triggers do not change anything structural. A hint is
worth encoding when the payoff is structural, not merely positive.

## Policy iteration does not work here, and the reason is the useful part

The obvious next step after the cycle, and it fails significantly. A search estimates a position by
what its rollout policy achieves from there, so greedy rollouts should systematically undervalue
anything needing setup. Replacing the rollout policy with one that takes the alter-ego cycle on a
rule ought to fix that bias.

It makes things worse. `ant_man_multiple_man_protection`, search at 20 variants, 100 seeds: greedy
rollouts win 4 at 19.90 damage, cycling rollouts win 3 at 18.87, and paired damage is better on 6
seeds against **worse on 27**, sign test p=0.0003.

**The same mechanism helps when chosen and hurts when imposed.** As a candidate the planner
evaluates and usually declines, the cycle is worth about +2 damage a game and replicates on fresh
seeds. As a rule inside the rollout it costs about 1 damage a game. The value was never in having
the cycle available, it is in knowing when to take it, and a rule fires in exactly the positions a
search would decline.

That also warns against the intuition that a better rollout policy gives better estimates. A
rollout policy is not trying to play well, it is trying to be an unbiased-enough sample of what
follows. Making it opinionated makes the estimates opinionated in the same direction, and the
search then cannot see past its own assumption. The code was removed.

## Three-form heroes are modelled as two, and it poisons their tuning

Ant-Man is Giant, Tiny and Scott Lang. `deck/custom` holds two Ant-Man decks and a Ms. Marvel
deck, so this is not one hero's problem.

`option_form` names only the *destination*, so the scorer cannot tell these apart:

- Giant to Tiny, a lateral hero-form switch
- Scott Lang to Tiny, the trip home from alter-ego

Both score `flip_tiny`. Coming back up therefore competes with playing a card and usually loses.
Measured with flipping forced on, the bot spent **4.83 of 5.9 rounds in alter-ego** with
`ae_action` at exactly 0.00. It goes down and cannot find its way back.

**That poisons the weights.** `flip_ae` is tuned to -16.29 on the Protection deck, so the bot
never flips at all: 92 offers, 0 taken. That is not a bad weight, it is the hill climber correctly
concluding that going downstairs is a trap while the bot cannot come back. Every experiment run on
top of those weights inherits the assumption. It also explains the shape of the failure: Ant-Man
dies in 85% of games, against Captain America's 59%.

**An attempted fix made it worse, and the reason is worth knowing.** Scoring the trip home with
its own flat `flip_up` weight dropped mean damage from 17.16 to 14.77, because the lateral weights
it replaced carry context terms: `flip_tiny + flip_tiny_x_pressure * press` reaches about 7 under
pressure, where a flat 2.0 does not. Retuning with `flip_up` available did not rescue it; the
tuner left `flip_ae` at -16.29 and never explored the new weight. Both changes were reverted.

Two things checked and ruled out while chasing this, so nobody repeats them: health is *not*
misreported in alter-ego (12/12 then 10/12, correct), and Recover is *not* unreachable (it is
offered; at 10 of 12 health it scores 1.33 and loses to everything, so the bot only values healing
once Rhino can kill it in two hits from full).

**What it actually needs.** The alter-ego cycle is a multi-turn plan, go down, recover, come back
up, and a scorer that ranks one action at a time cannot represent it. Any real fix wants the whole
cycle evaluated as a unit, and a replacement for `flip_up` that keeps the context sensitivity the
lateral weights already have.

## Onboarding a deck or a card: how to find what the policy cannot see

The policy only knows what a predicate in `policy.py` tells it. Everything else is invisible, and
invisible is silent: the tuner will route around a card and hand you confident weights, and a
search will optimise a plan the deck is not trying to execute. This is the procedure for finding
those gaps, written after a session where six plausible fixes measured at zero and the seventh
turned out to be a string that never matched.

**1. Run `deck_check.py <deck>`.** It reports the category the scorer puts every card in, plus
UNCLASSIFIED cards, unmodelled mechanics and conditional playability. Resolve what it flags before
tuning anything. A card in the junk category is ranked last in every decision it appears in.

**2. Read the printed text of every card the deck actually plays.** Not the category, the text.
`data/cards.json` has it under `text`. This is where the deck's plan lives, and it is the step
that found the only real gap in a whole session: Heroic Strike deals 6 damage *and stuns if you
paid with a physical resource*, Tackle stuns *and deals 3 on the same condition*, and the payment
picker was choosing by which card was cheapest to lose while literally discarding the resource
letter. A deck named Stun Lock was stunning by accident.

**3. Watch out for bracketed icons.** The printed text writes resource and status icons in
brackets: `using a [physical] resource`, not `using a physical resource`. A predicate matching the
unbracketed form compiles, runs, and never fires. Match both forms, and see step 6.

**4. Run `audit.py <scenario> <deck> <mode> <seeds...>`.** It counts, per card, how often something
was offered and how often it was taken. A high offered count with a near-zero taken count is a
lead. **It is a lead and not a bug.** Three such leads on `captain_america_stun_lock` all measured
at zero or worse: Super-Soldier Serum at 0 of 30 offers, defending at 1.35 a game on a deck built
around Counter-Punch, form changes at 6 of 120. The hill climber was right and the audit only
showed that it had made a choice.

**5. Ask what the deck wins by, then ask whether any feature encodes it.** A Protection deck wins
by surviving and grinding. `utility.py` has no feature for trading time for safety, so no weight
vector expresses that plan and no amount of searching over those weights finds it. This is why
search actively *harmed* `ant_man_multiple_man_protection`, dropping it from 16.7 to 15.3 damage,
while helping every aggressive configuration.

**6. Prove your predicate fires before you believe the measurement.** The resource-type fix came
back byte-identical to baseline, 19/60 wins and 24.95 damage to two decimals. Identical numbers
across a code change are not a null result, they mean the code did not run. Assert the predicate
returns what you expect on a named card, or diff a game log, before concluding anything.

**7. Validate on fresh seeds, always.** Pick a change on one seed block and confirm it on another
you have not looked at. Selecting a value because it looked best on a block and then reporting
that block is circular, and it is how a `play_econ` sweep produced a 21.1 that evaporated to a
20.73 against 20.53 with p=1.000 on 60 fresh seeds.

**8. Expect the honest answer to be zero.** Seven targeted improvements in one session, six at
exactly zero and one at plus one win in sixty. The weights sit at a local optimum and single-action
ranking is the wrong lever. What is left after that is structural, not parametric.

## Benchmark (authoritative): 200 seeds, fixed forward model, with the alter-ego cycle

Seeds 2000-2199, each deck with its own tuned weights, isolation verified clean.

**captain_america_stun_lock vs Rhino**

| policy | wins | rate | mean damage | sd | wall |
| --- | --- | --- | --- | --- | --- |
| scorer alone (`util`) | 16/200 | 8.0% | 20.00 | 5.19 | 10s |
| `turnplan` | 36/200 | 18.0% | 23.16 | 4.94 | 715s |
| `search:<w>:20:1` | **79/200** | **39.5%** | 25.93 | 4.39 | 880s |

**ant_man_multiple_man_protection vs Rhino**

| policy | wins | rate | mean damage | sd | wall |
| --- | --- | --- | --- | --- | --- |
| scorer alone (`util`) | 4/200 | 2.0% | 17.16 | 4.44 | 11s |
| `turnplan` | **17/200** | **8.5%** | 20.75 | 4.60 | 1323s |
| `search:<w>:20:1` | 13/200 | 6.5% | 20.30 | 4.52 | 1213s |

Turn planning against the scorer is p=0.0022 on Captain America; search against the scorer is
p=2.7e-14.

**The best policy is deck-dependent, which is new.** Search dominates on Captain America, 39.5%
against turn planning's 18.0%. On Ant-Man turn planning is ahead, 17 wins against 13, reversing the
12-to-13 it showed before the cycle existed. The cycle is the whole difference: `turnplan` uses it
0.47 times a game on Ant-Man and `search` cannot use it at all, because a weight vector cannot
express a plan that spans turns. On Captain America the same planner fires it 0.02 times a game and
correctly leaves it alone, since that deck wins in hero form.

So the two mechanisms are not ranked, they are suited to different decks: search for decks that win
by pressing an advantage, turn planning for decks that need a multi-turn manoeuvre. Run both before
concluding which is better for a new deck.

Also note the standard deviations, 5.19 to 4.94 to 4.39 on Captain America. Better policies reach
further *and* more reliably.

## Onboarding a deck or a card: how to find what the policy cannot see

The policy only knows what a predicate in `policy.py` tells it. Everything else is invisible, and
invisible is silent: the tuner will route around a card and hand you confident weights, and a
search will optimise a plan the deck is not trying to execute. This is the procedure for finding
those gaps, written after a session where six plausible fixes measured at zero and the seventh
turned out to be a string that never matched.

**1. Run `deck_check.py <deck>`.** It reports the category the scorer puts every card in, plus
UNCLASSIFIED cards, unmodelled mechanics and conditional playability. Resolve what it flags before
tuning anything. A card in the junk category is ranked last in every decision it appears in.

**2. Read the printed text of every card the deck actually plays.** Not the category, the text.
`data/cards.json` has it under `text`. This is where the deck's plan lives, and it is the step
that found the only real gap in a whole session: Heroic Strike deals 6 damage *and stuns if you
paid with a physical resource*, Tackle stuns *and deals 3 on the same condition*, and the payment
picker was choosing by which card was cheapest to lose while literally discarding the resource
letter. A deck named Stun Lock was stunning by accident.

**3. Watch out for bracketed icons.** The printed text writes resource and status icons in
brackets: `using a [physical] resource`, not `using a physical resource`. A predicate matching the
unbracketed form compiles, runs, and never fires. Match both forms, and see step 6.

**4. Run `audit.py <scenario> <deck> <mode> <seeds...>`.** It counts, per card, how often something
was offered and how often it was taken. A high offered count with a near-zero taken count is a
lead. **It is a lead and not a bug.** Three such leads on `captain_america_stun_lock` all measured
at zero or worse: Super-Soldier Serum at 0 of 30 offers, defending at 1.35 a game on a deck built
around Counter-Punch, form changes at 6 of 120. The hill climber was right and the audit only
showed that it had made a choice.

**5. Ask what the deck wins by, then ask whether any feature encodes it.** A Protection deck wins
by surviving and grinding. `utility.py` has no feature for trading time for safety, so no weight
vector expresses that plan and no amount of searching over those weights finds it. This is why
search actively *harmed* `ant_man_multiple_man_protection`, dropping it from 16.7 to 15.3 damage,
while helping every aggressive configuration.

**6. Prove your predicate fires before you believe the measurement.** The resource-type fix came
back byte-identical to baseline, 19/60 wins and 24.95 damage to two decimals. Identical numbers
across a code change are not a null result, they mean the code did not run. Assert the predicate
returns what you expect on a named card, or diff a game log, before concluding anything.

**7. Validate on fresh seeds, always.** Pick a change on one seed block and confirm it on another
you have not looked at. Selecting a value because it looked best on a block and then reporting
that block is circular, and it is how a `play_econ` sweep produced a 21.1 that evaporated to a
20.73 against 20.53 with p=1.000 on 60 fresh seeds.

**8. Expect the honest answer to be zero.** Seven targeted improvements in one session, six at
exactly zero and one at plus one win in sixty. The weights sit at a local optimum and single-action
ranking is the wrong lever. What is left after that is structural, not parametric.

## Benchmark (authoritative): 200 fresh seeds, fixed forward model

Everything below this section was measured before J42 was closed, with a forward model that was
silently corrupting live keyword state. These are the numbers to quote.

`captain_america_stun_lock` against Rhino, seeds 2000-2199, its matching tuned weights.

| policy | wins | rate | mean damage | sd | wall for 200 games |
| --- | --- | --- | --- | --- | --- |
| scorer alone (`util`) | 16/200 | 8.0% | 20.00 | 5.19 | 10s |
| `turnplan` | 35/200 | 17.5% | 23.16 | 4.90 | 661s |
| `search:<w>:20:1` | **74/200** | **37.0%** | 25.84 | 4.41 | 881s |

Fisher one-sided: search against the scorer p≈1e-12, turn planning against the scorer p=0.0033,
search against turn planning p≈8.5e-06. All three orderings are real at this sample size, which
60 seeds could not establish.

The same benchmark on `ant_man_multiple_man_protection`, seeds 2000-2199, its own tuned weights,
isolation verified clean at 0 of 40:

| policy | wins | rate | mean damage | sd | defends/round |
| --- | --- | --- | --- | --- | --- |
| scorer alone | 3/200 | 1.5% | 17.19 | 4.23 | 0.69 |
| `turnplan` | 12/200 | 6.0% | 19.84 | 4.86 | 0.69 |
| `search:<w>:20:1` | 13/200 | 6.5% | 20.64 | 4.82 | 0.67 |

Search against the scorer: p=0.0094 on wins, and paired damage better on 152 seeds against 13,
p≈3e-31. **This reverses an earlier finding.** On 20 seeds with the broken forward model search
appeared to make this deck worse, 16.7 damage down to 15.3, and that was written up as the scorer
being unable to represent a defensive plan. It was the leak: rollouts were stripping keyword state,
which costs a Protection deck more than any other kind. Defends per round barely move, 0.69 to
0.67, so search is not fighting the deck's plan.

The gap to the line explains the difference between the two decks better than anything about
strategy. Ant-Man's scorer is 11.8 damage short of the 29 needed and search adds about 3.5.
Captain America's is 9.0 short and search adds about 5.8, which reaches the threshold often enough
to convert. Same mechanism, different starting point.

**A deck's engine card can be structurally unplayable, and that is worth checking before tuning.**
`deck_check` on `ant_man_multiple_man_protection` showed Desperate Defense, a three-copy card in a
forty-card deck, filed as "other" and so ranked near junk. Reading it explains the deck: +2 DEF
when you defend, and if the attack does nothing, ready your hero. Unflappable draws on the same
trigger, Electrostatic Armor deals 1 to the attacker. Defending is this deck's engine, not its
cost, and nothing in the scorer could express that.

`audit.py` then found the real problem, which was not the weights. `WhenUnitWouldDefend/Play` was
offered 6 times and taken 0, and Desperate Defense was offered 6 times and played 0. The response
handler only accepted options with `cost_of(o) == 0`, and Desperate Defense costs 1, so the card
the deck is built around was structurally excluded from the one window it works at. Indomitable on
the Captain America list is the same shape. Allowing paid responses when the card pays you for
defending takes it to 6 of 6.

**It changes nothing measurable, and the weight that looked obvious makes things worse.** Over 200
seeds, greedy: Ant-Man 3/200 at 17.19 damage before, 4/200 at 17.16 after; Captain America 16/200
at 20.00 both before and after, identical. Adding a `def_hero_x_payoff` term so the scorer defends
more when the payoffs are in hand raised defends per round from 0.69 to 0.83 and *cost* wins:
Ant-Man to 2/200, Captain America to 9/200 at 18.75 damage. That term was removed.

The likely reason the payoff never pays: +2 DEF has to reduce the hit to zero for the ready and the
draw to trigger, and Rhino hits for 3 to 6. The card is right for the deck and wrong for this
matchup. Kept anyway, on correctness grounds rather than performance, because a bot that never
plays a three-copy card is not playing the deck.

**Risk-seeking evaluation was tried and does not work.** Worth recording because the reasoning is
appealing and the naive implementation is a silent no-op.

Winning is a threshold: nothing is paid for 24 of the 29 needed, so when the mean sits below the
line, variance is an asset and the search should prefer a line that might reach 29 over one that
comfortably reaches 24. `position_value` is linear in damage, which makes the search risk-neutral,
and `tune.py` already learned the same lesson in the other direction, cubing progress because
"wins live in the tail and averaging rewards playing safe".

**A convex value function changes nothing.** The search evaluates one rollout per candidate under
common random numbers and takes an argmax, so any increasing function of damage gives the same
ordering and the same decisions. Rewarding the tail needs a distribution, not a transform, which
means several futures per candidate aggregated convexly.

Measured on `ant_man_multiple_man_protection`, 100 seeds, futures paired across candidates:

| arm | wins | damage |
| --- | --- | --- |
| 20 candidates, 1 future (current) | 8/100 | 20.42 |
| 7 candidates, 3 futures, plain mean | 5/100 | 19.08 |
| 7 candidates, 3 futures, cubed | 6/100 | 19.06 |
| 20 candidates, 3 futures, cubed (3x budget) | 7/100 | 20.16 |

The mechanism is real and visible: cubing beats its own plain-mean control, 6 against 5, with mean
damage flat at 19.06 against 19.08, which is exactly the signature of trading expected value for
threshold-crossing. It just does not pay. Taking candidates to afford futures costs more than it
returns, and adding futures at 3x budget still loses to the baseline.

The likely reason is that common random numbers already make the single-sample comparison paired
and low-variance, so extra futures buy little estimator quality while candidates remain the thing
that buys wins. The code was reverted.

**Use 200 seeds for a win-rate claim.** Villain HP is 29 and the scorer averages 20.0 with sd 5.2,
so a win is roughly a 1.7-sigma event and win counts swing hard between small blocks. Two 60-seed
blocks disagreed about the same change, 20-to-30 on one and 15-to-13 on the other, purely from
that. Mean damage has far lower variance and moves consistently; treat it as the primary signal
and win rate as the headline.

Note the standard deviation falling as the policies improve, 5.19 to 4.90 to 4.41. The better
policies are not only reaching further, they are reaching more reliably, which is what a search
that can recover from a bad opening should look like.

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

**The search's own settings are also at their optimum, so do not re-tune them.** Both were
checked on 40 to 60 fresh seeds:

- *Perturbation width.* `sigma` has sat at 2.0 since it was written and turns out to be right.
  Wins by sigma: 10/40 at 0.5, 14/40 at 1.0, 14/40 at 2.0, 14/40 at 4.0, 11/40 at 8.0. Broad
  plateau from 1 to 4, both extremes worse.
- *Search frequency.* The search fires once per round, at the first decision, which looks like an
  obvious limit given a round runs eight to ten decisions. Spending the same rollout budget on
  three search points per round instead of one: 19/60 wins either way, damage 24.68 against 24.95,
  paired two-sided sign p=0.487. The round-opening decision really is where the turn is decided.
  The parameter that tested this was reverted, since it bought nothing.

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
