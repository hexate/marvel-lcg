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

One known gap remains from that pass. Nobody has yet seen the ribbon drawn over a real card during
an actual villain attack, which needs a game played far enough to get one, and the check above
deliberately stops short of that.

### The rotated case, closed 2026-08-18

The other gap was that a scheme renders rotated, so both ribbons sat correctly on the card's own
edges and read sideways. That is fixed for a quarter turn, in CSS only, in `image-preview.css`.

An encounter side scheme is a landscape card stored portrait: `card.css` gives it
`--rotate-times: 1`, `HoverCard.show` copies that onto the preview from the card's `.face`, and
`.image-preview` turns 90deg. Both ribbons are `::after` on the element that turns, so they turned
with it. It is the only type in either selector the game ever rotates, but the rule keys on
`--rotate-times` through a style query rather than on the type, because `HoverCard.rotate` (q, e, r,
middle click) can put any card in that state, and because a style query that an engine does not
support is ignored rather than misapplied, which degrades to exactly today's behaviour.

Two things had to be worked out rather than guessed.

**Which edge.** CSS rotation is clockwise, so at 90deg the card's local right edge lands at the
bottom of the screen and its local top edge lands at the right. ENTERS PLAY moves to the local right
edge to stay visually at the bottom, BOOST moves to the local left edge to stay visually at the top.
Anchoring each to `top: 0; bottom: 0` and leaving the other axis `auto` makes the band span the
card's full visual width at exactly one line thick, with no measurement, so `body.hold-alt`'s larger
preview needs nothing.

**How to keep the text upright.** Counter-rotating the band by -90deg would turn its box back too,
and the box has to stay along the card's edge. Laying the text out vertically instead leaves the box
where it is: `writing-mode: vertical-rl` plus `rotate: 180deg` puts the glyphs 90deg anticlockwise
running upward, and the card's own 90deg brings that back to upright and left to right. That pair is
what `sideways-lr` means in one keyword, which is much newer and not worth the support risk. The
180deg also rotates the box shadow, which is why the two offsets are written the opposite sign from
the side they land on.

Verified in Chrome twice. First in a standalone page reproducing the rotation, which is where the
shadow direction was settled by exaggerating both to 20px in a solid colour and seeing which side of
the band they fell on. Then against the running server on `marvel.html`: the CSSOM holds the
container rule with both selectors intact, and forcing the centre preview to
`type-encounter-side-scheme` with `--rotate-times: 1` draws ENTERS PLAY horizontally along the visual
bottom edge and, with `boost-flip` added, BOOST horizontally along the visual top. The unrotated case
was re-checked in the same session because the base rules moved from `padding: .15rem 0` to
`padding-block: .15rem` so the padding follows the writing mode: still `horizontal-tb`, still the
bottom band, still 2.4px block padding and 0 inline. No change.

One limit remains, and it is deliberate. Only a quarter turn is handled; at two or three the card is
upside down or on its other side, which needs the same work again and only happens if a player
rotates the centre preview by hand.

### The boost icons, closed 2026-08-19

The row of lifted icons was the other half of this and is now done. It was written up as inferred
from reading, and the reading was right: ✓ VERIFIED before the change as three icons 165px apart
down the screen and 0px apart across it, each one on its side.

`.image-preview-boost` is a real element rather than a pseudo, but it is a child of the card and so
it turned with it. The same pair fixes it, doing two jobs instead of one. `writing-mode: vertical-rl`
turns the flex container's inline axis vertical, so `flex-direction: row` lays the icons out along
the axis the card's own turn maps to the screen's horizontal, and the `180deg` both brings each icon
upright and reverses the run so it reads left to right. `justify-content` and `align-items` needed no
change, because they follow the axes rather than the screen. The 5vh clearance moves with the ribbon
it exists to clear: the base keeps it off the top because BOOST sits there, and under a quarter turn
BOOST is on the card's left edge, so the clearance is too. The base `padding: 0 2vh` becomes
`padding-inline`, for the same reason the ribbons' padding did.

✓ VERIFIED in Chrome on the rotated card at three, five, six and ten icons, and unrotated at three,
five and six. Rotated, the row runs across the screen left to right, five fit on one line where the
portrait card wraps at four, and the wrap still stacks rows down the screen. Every icon stays inside
the card box in all seven cases, which is what the wrap exists to guarantee. The unrotated case is
unchanged.

Worth knowing for the next person measuring this preview: `#image-preview-div-center` runs a
`rotateY(90deg)` to `rotateY(0)` flip, and in a background tab it sits at 90deg, edge on. Every
descendant then reports a zero-width rect and a single shared position, which looks exactly like a
broken layout and is not. Set `animation: none` on the div before reading any geometry.

## Decision log

| Date | Change |
| --- | --- |
| 2026-08-19 | Closed the boost icon row, the last of N2's rotation gaps. Everything the centre preview draws over a rotated card now reads upright. What is left on N2 is the option list, not the rotation: 2 as a floating value, 4, 5, 6, 7, and the `pause_when_reveal_or_boost` prompt-text check. |
| 2026-08-18 | Closed the rotated-scheme half of N2's known gaps. Both ribbons stay on the card's visual bottom and top edges and read upright at a quarter turn, keyed on `--rotate-times` rather than the card type. The boost icon row is still untreated and is now the open half. |
| 2026-08-18 | Upstream answered the three open issues. Nothing in them touches N1 or N2 directly, but the "upstream-shaped?" column can stop being a live question: he conceded the technical point on two of them and confirmed the third as a real bug, and acted on none. The honest default for this document is now no, without the case-by-case caveat. Reasoning in section 0 of [proposed_changes.md](proposed_changes.md). |
| 2026-08-16 | Recorded the three N2 commits that landed on 2026-08-13 but were never written up, and moved N2 to IN PROGRESS. Added IN PROGRESS to the legend, since a feature with seven options was always going to need it. |
| 2026-08-13 | Created, alongside `stable` becoming the fork's trunk. Seeded with N1, which is not a new idea but the deferred half of F6c: that row was closed as a decision not to fail closed, on the explicit grounds that the real fix is a feature, so it belongs here rather than sitting as a permanently open defect. |
