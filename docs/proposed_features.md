# Proposed features

New features and improvements for the fork. This is the counterpart to
[proposed_changes.md](proposed_changes.md): that document is an audit of code that already exists
and the defects in it, this one is for things that do not exist yet.

Everything here lands on `main`, which is the trunk of the project rather than of a fork. Nothing
here is written for upstream: that channel closed on 2026-08-10 and the reasoning is in section 0 of
[proposed_changes.md](proposed_changes.md).

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

There used to be a third question here, whether a feature was upstream-shaped, and a column in the
table to record the answer. Both are gone as of 2026-08-19. Upstream takes nothing, so the answer
was "no" on every row that will ever be added, and a column whose value is known in advance only
costs attention. The rows that carried a real answer are in the history.

## Features

| ID | Feature | Rationale | Size | Status |
| --- | --- | --- | --- | --- |
| N1 | **Auto-generate a password when binding to a non-loopback address.** `IsAuthenticate` returns `True` for every caller when no password is configured, which is the shipped default, so every `*Security` route is open to anyone who can reach the port | Carried over from F6c, which was closed as "not failing closed" precisely because the real fix is a feature. Failing closed would break four-player play for everyone who never set a password, so the exposure was accepted rather than fixed. Generating one on a non-loopback bind and printing it at startup closes the hole without breaking the default local case | ? | PROPOSED |
| N2 | **Make a boost card visibly different from a card entering play.** When the villain attacks or schemes it flips encounter cards for their boost icons. Those cards add to the attack or scheme and are discarded immediately, but they currently animate and land like a card being revealed into play | Found from play: "it looks as if it's being drawn to place on the board". Not a cosmetic nitpick, the two events have opposite consequences. One is a permanent threat you now have to deal with, the other is a number that has already been applied and is gone. Reading the board wrongly costs you real decisions | Small for the first slice | IN PROGRESS, first slice landed 2026-08-13, see the work log below |

