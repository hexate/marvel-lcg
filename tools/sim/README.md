# Headless play simulator

Plays complete games with no UI, so a strategy question can be answered by running a
few hundred games instead of arguing about it. Built on `unit_test/harness.py`, which
supplies an `InputDevice` that answers prompts from a Python callable.

A game takes roughly half a second.

## Files

| File | What it does |
| --- | --- |
| `policy.py` | The heuristic player. Reads world state, scores the legal options, picks one. |
| `run_game.py` | Plays exactly one game and prints a JSON result line. One game per process. |
| `batch.py` | Runs many games in parallel from a config file and summarises them. |
| `scenario_clock.py` | No simulation. Prints each scenario's damage and threat budget from card data. |

## Running

```sh
.venv/bin/python tools/sim/run_game.py <scenario> <deck> <seed> <mode>
.venv/bin/python tools/sim/run_game.py rhino captain_america_stun_lock 205 balanced

python3 tools/sim/batch.py <config.json>
.venv/bin/python tools/sim/scenario_clock.py rhino klaw taskmaster
```

`<scenario>` is any file in `data/scenarios/`. `<deck>` is any file in `deck/starter/`
or `deck/custom/`.

Batch config:

```json
{"scenarios": ["rhino"], "heroes": ["captain_america_stun_lock"],
 "modes": ["balanced"], "seeds": [11, 23, 37], "out": "myrun", "workers": 8}
```

It writes `<out>.json` (summary) and `<out>.raw.json` (per game, including telemetry)
next to the scripts.

## Modes

`balanced` keeps the main scheme low, builds a board and clears minions.
`aggro` hits the villain and thwarts only at the brink; it exists as a control, so a
gap between the two is about the strategy rather than about engineering effort.
`brawl` keeps the hero ready to swing and spends allies as blockers instead.

`g<NN>` / `t<NN>` are `balanced` with a preferred Ant-Man form (Giant / Tiny) and a hero
defence threshold of NN% health. `w<NN>` is for scenarios won by clearing threat rather
than by damage. Suffix `+a` lets allies chump-block; `+nc` disables end-of-turn cycling.

## Things that cost a day each, written down so they cost nobody else one

* **Cards ready at the END of the player phase** (`Faces.ReadyAll` in
  `game/player/element/player_phase.py:93`), before the villain phase. A hero who
  defends is therefore still exhausted on its next turn and loses that activation
  entirely. A policy that defends every attack never attacks at all.
* **`End Phase` is the discard-and-redraw step**
  (`MayDiscardHandCardsAndDrawUpToMax`). Declining it leaves a dead hand dead for the
  rest of the game. This was worth roughly +80% card plays once answered.
* **Multi-form heroes do not use `Change_Form`.** Ant-Man offers
  `Change_To_AVENGER_GIANT`, `Change_To_AVENGER_TINY`, `Change_To_Scott_Lang`. Matching
  only on `Change_Form` leaves him in alter-ego for the whole game.
* **Turn options are named by ACTION, not by card** (`Attack`, `Play`, `Thwart`). The
  card is identified by `bind_id`, which is `face.card.object_id`.
* **A `Play` option's legal target is usually the player**, not the card's ability
  target; damage cards are aimed at a later prompt.
* **`GameOverReason.players_won` is only a type annotation** until the game ends in a
  win or loss. Read it with `getattr`, or an exit-ended game raises.
* **`Engine.SaveCrash` hard-codes `./crash.json`** and calls `exit(-1)`. `run_game.py`
  neuters it so a batch run does not clobber a real crash repro.
* **Statistics are off under `-test`** (the group expands to include `-no_statistics`),
  so simulated games never touch `statistics.json`.
* Some scenarios are won by clearing threat, not by damage: Batroc resets when he would
  be defeated, and MaGog is decided on ratings counters.
