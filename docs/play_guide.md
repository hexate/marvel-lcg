# Playing the game

Prose about how to play, in the repository. N20 closed the gap for the controls and left
this half open: the itch.io thread is still the only writing about how to play, and it
lives outside the project.

**Where each claim comes from.** Three sources, marked throughout, because they do not
deserve equal trust.

* **Card data.** Computed from `data/`, reproducible with
  `tools/sim/scenario_clock.py`. Take these as fact.
* **Your record.** `statistics.json`, 50 finished games. Facts about what happened, not
  about what should happen.
* **Engine behaviour.** Read out of the code and verified by running it. Fact, and
  several of these are not obvious from the rulebook.

Anything that is an opinion is marked as one. Two pieces of strategy advice given
earlier in this work were later withdrawn as wrong, so the distinction is load bearing.

## The two clocks

Every scenario is a race between damage you must deal and threat you can absorb. Both
numbers are printed on the cards, and knowing them before you shuffle changes how you
play more than any tactic does.

| Scenario | Villain HP | Threat runway | Accel | Villain SCH | Minion HP in deck |
| --- | --- | --- | --- | --- | --- |
| Rhino | 29 | **7** | 1 | 1 | 17 |
| Klaw | 30 | 14 | 1 | 2 | **37** |
| Ultron | 39 | 18 | 1 | 1 | 12 |
| Risky Business | 32 | 14 | 1 | 2 | 25 |
| Taskmaster | 29 | 11 | 1 | 1 | **10** |
| Crossbones | 26 | 12 | 1 | 1 | 36 |
| Zola | 26 | 13 | 1 | 2 | **40** |
| Red Skull | 28 | 18 | 1 | 2 | 37 |
| Venom | 35 | 8 | 1 | 1 | 15 |
| Juggernaut | 39 | **6** | 1 | 1 | 18 |
| Unus | 27 | 11 | 1 | 1 | 23 |
| Enchantress | 31 | 12 | 1 | 2 | **52** |
| Nebula | 31 | 10 | **0** | 1 | 18 |

Solo, per player. Runway is the total threat across every main scheme stage, so it is
how much you can absorb before you lose. Acceleration is added every villain phase
whatever you do. The villain's SCH is added on top, but only in rounds you end in
alter-ego.

Three things fall out of that table.

**Rhino and Juggernaut have almost no runway.** Seven and six. At one acceleration a
round that is gone in six or seven rounds with no help from the villain, and a round
spent in alter-ego costs two or three of it. This is why "duck into alter-ego to heal"
is a much worse habit against Rhino than against Red Skull, who gives you 18.

**Nebula has no acceleration at all.** Her main scheme only gains threat when she
schemes, meaning when you end a round in alter-ego. Stay in hero form and the scheme
clock is close to stopped.

**Minion hit points are the hidden cost.** Klaw's deck holds 37 hit points of minions
against Klaw's own 30. Enchantress holds 52 against 31. Every point you spend killing a
minion is a point not spent on the villain, so in those scenarios the damage you need is
much larger than the villain's printed health.

## Your record says which fights to pick

From `statistics.json`, 50 finished games, 5 won.

| | beaten |
| --- | --- |
| Villain stage 1 | 22 of 50 (44%) |
| Later stages | 4 of 27 (15%) |

Per villain, the pattern is stark. Klaw: stage 1 beaten 7 times in 15, stage 2 **zero
times in 7**. Rhino: 6 in 11, then 2 in 6, and that is where most of your wins are.

Cross that against the table above. Klaw is the fight you have played most and it has
the second-worst minion burden in the list. Rhino has 17 minion hit points and is where
you actually win. **Opinion, but a well-supported one: play Rhino, Taskmaster and Ultron
while you are working on this, and leave Klaw, Zola, Crossbones and Enchantress until
the damage is reliable.** Taskmaster in particular has the lowest minion burden in the
game at 10, and hands you four allies from set-aside.

Your other totals, per game: 32.5 damage dealt, 7.8 threat removed, 3.6 minions engaged,
28.2 cards drawn. The damage-to-threat ratio of 4.2 to 1 is not itself a fault. What it
means is that with 3.6 minions a game at roughly 3 hit points each, about 11 of that
32.5 never reaches the villain, which is most of the gap between 32.5 and the 30 Klaw
needs.

## Four things the engine does that the rulebook will not tell you

All four verified by running the code, and each changes a decision.

**Cards ready at the end of the player phase, before the villain phase**
(`Faces.ReadyAll` in `game/player/element/player_phase.py:93`). So when you defend during
the villain phase you are still exhausted on your next turn, and you lose that
activation entirely. Defending is not free and it is not cheap: it costs your next
attack. Defend with an ally where you can, and when you defend with the hero, know what
you are paying. The exception is a hero who can ready himself, which is why Captain
America can defend every attack and most heroes cannot.

**End Phase is a real discard and redraw.** `MayDiscardHandCardsAndDrawUpToMax` lets you
discard any number of cards and draw back up to hand size, every single turn. If you are
holding cards you cannot use, that is the way out, and it is easy to click past.

**Guard means the villain is unreachable.** A minion with Guard has to die before you
can attack past it, so it is not a minion you can choose to ignore.