| N3 | **Status card art is 149x95.** `stunned.webp`, `confused.webp` and `tough.webp` in `assets/textures/` are 149x95 and about 4kb each, against 715x1035 for every real card in `assets/cache/`. They are found by `Cache.FindImageFile`, which searches the texture folder for `.webp`, so these are in use rather than missing | Blown up to the centre preview they are a 6 to 7x upscale. Status cards are landscape and render rotated, so the preview is roughly 509x367 CSS pixels, about 1018x734 on a 2x display. Q raised this first and it is the worst-looking thing on the board | Small if the art can be sourced, none of it is code | **SUPERSEDED by N9.** Q chose to draw them rather than source art, so the 149x95 files stay where they are and v1 keeps using them |
| N4 | **The board is one flat radial gradient.** `layout.css:57` is the whole surface: `radial-gradient(#333, #111)` | It reads as an empty dark rectangle rather than a table. v2 already owns this line, so it is the cheapest visual change available and the one with the widest effect | Small | **DONE** 2026-08-19, in two slices. The first was not the gradient at all: the hard line across the board was `.player-background`, `top: 40%` with a flat fill marking the current seat, and it is feathered now. The second is `public/css/marvel2/board.css`, loaded only by `marvel2.html`. Cool charcoal felt, lit slightly above centre where the cards are, falling off to a much darker corner, with a fine grain over it. The delicate part was a coupling rather than the colour. `.player-background` spans the bottom 60% of the scene at full width and was opaque, so the base was only ever visible in the top 40% and the two halves agreed only because both ended on the same `#111`. Changing the base alone would have put the seam straight back along the left and right edges. The seat tint is translucent now and ends at `transparent`, so it tints whatever the base is instead of holding a second copy of it, and the palette can change again without reopening anything. The grain is an SVG `feTurbulence` tile, no asset and nothing to go blurry at any board size, and its blend operator was measured on a canvas rather than picked: `overlay` lifts the mean 6 levels and re-tints the palette above it, `screen` washes the board out at +43, `soft-light` drifts a correctable `opacity * 14`. 0.35 gives about 18 levels peak to peak. Also moved the two surface rules out of `layout.css`, which promises in its header to be geometry. ⚠ The grain does not survive a full-board screenshot, because that path is JPEG over a downsampled 2x display. It is there under magnification, and that is how to check it if it ever needs re-tuning |
| N5 | **The player's half is vertically cramped.** Allies, supports, hero and hand are one column at `--y` 410, 605, 795 and 975. A card is 176 tall, so the gaps are 19, 14 and 4 units. The last is about 3 real pixels | Q asked for space between the hero row and the hand specifically, which is the 4. v2 already sets these coordinates and already deviates from v1 deliberately (`--x: 1773` against v1's 1880), so re-spacing is in bounds rather than a fork of the layout | Small, but see the trap below | **DONE** 2026-08-19. Board rows to an even 14 and 29 before the hand, by moving minions to 200, allies to 390, supports to 580 and the hero to 770. The hand and the 905 hover literal are deliberately untouched, so what you can see of your hand at rest is unchanged. Modest by construction: six rows of 176 is 1056 of 1080, so there was slack to move and none to hand out |
| N6 | ~~**Cards have no depth.**~~ **Wrong premise, corrected 2026-08-19.** They do: `card-face.css` gives a card in play `4px 8px 8px / .38`, a card in a pile `1px 4px 9px / .33` and a hovered card `8px 16px 16px / .25`, all transitioned. The real defect is which box carries it. Hover scales `.face .image` by 1.15 and leaves `.card` and `.face` at their original size, so a hovered card grows out of its own shadow: measured on an engaged minion, the art reaches 111.8x155 while the face stays 97.2x134.8, and the shadow is drawn 14.6px inside the visible edge | Depth is most of what separates a modern card game from a web page with pictures on it. A lift whose shadow stays behind reads as the card flattening instead | Small | **DONE** 2026-08-19. `public/css/marvel2/cards.css`, loaded only by `marvel2.html`. The shadow moves to `.face .image`, which is the box that scales and the one carrying the rounded corners, so it traces the silhouette at any size; nothing clips it, since there is no `overflow` on the card chain. Two values changed while the shapes are kept: offsets in `--su` rather than pixels so they track the card as the board rescales, and a hovered card no longer fades from .38 to .25, which on a dark board is close to invisible. It also gains about 15% for free, because a shadow on a scaled element scales with it |
| N7 | **Typography is three unrelated stacks.** 12 rules use bare `monospace`, 7 use `'Segoe UI', Tahoma, Geneva, Verdana`, one uses `Circular, -apple-system, ...` and one uses `"Inter"`, none of which ships | Bare `monospace` is whatever the browser picks, which is Courier on some machines and is most of why the chrome looks dated. One stack and one scale would change the feel more than any single colour | Small to medium | **DONE** 2026-08-19. `public/css/marvel2/type.css`, loaded only by `marvel2.html`. Two tokens, `--font-mono` and `--font-ui`, and monospace deliberately stays the default: the board leans on it and the turn banner's `---` rules only line up in it. What changed is that it stops being the browser's guess. Lighter than it looked, because `marvel.css` sets `monospace` on `body`, so that is the app-wide default and most of the twelve are restating it. Heavier than that in one respect, found by measuring: restating still beats inheritance, so setting `body` alone moved `body` and the side bar and left `.card` and the previews on bare `monospace`. Every explicit declaration is restated too, including the three in `image-preview.css`, which is shared with v1 and so is overridden rather than edited. `marvel-icons` and FontAwesome verified untouched |
| N8 | **The chrome is unstyled next to the board.** Side bar, history, prompts and buttons are flat fills with hard edges. `--font-size-out` only started scaling with the window on 2026-08-19 (J25), so this was never worth doing before | Now that it scales, the chrome is the largest remaining surface that does not match the board | Medium | **DONE** 2026-08-19, and "unstyled" was too strong again. Buttons already carry a radius, a shadow, a press state and a semantic `--color` each. The side bars are not broken either: they are deliberate drawers, parked off screen at `right: calc(-1 * var(--width) + 4px)` with a 4px peek tab and a slide transition. What was actually wrong is legibility. `.button:hover` threw the button's colour away for `--color2`, `rgb(191,191,191)`, with the label still white: 12.63:1 at rest and **1.84:1 hovered**, against a 3:1 floor. The action buttons escaped only because `btn-ok.css:99` has the same swap commented out. Hover now derives from each button's own `--color`, lightened 4%, with the border carrying the rest of the signal. 4% was measured, not guessed: swept 12/10/8/6/4 across all eight button colours, and `darkgoldenrod` is the only one that fails, at 2.76 by 12%, because it starts at 3.25. Also softened the pure white borders to a quarter strength and added the `:focus-visible` ring that did not exist. ⚠ The resting appearance, the rule cascade and the contrast maths are verified; the live hover appearance is **not**, because the driven pointer state does not survive between tool calls and `.button` transitions `all`, so computed reads mid-transition are ambiguous |
| N9 | **Status cards as markup instead of a bitmap.** The alternative to N3 rather than a companion to it: draw Stunned, Confused and Tough in the DOM from the card data, the way `.image-preview-boost` already draws boost icons | Crisp at every size with no asset to source, themeable, and it sidesteps the question of where higher-resolution official art would come from. Costs a rendering path the other cards do not use | Medium | **DONE** 2026-08-19, Q's choice over N3. `public/css/marvel2/status-cards.css`, loaded only by `marvel2.html`. Cost almost nothing in the end: `Lib.game.addTypeClass` has always appended the card name for a `StatusCard`, so `type-status-card-stunned` and friends already existed on board cards, and only `HoverCard.show` was dropping the name when it classed the preview. One argument fixed that. The face is a radial gradient per status with the word over it, sized in `vh` so it tracks the preview, and it takes the same `vertical-rl` plus `180deg` the ribbons use so the word stays upright through the card's quarter turn. Scope: the centre and side previews only. The board card keeps the texture, which is adequate at 97x135 and is where v1 and v2 still agree |

