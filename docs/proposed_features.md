# Proposed features

New features and improvements for the fork. This is the counterpart to
[proposed_changes.md](proposed_changes.md): that document is an audit of code that already exists
and the defects in it, this one is for things that do not exist yet.

Everything here lives on `stable` and is assumed fork-only. See the branch layout section of
[proposed_changes.md](proposed_changes.md) for why, and for how to cut a contribution if one of
these ever turns out to be upstream-shaped.

## How to use this

IDs are `N1`, `N2`, and so on, allocated in the order they are written down rather than by priority.
`A` through `J` and `U` are already taken by the other tracker, so `N` is the free prefix. An ID is
never reused or renumbered, because commits and issues refer to it.

Status vocabulary matches the other document:

| Status | Meaning |
| --- | --- |
| PROPOSED | Written down, not yet decided. The default. |
| DECIDED | A call has been made, including a call not to do it. Say what was decided and why. |
| IN PROGRESS | Being worked on. For a feature with several slices, say which have landed. |
| **DONE** | Implemented, with the commit. |

Two things worth writing down at proposal time, because both are cheap now and expensive later.

What breaks if this is wrong. A feature that touches save files, the RNG, or the card scripting API
can invalidate recorded games, and the replay corpus is what the test suite is built on. Anything in
that category needs a migration story before it is DECIDED, not after.

Whether it is upstream-shaped. Upstream declared sunset on 2026-08-10 and takes urgent bugfixes case
by case, so the honest default is no. A feature only qualifies if it is small, self-contained, and
repairs something rather than adding to it. Recording the answer here stops the question being
relitigated every time the branch comes up.

## Features

| ID | Feature | Rationale | Size | Upstream? | Status |
| --- | --- | --- | --- | --- | --- |
| N1 | **Auto-generate a password when binding to a non-loopback address.** `IsAuthenticate` returns `True` for every caller when no password is configured, which is the shipped default, so every `*Security` route is open to anyone who can reach the port | Carried over from F6c, which was closed as "not failing closed" precisely because the real fix is a feature. Failing closed would break four-player play for everyone who never set a password, so the exposure was accepted rather than fixed. Generating one on a non-loopback bind and printing it at startup closes the hole without breaking the default local case | ? | Arguably yes, it repairs something | PROPOSED |
| N2 | **Make a boost card visibly different from a card entering play.** When the villain attacks or schemes it flips encounter cards for their boost icons. Those cards add to the attack or scheme and are discarded immediately, but they currently animate and land like a card being revealed into play | Found from play: "it looks as if it's being drawn to place on the board". Not a cosmetic nitpick, the two events have opposite consequences. One is a permanent threat you now have to deal with, the other is a number that has already been applied and is gone. Reading the board wrongly costs you real decisions | Small for the first slice | Probably not, it is an addition rather than a repair | IN PROGRESS, first slice landed 2026-08-13, see the work log below |

Nothing else is tracked yet. This document was created on 2026-08-13, when `stable` became the
fork's trunk.

## N2: a boost card and a revealed card look the same

The cause is specific rather than a general lack of polish. In `public/js/marvel/card_animation.ts`
the two events are mapped to the same animation:

```ts
"AfterCardsMovedToRevealingArea_Text"   : "center_flip",
"AfterCardsMovedToBoostingArea_Text"    : "center_flip",
```

and `public/js/marvel/cards.ts:545` pushes the `area_boost` descriptors into
`print_cards_objs['area-play']`, so a boost card is rendered into the play-area container as well.
The two things a player is trying to tell apart are identical in both motion and position.

Nothing needs inventing on the server. `world.area_boosting` is already its own area,
`AfterCardsMovedToBoostingArea_Text` is already its own message, and
`WhenCardWouldGainBoostIcons_Text` already has its own animation slot, `target2_boost`. The
information is all present and the client is throwing it away.

Options, cheapest first. The first two are the slice worth doing before judging the rest.

1. **Split the animation.** Give the boosting-area message its own entry instead of sharing
   `center_flip`, and move the card toward the villain or scheme it is feeding rather than to centre
   stage. One map entry and one keyframe.
2. **Float the value.** `change-value.css` already renders `data-value` through `::after` with a
   rise-and-fade. Firing it on boost resolution puts a `+2` on the card without building a new
   mechanism.
3. **Draw it as spent, not played.** Desaturate or dim the card while it is in the boosting area, so
   its appearance contradicts its position instead of reinforcing it.
