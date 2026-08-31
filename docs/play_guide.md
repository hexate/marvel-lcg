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

## What the search bot found, and what it costs to believe it

This section is the only part of the guide with a controlled experiment behind it rather than
reading and inference. A rollout search that plays the position out before deciding wins 7 of 20
Rhino games as Captain America. The same scorer without search wins 0 of 20, and loses to the
searching version on 19 of the 20 shared seeds (sign test p=0.00002). So the two differ in ways
worth reading, because one of them wins.

They differ in three things and only three.

**It attacks more.** 2.07 attacks per round against 1.83. Across all 100 games in the sweep, the
winners averaged 2.08 attacks per round and the losers 1.86. This is the same conclusion the
earlier record analysis reached from your statistics, arrived at independently.

**It almost never defends.** 0.07 defends per round against 0.19, a two thirds cut. The split on
outcomes is sharper than any other number here:

| | games | wins |
| --- | --- | --- |
| never defended | 46 | 16 (35%) |
| defended at least once | 54 | 5 (9%) |

Fisher one-sided p=0.0018. Every one of the seven games the search won had zero defends in it.

**It thwarts exactly as much.** 0.53 per round against 0.56, which is noise. In this matchup
thwarting is not the lever, which is also what your play record said. That part turned out not to
generalise, see below.

So the shape is: the extra attacks come out of the defends, not out of the thwarts, and the
searching bot survives *longer* while defending less (6.0 rounds against 5.2) and ends with more
health, not less (0.11 of maximum against 0.08). It buys survival by flipping to alter-ego more
often (0.18 against 0.15 per round) rather than by defending. Defending spends a card and an
action to stop one attack. Flipping down spends a turn and recovers repeatedly.

### The honest caveat

Defending is partly a symptom. You defend when an attack would otherwise kill you, so a game where
you defend is disproportionately a game that was already going badly, and some of that 35% against
9% is the losing position causing the defend rather than the defend causing the loss.

Two things stop that from explaining it away. The comparison is paired: both arms played the same
20 seeds from the same deck, so the searching version met the same situations and chose to defend
less in them. And it came out of those situations with more health rather than less, which is not
what you would see if it were simply skipping a defence it needed.

Treat it as a strong prior, not a rule: if you are reaching for a defence, check first whether
flipping to alter-ego next turn does more for you than blocking one attack does now.

### Which of it generalises, tested on three more matchups

Repeated on Rhino/Spider-Man, Klaw/Doctor Strange and Taskmaster/Ant-Man, 20 shared seeds each,
this time on the untuned default weights.

**Search still helps, every time.** Paired damage against the same scorer without search:
Spider-Man better on 16 of 20 and worse on 1 (sign p=0.0001), Doctor Strange better on 9 worse on
2 (p=0.033), Ant-Man better on 12 worse on 4 (p=0.038). Mean damage roughly doubled in two of the
three.

**But it won nothing.** 0 wins in all six arms. The reason looks like the starting point rather
than the search: those runs used untuned weights and reached 1.9 to 6.5 damage of the 29 needed,
so doubling a bad number is still a loss. The Captain America run that produced the wins started
from a hill-climbed weight set already averaging 20.15. Read that as search amplifying a decent
policy rather than rescuing a poor one, and note that it means the win result rests on tuning and
search together, not search alone.

**Defending less is the part that holds.** Down in all four matchups tested, without exception.

**Attacking more mostly holds.** Up in three of the four, flat in Klaw/Doctor Strange.

**Thwarting the same does not hold.** In all three new matchups search thwarted *more*, by +0.23,
+0.07 and +0.04 per round. The flat thwart rate in the Captain America games was specific to that
matchup, and the sentence above has been corrected accordingly. Those three are also positions
where the bot is far more pressed, defending 0.75 to 0.95 times per round against Captain
America's 0.19, so it is a different regime and the thwarting is probably survival rather than
preference.

### Tested on a second tuned hero, and it did not reproduce

The generalisation run above left one thing open: it used untuned weights, so its zero wins could
have been the starting point rather than the search. The repo already had two hill-climbed Ant-Man
weight sets against Rhino, so that is a direct test of tuning and search together on a second hero.

It does not reproduce. 0 wins of 20 in all four arms.

| weights | arm | wins | mean damage | rounds | end health |
| --- | --- | --- | --- | --- | --- |
| basic | greedy | 0/20 | 14.6 | 4.7 | dead |
| basic | search | 0/20 | 14.8 | 4.6 | dead |
| protection | greedy | 0/20 | 13.2 | 5.3 | dead |
| protection | search | 0/20 | 14.4 | 5.5 | dead |

Search barely moved the basic set (paired sign p=0.23, no effect) and moved the Protection set a
little (13.2 to 14.4, p=0.025). Every one of the 40 games ended with the hero eliminated.

**The reason is survival, not decisions.** Captain America's tuned scorer was already averaging
20.15 damage of the 29 needed and living 5.2 rounds, so it was losing narrowly and search pushed a
third of those over the line. Ant-Man averages 14.6 and dies at round 4.6. Search cannot
manufacture a win from a position that is dead before the damage lands, and this is the same 15 of
29 ceiling that the earlier tuning work kept hitting from the other direction.

So the honest scope of the win result is one hero. What generalises is that search reliably
improves damage, and that it converts near misses into wins. What does not is the idea that it
rescues a losing matchup. If Ant-Man against Rhino feels unwinnable to you, this is evidence that
it is a deck and matchup problem rather than a matter of playing the turns better.

Also worth noting for the advice above: search defended less here too, 0.57 per round against
0.73, which is now five matchups out of five.

### How much better decisions are actually worth

The Captain America and Ant-Man results look contradictory until you put a number on what search
buys. It is worth about six damage a game: mean +5.7, median +6.0, sd 3.7, over the 20 paired
Rhino seeds.

That single number predicts both outcomes. Sorting the Captain America seeds by how close the
plain scorer already got to the 29 damage needed:

| plain scorer reached | seeds | search converted |
| --- | --- | --- |
| under 15 | 1 | 0 (0%) |
| 15 to 19 | 8 | 1 (12%) |
| 20 to 24 | 8 | 4 (50%) |
| 25 or more | 3 | 2 (67%) |

The prediction was made before looking: if closeness is what matters, the games search converts
should be the games the plain scorer already scored highest on. It won 5 of the plain scorer's top
7 seeds, hypergeometric one-sided p=0.022, and the seeds it converted averaged 22.4 against 18.9
for the ones it did not.

The between-hero result falls out of the same number. Tuned Captain America averages 20.1, which
is 8.9 short of the line, so a six-damage improvement converts some of the spread and it wins a
third of the time. Tuned Ant-Man averages 14.6, which is 14.4 short, so six damage converts
nothing and it wins none. There is no contradiction, just one gap that six damage can close and
one it cannot.

**What this means for your own play.** Playing the turns better is worth roughly six damage a
game, and that is a real amount, enough to flip a third of narrow losses. It is not enough to
rescue a game you are losing by fourteen. So the useful diagnostic when you lose is not "did I
misplay" but "how close did I get". If you are finishing consistently within about six of killing
the villain, better decisions will start converting those, and the first thing to change is the
defending. If you are finishing far short, no amount of turn-by-turn improvement gets there and
the deck or the matchup is what needs to change.

### What this does not cover

Four matchups, 20 seeds each, all starter decks. The searching bot also has a known defect (J42)
where its no-op control does not exactly reproduce the plain scorer. That does not affect the
comparisons above, since the searching arms beat that control as decisively as they beat the plain
scorer, but it means the simulator is not yet clean.

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