| N11 | **The start and setup pages ship browser defaults.** The two screens you meet before the game looked like neither the game nor each other. `scene.html` was almost entirely unstyled native widgets on a dark background: light grey system buttons, a system select, system file inputs, and hairline `fieldset` rectangles with the label notched into the top edge. `main.html` had the opposite problem, a copy-pasted button pack with a fixed 130x40 box, an inset white bevel, and a hover that emptied the fill and drew 2px lines round the edge instead | Q, from use: "all the buttons are ugly and square". These are the first thing anyone sees, and the board they open has had three passes of work while these had none | Small | **DONE** 2026-08-19. `public/css/menu/controls.css`, shared by both pages, restating the board's button language from N7 and N8 rather than inventing a third one: solid fill on a per-button `--color`, white bold label, 1px border at quarter-strength white, hover lightening the fill 4% with the border carrying most of the signal, `scale(.96)` on press, `:focus-visible` ring. Sized by padding now, so labels stop being clipped or swimming, and each page marks its one real action primary. Page background is the v2 felt, fixed so the vignette does not scroll through a setup page several screens tall. Two fixes beyond the brief: prose links were `rgb(0, 0, 238)` underlined, near unreadable on dark and worse visited, replaced at a checked 5.4:1 and 5.2:1; and `Join as player 2..4` are genuinely disabled, which was invisible when all four rendered as identical blue link text. ⚠ One regression found and fixed in passing, worth knowing because the obvious check misses it. `font-family: inherit` on a file input truncates it: form controls do not inherit fonts unless asked, so these had been in the browser's narrow default where "No file chosen" measures 77px and fits a 100px hero slot, against 112px in the page's monospace. `scrollWidth > clientWidth` never fires on a file input, because the ellipsis happens inside its shadow DOM, so it reports no overflow however badly the label is clipped. `measureText` against the content box is what detects it. Follow-up 2026-08-19, both of the deferred items done at Q's request. Checkboxes are drawn rather than native: they were bright white squares, the loudest thing on the page, and `accent-color` could never fix that because it only colours the checked state. `appearance: none` with a `clip-path` tick, no asset. The five panels keep their colour coding, because it is how you tell which group you are in, but the hue moved off a lit 1px outline onto one edge and the heading, with a near-neutral fill and a border matching the fieldsets. ⚠ That created a legibility regression caught on measurement: the headings became 12.8px, which wants 4.5:1 rather than 3:1, and three of five failed as raw accents against the rgb(34,37,46) panel fill (crimson 4.27, blue-grey 3.62, magenta 3.34). Each is now mixed toward white by the smallest step that clears, keeping as much hue as possible: 4.94, 4.64, 4.75. Green and amber already passed. Hence two tokens per panel, `--accent` for the edge and `--accent-text` for the heading. ⚠ Also worth knowing: `getComputedStyle().color` returns `color-mix()` results as `oklab()`, so parsing digits out of it yields nonsense rather than an error. Rasterise to a canvas and read the pixel instead. ⚠ The radio rules are written and symmetric with the checkbox ones but are **unverified**, because this page renders zero radios in any reachable state |
| N10 | **An ability whose size comes from a cost lets you choose the two independently, and silently keeps the smaller.** Shield Toss (`03006`) is "Discard X cards from your hand, then return Captain America's Shield → deal 4 damage to X enemies". The script takes X from the discard and deals damage to `effect.targets[:discard_num]`, so selecting three enemies and discarding none resolves to nothing at all, with no indication why | Reported from play: three minions selected, three resources paid, the confirm button read "overpay", it resolved and every enemy was untouched. The rules are right, the flow is not. Three separate things mislead. The card costs 0, so the resource prompt is irrelevant but is the most prominent step, and "overpay" reads like buying more effect. The discard range starts at 0, so doing nothing is a valid answer to the step that actually matters. And target selection is not bounded by, or reconciled with, the discard | Small for a warning, medium for binding the two | PROPOSED |