4. **Distinguish a star boost.** Some boosts do more than add a number: Tiger Shark's gives the
   villain a tough status, Weapons Runner's puts itself into play engaged with you. Those outlive
   the flip and deserve different treatment from a card contributing only icons.
5. **A distinct sound.** The presentation layer already carries a sound name per message. Needs an
   asset.
6. **Accumulate the total on the target.** Villain ATK visibly going 2, 2+1, 3. The most informative
   and the most work, because the intermediate value has to be surfaced rather than just the final
   one.
7. **Give the boosting area its own container.** Fixes the position problem at its root rather than
   compensating with motion and colour, but it touches layout, so it is the last resort rather than
   the first move.

Worth checking before building anything: `pause_when_reveal_or_boost` already ships on by default.
If its prompt currently reads the same for both cases, naming the boost and its value there may
capture much of the benefit for almost nothing.

### What has landed

Three commits on `feat/boost-card-clarity`, all 2026-08-13. Everything below is client-side, so the
Python suite is untouched at 106 passing.

| Commit | What it did | Options |
| --- | --- | --- |
| `8d57468` | `AfterCardsMovedToBoostingArea_Text` gets its own `boost_flip` instead of sharing `center_flip`. The centre-flip test moves behind `CardAnimation.isCenterFlip()`, which `HoverCard.getPreview` also needed. The centre preview is banded BOOST along the top and outlined in encounter orange | 1, in the "label the event" form rather than the "move it toward the villain" form |
| `d4e5aab` | The boost card's art greys out, and its own boost icons are lifted onto the preview from `.info_pay`, falling back to `info['boost_const']` for a card that arrived face down | 3, and the readable half of 2 |
| `1c277bd` | Minions, encounter side schemes, attachments and environments get a steel blue outline and an ENTERS PLAY ribbon on the bottom edge. CSS only, keyed off the type classes `HoverCard.show` was already setting | None of the seven. See below |

`1c277bd` is the other half of the problem rather than one of the options as written. The options all
ask "how do we mark the boost", and answering that still leaves a revealed card that stays on the
board looking like one that resolves and is gone. It marks the permanent types rather than dimming
the temporary ones, so a treachery looks exactly as it always did and an unbanded reveal means "this
is already over".

Scope limits, all deliberate:

- It shows in the centre reveal preview only, so it rides on `pause_when_reveal_or_boost`. Turn that
  setting off and the marking goes with the pause.
- Encounter-side only. Nothing distinguishes a player event from an ally or an upgrade, because the
  centre preview never fires for a card the player is playing.
- The printed icons are shown, not the resolved total. `update_boost_icons`, `set_boost_icons` and
  `cancel_boost_icons` all exist, so a number here could be a lie. That is option 6's job.

Still open: 2 as a floating value, 4, 5, 6, 7, and the `pause_when_reveal_or_boost` prompt-text check
above.

Verified in Chrome against the running server on 2026-08-16, which closes the "not verified in a real
browser" note on `8d57468`. On `public/marvel.html` the CSSOM holds the ENTERS PLAY rule with its
full selector and all five `boost-flip` selectors, and `.image-preview-boost` is present in the DOM.
Toggling classes on the preview element and reading the computed `::after` gives the three cases that
matter: bare, `content: none` and the default grey outline, so a treachery is untouched;
`.type-minion`, `content: "ENTERS PLAY"` with `rgb(46, 134, 171)` on ribbon and outline; and
`.type-minion.boost-flip`, which flips to `content: "BOOST"` in `rgb(230, 125, 34)`. That last one is
the one worth having, because it proves the `:not(.boost-flip)` guard holds and a minion flipped for
its icons cannot wear both ribbons.

Two known gaps remain. Nobody has yet seen the ribbon drawn over a real card during an actual villain
attack, which needs a game played far enough to get one, and the check above deliberately stops short
of that. And schemes render rotated, so the ENTERS PLAY ribbon sits correctly on the card's own
bottom edge but reads sideways. Counter-rotating it is a later call.

## Decision log

| Date | Change |
| --- | --- |
| 2026-08-16 | Recorded the three N2 commits that landed on 2026-08-13 but were never written up, and moved N2 to IN PROGRESS. Added IN PROGRESS to the legend, since a feature with seven options was always going to need it. |
| 2026-08-13 | Created, alongside `stable` becoming the fork's trunk. Seeded with N1, which is not a new idea but the deferred half of F6c: that row was closed as a decision not to fail closed, on the explicit grounds that the real fix is a feature, so it belongs here rather than sitting as a permanently open defect. |