**Boost cards mean the printed ATK is never the real number.** Every villain attack and
scheme draws a facedown boost card, each icon is +1, and star icons fire extra effects.
Before you end your turn, the number that matters is villain ATK plus about one, plus
every engaged minion's attack. That is the arithmetic that decides whether you can
afford to be in hero form.

## A procedure for the end of your turn

Opinion, assembled from the above rather than from experience.

1. Count what is coming. Villain ATK plus one for boost, plus each engaged minion.
2. If that number kills you, you need a blocker or you need to be in alter-ego. Decide
   which before you spend your last resources.
3. If you are going to alter-ego, add the villain's SCH to the threat you will take, and
   check it against your remaining runway from the table. Against Rhino you will often
   find you cannot afford it.
4. Cycle the hand you cannot use.

## What the search bot found, on your decks

Everything in this section is measured on the decks in `deck/custom/`, named per number. An
earlier version of it was measured on starter decks by mistake and reached different conclusions,
which is written up in J43 and summarised at the end here, because two of those conclusions were
wrong in ways worth knowing about.

The experiment: a rollout search that plays the position out before deciding, against the same
weighted scorer without search, on the same 20 seeds.

### Captain America, stun lock deck, against Rhino

| arm | wins | mean damage | rounds |
| --- | --- | --- | --- |
| scorer alone | 1/20 | 20.1 | 5.2 |
| with search | 6/20 | 25.4 | 5.5 |

Better damage on 18 of the 20 seeds and worse on 1, sign test p<0.0001, mean gain +5.3 against
the 29 needed to kill Rhino.

So searching the position is worth about five damage a game on this deck, and that converts one
win in five into six. This is the strongest and most reproducible result here: the same
comparison on the starter Captain America deck gave +5.7, so the size of the effect survives a
complete change of deck even though other things did not.

### Ant-Man, Multiple Man Protection deck, against Rhino

| arm | wins | mean damage | rounds |
| --- | --- | --- | --- |
| scorer alone | 0/20 | 16.7 | 5.5 |
| with search | 1/20 | 15.3 | 6.2 |

**Search makes this deck worse.** Damage down on 13 of 20 seeds and up on 6, mean gain -1.4.

That is the most interesting number in the whole investigation, because it is the opposite of
everything else. The reason looks like the search's bias: it attacks more (+0.17 per round) and
thwarts more (+0.11) on a deck built to defend. A Protection deck wins by surviving and grinding,
and a searcher that keeps finding reasons to attack is optimising the wrong quantity. The scorer
it perturbs has no feature that understands "this deck wants to trade time for safety", so no
amount of searching over its weights finds that plan.

**This is a heuristic problem, not a deck problem.** The deck is a built, community-style list and
it reaches 16.7 damage under the plain scorer, better than the starter deck manages. What fails is
the policy's model of what the deck is for.

### What this changes about the advice

**Attacking more still holds.** Up in both decks, +0.12 and +0.17 per round, and the winning arm
attacks more in every configuration tested.

**Defending less does not hold, and I withdraw it.** On the real Captain America deck the search
defends 0.24 times per round against the scorer's 0.25, which is no difference at all. The large
gap that produced that advice, 0.19 down to 0.07, was measured on the starter deck. A starter deck
defends because it has nothing better to do with the card; a built deck's defends are chosen. Do
not cut defending on the strength of this guide.

**Thwarting has no stable direction.** Down 0.10 per round on Captain America, up 0.11 on Ant-Man.
It depends on the deck.

### How much better decisions are worth

On Captain America, about five damage a game, and that is enough to convert narrow losses: the
seeds the search won were the seeds the plain scorer already scored highest on (measured on the
starter deck run, 5 of the top 7, hypergeometric p=0.022).

The useful diagnostic when you lose is still how close you got rather than whether you misplayed.
But the Ant-Man result adds a condition: better decisions are worth five damage *when the policy
understands the deck*. On a deck whose plan the policy does not model, searching harder makes it
worse, not better. If your deck wins by defending and grinding, a bot tuned to maximise damage is
not measuring your deck.

### What this does not cover

Two decks, one villain, 20 seeds each. `deck/custom/` is gitignored player data, so none of these
numbers can be reproduced from a clean clone. The searching bot also has a known defect (J42) where
its no-op control does not exactly reproduce the plain scorer, which does not affect the
comparisons since the searching arms beat that control too, but means the simulator is not clean.

### What the starter-deck version of this section got wrong

Worth recording, because the failure was silent. The harness resolves a bare hero name to
`deck/starter/` and never says so (J43), so a whole sweep ran on starter decks while applying
weights tuned for the custom decks. Two conclusions did not survive the correction: that defending
less is general advice, and that Ant-Man losing to Rhino is a deck-building problem. The second was
exactly backwards.


## What I got wrong

Twice, and both are worth knowing because they were stated confidently.

I said you needed to clear roughly 20 threat a game against Klaw and were clearing 7.8.
That counted threat placed and ignored that the scheme's own capacity absorbs most of it
before you lose. The real figure is nearer 4 to 10, and your 7.8 is inside it. Thwarting
is not your main leak.

I then said Ant-Man had a structural ceiling because a bot could not win with him. He is
rated one of the strongest heroes in the game. That was a fact about the bot.

Which is the caveat for this whole document. The simulator in `tools/sim` reached about
5% against Rhino, against your 10%, so nothing here is advice from a system that plays
better than you do. The card maths, your own record and the engine behaviour are solid.
The judgements built on them are mine.