Nothing else is tracked yet. This document was created on 2026-08-13, when `stable` became the
fork's trunk.

## The look and feel plan, 2026-08-19

Asked for by Q: v2 is functional but plain. Ordered by what changes the most per unit of work, not
by how interesting it is. Everything here is v2 only and none of it touches the coordinate system
that J19 to J26 were about, with the single exception noted under N5.

### First, because it is cheap and nothing else depends on it

**N3, the status card art.** This one is worth restating because the cause is not what it looks
like. The art is not being generated and it is not missing: `assets/textures/stunned.webp` and its
two siblings exist, are found, and are simply 149x95. Every other card on the board is 715x1035.
Replacing three files fixes it with no code at all, and nothing else in this plan is that cheap.
The open question is where higher-resolution art comes from, which is why N9 exists as the way out
if the answer is nowhere.

**N4, the board surface.** One line, `layout.css:57`. Worth doing early because every other visual
change is judged against whatever is behind it, so changing it later re-opens decisions. A flat
gradient reads as absence; almost anything with structure reads as a table. `assets/textures/`
already ships a `sets` folder and a `mask.svg`, so there may be usable material there before
anything new has to be made.

**N5, the vertical rhythm.** The numbers are `#player-all-allies` 410, `#player-all-supports` 605,
`#player-all-area-hero` 795, `#player-all-hand-cards` 975, all in `layout.css`. The hand
deliberately overflows the bottom by 71 and rises on hover, so it is not simply a matter of moving
everything down.

**The trap in N5, and it is a real one.** `layout.css:327` raises the hand to `calc(905 * var(--su))`
on hover, a literal that mirrors `card-hand.css:16`. It is 70 units above the hand's resting 975.
Move the hand row without moving that number and the hover either stops lifting or lurches, which
is exactly the bug that was fixed on 2026-08-16. Any change to the hand's `--y` has to move the 905
by the same amount.

### Then, because they compound

**N6, depth.** Card shadow, a hover lift, and a stronger shadow on whatever is active. This is
where the board stops looking flat. It pairs with N4: a shadow needs a surface to fall on.

**N7, typography.** Pick one stack and one scale. The board is already full of numbers that need to
be read at a glance, so this is legibility as much as style.

**N8, the chrome.** Left until after N4, N6 and N7 because it should be styled to match the board
rather than the board to match it.

### Deliberately not proposed

The v1 layout. It is the reference the fork is measured against and the thing to fall back to when
v2 misbehaves, which it did five times this week. Restyling both doubles the work and removes the
control.

The card faces themselves. They are the printed cards and should stay that way.

A theme system. Worth having once there are two themes worth switching between, and premature
before that.

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

### Closing out the options, 2026-08-19

Two of the five open items dissolved on inspection rather than needing building, which is the
pattern this whole feature has followed.

**The `pause_when_reveal_or_boost` prompt check is answered, and the answer is no.** The two
messages already read differently: `AfterCardsMovedToRevealingArea_Text` says "moved to revealing
area" and `AfterCardsMovedToBoostingArea_Text` says "moved to boosting area"
(`sender_card.py:382` and `:630`). So there was nothing to gain there. Neither carries the boost's
value, which is the thing a player actually needs, and that is options 2 and 6.

**Option 6 was already built.** It was written up as "the most informative and the most work,
because the intermediate value has to be surfaced rather than just the final one". The work was
done: `gain_att` calls `GainForThisActive(..., attack=boost_value, render_ui=True)`
(`can_attack.py:279-288`), `attack` is in the rendered info dict, and the client diffs the
descriptor between renders and floats the delta through `.change-value`. The villain's ATK really
does go 2, then 3, with a `+1` rising off the card. The value is the resolved one, not the printed
one: `can_boost.py:71-75` passes 0 when cancelled and `CountBoostIconsInternal()` otherwise, after
amplify has been applied, so the earlier worry that "a number here could be a lie" does not apply.

What was missing was that nobody gave it a colour. ✓ VERIFIED by resolving every delta type in the
browser: health green or red, threat yellow, trait bisque, boost red, and `attack`, `scheme`,
`thwart` and `defense` all `rgb(167, 167, 167)`, the inherited grey. The one number saying how much
harder the villain just hit drifted past in the same grey as everything else. Both boostable stats
now take the encounter orange, the same one the BOOST ribbon uses, so the ribbon and the number it
caused read as one event. `attack` and `scheme` are exactly the two `ResolveBoostCards` feeds.

**Option 2 is closed as superseded.** It wanted the value floated on the boost card itself. The
resolved value now floats on the target, which is where the consequence lands and where the player
is already looking during an attack. Putting the same number in two places is noise.

**Option 4 is done, and my reason for parking it was wrong.** It was written up here as needing the
client to know a boost carries a star ability, "which is not in the descriptor today". True and
irrelevant: it is in the card's own text. 375 cards carry the marker, in exactly one spelling,
`[star] <b>Boost</b>:`, ✓ VERIFIED by scanning every text in `cards.json` and finding no other form.
`cleanResText` leaves it alone, because it only substitutes the four resource icons and `boost`. So
the client already held the answer and only had to look, and no engine change was needed.

`CenterPreview.hasStarBoost` reads the marker and toggles a `boost-star` class. Two things follow
from it. The ribbon becomes "★ BOOST", using the game's own marker rather than new vocabulary: the
star in the ribbon is the same star the card prints in front of its ability, so the two read as one
thing. And the grey-out lifts from `grayscale(.9) brightness(.55)` to `grayscale(.3) brightness(.9)`,
because the entire reason this card is different is that its text matters and the pause is when you
read it. ✓ VERIFIED against Weapons Runner: "★ Boost: Put Weapons Runner into play engaged with
you" is legible in the preview, next to a ribbon carrying the same star.

**Option 7 is done, but not as written, and the deviation is the finding.** It asked for the
boosting area to get its own container. That is not available. ✓ VERIFIED by measuring the centre
column on a real board: there is no free 176-unit band anywhere in it. `area-play` already overlaps
engaged minions by 26 units and allies by 136, and only coexists with them because it sits at
`--x: 50` while they are centred. The two candidate gaps, left of the minion spread and right of it
before the scheme column, both move with the board state, so a fixed container in either would
trade a transient ambiguity for a permanent collision. That is what "it touches layout" was warning
about.

What option 7 actually wanted is that a boost never lands where a reveal lands, and that needs an
offset, not a container. `area_boost` and `area_revealing` are already separate lists in the world
descriptor and `cards.ts` merges both into `area-play`, which is the whole source of the ambiguity.
The descriptor now carries `is_boost_area` through to an `in-boost-area` class, and both layouts
push such a card just over half a card height down: `.area .card.in-boost-area` in `pos-area.css`
for v1, `#scene .area .card.in-boost-area` in `layout.css` for v2, since v2 does not load
`pos-area.css`. ✓ VERIFIED in both: 96.8px against a 176 card in v1, 74.1px against a 134.8 card in
v2, both 0.55, and the card stays on the board.

**Still open:** option 5 alone, and only because it needs a sound asset that does not exist and
cannot be written. Every other option is closed.

N2 is otherwise finished. What began as "a boost card and a revealed card look the same" now differs
in five ways: the animation, the ribbon, the grey-out, the position, and the orange value that lands
on the target, with a star boost marked apart again from a plain one.

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
| 2026-08-19 | Added N10 from a play report: Shield Toss resolved to nothing. Not an engine defect, the rules are implemented correctly, and worth writing down so it is not re-investigated as one. `03006` takes X from the discard cost and damages `targets[:X]`, so three targets and no discard is three targets and no damage. It is unusual in the card pool: every other `CostFunc.Discard`-driven ability uses a fixed count, so nothing else exposes the gap between a player-chosen cost and a player-chosen target list. There is no engine idiom for binding one to the other, which is why the fix needs a decision rather than a patch. |
| 2026-08-19 | Repainted the status faces from the real card colours. The web turned up only custom 3D-print tokens, but the game already ships the actual card art at `assets/textures/*.webp`, so the palette is sampled from that: filtering to chromatic pixels and taking the dominant hue gives lime at ~70deg, purple at ~280 and orange at ~20. Two of my three first guesses were wrong, amber and steel instead of lime and orange. The ink stopped being white as a result, since two of the cards are light. The lesson worth keeping is the second one: contrast has to be measured against the darkest part of a gradient, not the centre. Measuring only the centre put the last line of each paragraph on a dark edge where it dimmed, so each card's edge value is now the darkest that still clears 4.5:1 against its own ink. |
| 2026-08-19 | Corrected both of the previous day's follow-ups after Q played it further. The status rule is the Rules Reference text verbatim now rather than my paraphrase, sourced from marvelcdb.com/rules and cross-checked; the printed status cards carry only a name and an icon and no rules text at all, so the Rules Reference is the canonical wording and there is nothing shorter that is still official. It is a paragraph, so the name drops to the top 30% and the rule takes the rest. And monospace is no longer the default: the first pass kept it on the theory that the board leaned on it deliberately, and playing it said otherwise. Fixed pitch is now kept only for the debug surfaces, where columns line up, and digit alignment is handled by `font-variant-numeric: tabular-nums` on the proportional face, which is the only part a monospace font was actually being used for. |
| 2026-08-19 | Two follow-ups from Q playing it. The status faces carry the rule as well as the name now; it could not come from the data, since all three statuses have `text: null` in `cards.json`, which is also why the old generated placeholder had nothing to draw, so the wording is written in the stylesheet from what the engine does. And the prompt box moves to the proportional stack: keeping monospace as the default was right for the board, but the running commentary in the centre of the screen reads as prose, not as console output. The status faces went proportional with it, being a designed card face rather than a readout. |
| 2026-08-19 | Fixed the prompt box overlapping the minion row, and corrected the misidentification above. It is not a v2 defect: `#prompt-box-container` is `top: 32%` of the body in both layouts, and v1 collides worse, 31px against 23px, because its minion row sits lower. Moving it is not available, since the board rows run 8 to 881 with 11px gaps and a 35px box lands on something wherever it goes. The prompt is pinned to the viewport and the board to scene units, so any percentage is a guess about a layout it cannot see. What made it read as damage was the solid black fill amputating whatever it covered, so it is a translucent blurred panel in v2 now and the cards stay legible through it. New home for this and the rest of N8: `public/css/marvel2/chrome.css`, linked last so it can override v1 chrome without a specificity war, which the first attempt lost by loading before `prompt.css`. |
| 2026-08-19 | Started the plan. N5 and N9 done, N4's first slice done, N3 superseded by Q choosing to draw the status cards rather than source art. Two things worth carrying forward. A board that looks empty is probably not broken: a client that joins mid-game and idles never gets the render messages that assign `--x`/`--y`, so every card falls to the origin, and v1 does the same. `MoveCard.resetAreaXY` per area lays it out locally without touching the game. And the turn banner does overlap the minion row, though not by the element named here at the time. **Corrected 2026-08-19:** `#message-overlay` was a misreading. It is parked off screen at `translateX(-100%)` and overlaps nothing; the survey that fingered it printed each element's `top` and `height` and never its horizontal position. The real one is `#prompt-box-container`, `top: 32%` of the body against a board measured in scene units, and it is fixed now. |
| 2026-08-19 | Added N3 to N9 and the look and feel plan, at Q's request. Grounded rather than brainstormed: the status card complaint turned out to have a specific and cheap cause, 149x95 source art where every other card is 715x1035, and the cramped feel Q described measures as a 4 unit gap between the hero row and the hand against a 176 unit card. Nothing in the plan touches the scene coordinate system, apart from N5 moving area `--y` values, which is what those variables are for. |
| 2026-08-19 | Closed the boost icon row, the last of N2's rotation gaps. Everything the centre preview draws over a rotated card now reads upright. What is left on N2 is the option list, not the rotation: 2 as a floating value, 4, 5, 6, 7, and the `pause_when_reveal_or_boost` prompt-text check. |
| 2026-08-18 | Closed the rotated-scheme half of N2's known gaps. Both ribbons stay on the card's visual bottom and top edges and read upright at a quarter turn, keyed on `--rotate-times` rather than the card type. The boost icon row is still untreated and is now the open half. |
| 2026-08-18 | Upstream answered the three open issues. Nothing in them touches N1 or N2 directly, but the "upstream-shaped?" column can stop being a live question: he conceded the technical point on two of them and confirmed the third as a real bug, and acted on none. The honest default for this document is now no, without the case-by-case caveat. Reasoning in section 0 of [proposed_changes.md](proposed_changes.md). |
| 2026-08-16 | Recorded the three N2 commits that landed on 2026-08-13 but were never written up, and moved N2 to IN PROGRESS. Added IN PROGRESS to the legend, since a feature with seven options was always going to need it. |
| 2026-08-13 | Created, alongside `stable` becoming the fork's trunk. Seeded with N1, which is not a new idea but the deferred half of F6c: that row was closed as a decision not to fail closed, on the explicit grounds that the real fix is a feature, so it belongs here rather than sitting as a permanently open defect. |
