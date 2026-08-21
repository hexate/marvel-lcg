# Changelog

Continuing [irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg), originally developed by
the Irefrixs Team and sunset on 2026-08-10. Entries describe what changed here, newest first. The
full reasoning behind every item, including the ones deliberately not done, lives in
[`docs/proposed_changes.md`](docs/proposed_changes.md).

## 2026-08-19 to 08-21

The project became its own trunk, and the look and feel got a pass end to end. 68 commits.

### The project itself

- The default branch is `main` and it is the work, not the mirror. It was `master`, the pinned copy
  of upstream, so the front page of the repository showed unmodified upstream code and none of the
  changes. That was reasonable while this was a queue of patches for someone else. It is not now.
  `master` stays pinned, because the `compare/master...pr/x` links in the upstream issues read
  against it.
- The docs say what this is rather than what it forked from. The README leads with the project,
  upstream gets a short section saying read it and do not send to it, and the reasoning for that
  sits in [`docs/upstream_rationale.md`](docs/upstream_rationale.md).
- `./build.sh` builds both halves from a clean clone. There are two, a Python virtualenv and a
  TypeScript compile, and neither was scripted end to end. The compiled `.js` is gitignored, so a
  fresh clone rendered nothing until someone worked out the second step from a stale message in
  `play.sh` telling them to install TypeScript globally. TypeScript is a pinned devDependency now
  rather than whatever a global install happens to give you that month, which is what broke the
  build on 2026-08-10 when that became TypeScript 7.
- There is no `LICENSE` file, here or upstream, so the default is all rights reserved. The original
  maintainer said in writing that community builds are welcome, but a comment on an issue is not a
  grant with terms. Tracked as U11.

### The board reads as a table

- The board has a surface. It was one flat `radial-gradient(#333, #111)` and read as an empty dark
  rectangle. It is cool charcoal felt now, lit slightly above centre where the cards are, with a
  fine grain over it. The seat tint that marks the current player was an opaque band with a hard
  line across the board; it is feathered and translucent, so it tints the surface instead of holding
  a second copy of it.
- The rows have play zones, so the width the new layout won reads as space rather than emptiness,
  and the two sides can be told apart.
- Cards keep their shadow when you hover them. The lift scaled the art and left the shadow on a box
  that did not move, so a hovered card grew out of its own shadow.
- The player's half has room. Allies, supports, hero and hand were 19, 14 and 4 units apart, and the
  last of those is about three real pixels.
- The three status cards are drawn from the card data instead of upscaled. The art for Stunned,
  Confused and Tough is 149x95, against 715x1035 for every real card, so blown up to the centre
  preview it was a 6 to 7x upscale.
- Typography is two deliberate stacks instead of three accidents. Bare `monospace` was the app-wide
  default, `'Segoe UI', Tahoma, Geneva, Verdana` sat on seven card overlays and falls through to
  Verdana off Windows, and a `Circular` that does not exist anywhere quietly did nothing. The
  reading face is proportional now, with fixed pitch kept for debug output, and counters get
  `tabular-nums` so digits stop jittering as they count.
- The menu and setup pages are styled rather than shipping browser defaults, and they are on the
  same font as the board.
- The chrome outside the board scales with the window, in the board's own terms.

### Chrome that belongs to the same program

- The prompt box floats over the board instead of cutting a hole in it. It is pinned to a percentage
  of the viewport while the board is in scene units, so any position is a guess about a layout it
  cannot see; a translucent fill with a blur behind it makes the overlap stop mattering.
- A hovered button no longer erases its own label. Hover threw the button's colour away for a light
  grey with the white label left on top: 12.63:1 at rest and 1.84:1 while you point at it.
- The game log is readable. It was black text on a `#333` panel, and the panel's `opacity: .85` faded
  the text along with the fill, so it reached the eye at 1.53:1 against a 4.5:1 floor. It also broke
  ordinary words mid-character, wrapping like "the villa / in attacks".
- Hovering a card name in the log or the prompt no longer makes it unreadable. That hover filled the
  name with `silver` under white text, 1.82:1.
- The right-click menu and the extra button panel match the rest. One was a white box with square
  corners on a dark felt board, the other a flat mid grey that was the brightest thing on screen.
- Scrollbars have a shape. What was there was a web snippet with its `border-radius` lines dropped,
  so nothing had a fill and the thumb was a soft dark smudge on a soft grey smudge. Firefox had the
  stock scrollbar throughout, and the setup screen, deck editor and card viewer never loaded the
  stylesheet at all.
- The range sliders are drawn rather than left as a white track with a blue thumb.
- Keyboard focus is visible on the buttons, the menu and the sliders. There was no focus style at
  all, and the extra button panel actively removed the one it would have inherited.

### Motion

- Cards ease into place instead of moving at a constant speed and stopping dead. Every draw, play,
  discard and row change ran on `linear`.
- The new layout had silently deleted the card scale transition. A `transition: box-shadow` shorthand
  replaced the property list it was added to rather than joining it, so a hovered or activating card
  jumped to size with no transition at all.
- Hover states arrive the way they leave. The card lift and the side bar drawers both cancelled their
  transition on `:hover`, so they snapped in and eased out.
- `prefers-reduced-motion` is honoured. The `?disable_animations` escape hatch had never worked: it
  asked for a stylesheet path that does not exist, so it 404'd silently and only ever disabled the
  card tilt.

### Playing the game

- A boost card is visibly different from a card entering play. The two have opposite consequences,
  one being a permanent threat and the other a number that has already been applied, and they
  animated and landed the same way. The number a boost adds now has a colour, a boost that does more
  than add a number is marked, and a boost no longer lands where a revealed card lands.
- An effect whose size comes from a quantity you choose no longer lets you choose zero, get nothing
  and be told nothing. X costs are shown while you pay them, and Shield Toss's targets are bound to
  its discard.
- A facedown encounter card dealt to you gets its own place. It was landing in the shared hero row
  among your cards in play, so it read as something entering play, which it is not.
- The setup screen lists the decks you have. Choosing a hero was four file inputs and you had to
  already know that decks live in `./deck/starter`.
- Landscape-printed cards are the right way up in the setup screen, the deck editor and the card
  viewer. Every card image the server sends is portrait, including the 76 of 914 that are printed
  landscape, so something has to turn them back and only the board did.

### Fixed

- The "3D Render" setting does something. Its stylesheet path had a `public/` segment missing and a
  dot where a slash belongs, twice, so a 3KB stylesheet had never once been applied.
- The main scheme's threat readout no longer clips at two digits either side.
- The side-scheme type is no longer missing, and the set grids and a dictionary race are fixed with
  it.

### Investigations that changed nothing, and why

- I6 proposed skipping a CRC during replay. Measuring made it look worth doing at 9% of runtime, and
  then the premise collapsed: the CRC is not a render artifact despite living next to one. Withdrawn
  as unsafe.
- G5 asked for a game played to completion in the browser, on the belief that a mid-game replay
  cannot drive the test harness. Six of the seven replays already on disk drive it to a clean pass.
  Dissolved rather than done.
- F8 said cross-area targeting isolation is opt-in, and H5 sized fixing it as the largest hidden cost
  in the document. Isolation is enforced one level up from where the row was looking. Re-scoped and
  retracted.
- F12 records that whether an encounter set is "standard" or modular is decided entirely by whether
  its name starts with "standard" or "expert", re-derived independently in four places. Found while
  explaining what the Standard Sets box does, not from anything failing.

## 2026-08-16 to 08-18

A new board layout, a rebuilt setup and game over screen, and the tooling to exercise them. 13
commits.

### The board, rebuilt as v2

- The board is laid out by CSS instead of a JavaScript transform, and it is the default. v1 draws
  on a fixed 1920x1080 canvas and scales it uniformly, so any window that is not 16:9 pays for the
  difference in empty bars: 1285px of board in a 1512px viewport, about 15% of the screen wasted.
  v2 keeps the same coordinate system, because the animation and hit-testing code speaks it, but
  expresses one scene unit as a fraction of the container. Height still governs card size, so cards
  are exactly the size they are in v1 at the same window height, and the width that is left over
  goes to the board. Add `v1` to the board URL for the original; the corner control flips between
  them and keeps the game and the seat.
- Nothing measures the viewport any more, so there is no measured scale to go stale. One did during
  the layout audit, which is what made the board look broken.
- Three rounds of coordinate bugs came out of this, and all three are worth knowing if the CSS is
  touched again. Pseudo-elements carry their own copies of the coordinates and a rule on `.deck`
  does not reach `.deck::after`. An id beats any number of classes, so v1's four-class nudges for
  activating and selected cards were being overridden into nothing rather than converted. And some
  rules write scene coordinates as literal pixels, which no search for `* 1px` will ever find; that
  one put the hand at 905 real pixels on hover, below the bottom of the window, so moving between
  cards made it jitter.

### Setup and game over

- An encounter set can be read before it is chosen. The info badge opens the set as a grid of cards
  you can roll over at a readable size, and rolling over anything else previews just that card.
- The game over screen cannot outgrow the window. It was sized by its content and capped by
  `max-height`, which conflict, and CSS resolves `min-height` last, so the cap lost: the panel grew
  past the viewport, the flex container centred the overflow, and the corner controls went with it.
  The chart toggle rendered above the top edge and Save replay below the fold.

### Fixed

- Code is no longer cached for a year. Card art still is, because it never changes, but HTML, CSS,
  JavaScript and JSON are served with `max-age=0` so a reload during development actually reloads.
- `/get_version` is served `no-store`. It is how the client decides whether its cached assets are
  stale, so caching it made it authoritative about its own staleness (J18).
- `/get_card_json` answers instead of returning 500 on every call.
- Text is served with its charset stated rather than left to the browser to guess.
- The port probe no longer refuses ports the server can go on to bind (J14).
- Decks in `deck/custom/` are visible to the game.

### Tooling

- The version bump commits only `build.py`, and both git calls have their exit codes checked. It
  ran `git add build.py` and then a bare `git commit`, which takes everything already staged, so
  bumping with unrelated work in the index swept that work into the `Package version` commit.
  Failures went through `os.system` unread, so a rejected commit left `build.py` rewritten and
  reported success, and the next run incremented from the new number and skipped a version. The
  current version is now read from the file rather than the imported class, which a stale
  `__pycache__` entry could report one version behind.
- Running the unit tests no longer packages anything. `unit_test/test_task.py` asserted nothing: it
  bumped the version, made a git commit and wrote a zip into the repository root, and being named
  `test_*` meant plain `unittest discover` did all three. Both chores are `tools/package.py` now,
  which takes an explicit subcommand, so `unittest discover` is safe to run.
- `tools/autoplay.js` plays a game in the browser, for exercising the client without doing it by
  hand. It reads the board rather than following a script, so it copes with different heroes,
  villains and aspects, and it reports where cards land relative to the viewport, which is how the
  v2 layout got checked against real games.
- The client publishes the current ask on `window.__ask`. A turn is one ask holding every legal
  option at once, and each option names the card that provides it, but none of those names reach
  the DOM: the client highlights the bound cards and the player chooses by clicking one. Anything
  driving the client from outside was guessing without this.

---

## 2026-08-10, stabilization

No new features. This pass fixes defects, closes one security hole, and puts tests and CI around
what was already here. 34 commits, 21 tracker items closed.

### Two changed defaults

Read these before upgrading. Everything else in this release is invisible if the code was working
for you.

**The game no longer uses numpy at runtime.** The bundled pure-Python generator now reproduces
numpy's sequence exactly, so `disable_numpy_random` defaults to `true` and numpy is a test
dependency rather than a runtime one. Games deal identically: verified across 450,000 raw words,
5,400 shuffles at sizes from 2 to 1025, interleaved operation streams, decks of card objects, and
real opening hands from the engine. Existing saves are unaffected, and new ones record
`rng: "mt19937-v2"`.

**`/debug` now requires a local request or a configured password.** That endpoint passes its query
string to `exec`, and the wrapper in front of it admitted everyone whenever no password was set,
which is the shipped default. Nothing changes for a normal single-player session on `127.0.0.1`.
If you were driving `/debug` from another machine, set `password` in your config.

### Fixed

Build and platform:

- The client could not be built at all with TypeScript 7, which is what `npm install -g typescript`
  installs today. `moduleResolution` is removed, and the config now type checks clean on 5 and 7.
- Four places compared paths against Windows separators, so on macOS and Linux they silently never
  matched: card-script coverage counted nothing, the downloaded-save safety break in front of
  `exec` never fired, `FormatPath` raised `IndexError` on short paths and prefixed `./` onto
  absolute paths, and `.gitignore` missed the `save.json` the debug save command writes.

Engine correctness:

- Clicking Cancel on the End Phase prompt crashed the game. The rule behind it was right and is
  kept, but a client that breaks it is now refused and asked again instead of raising.
- `Random.Undo` silently did nothing on the bundled backend, so the `Unshuffle` debug command
  quietly stopped working whenever that backend was selected.
- `-no_someflag` on the command line was accepted and then ignored for any variable already
  declared, which is most of them.
- `Json` offered a `"Restrict"` checksum mode that behaved exactly like `"Warn"`. A mismatch now
  refuses to load. Files that carry no checksum at all are unaffected, since they are old rather
  than damaged.
- The game refuses to start under `python -O`. About 620 `assert` statements carry the rules of
  the game, and `-O` deletes every one, producing a build that walks past illegal plays rather
  than stopping.

Security:

- `/authenticate` issued a session cookie without checking the password. It was not a bypass, since
  the check happened later, but every attempt got a `200` and a malformed body got a `500`. It now
  verifies, answers `401` or `400`, and compares in constant time.
- Serving on a non-loopback address with no password configured now logs a warning naming the
  address.

### Infrastructure

- CI runs the suite and type checks the client on every push and pull request.
- `tools/run_tests.py` runs everything self-contained, on a clean clone, with one command. It skips
  `unit_test/test_task.py`, which is not a test: it bumps the version, makes a git commit and
  writes a zip into the repository root.
- `tools/rng_parity_check.py` measures any MT19937 implementation against numpy operation by
  operation.
- Dependencies are bounded at the next major of each package, so a new release cannot break an
  install that touched no code.
- An empty replay corpus now explains itself instead of failing on `assert world` forty lines later.

### Verified

76 tests across 16 modules, plus the replay suite, the RNG parity harness, and the client type
check on TypeScript 5 and 7. Green locally and in CI on Ubuntu. Also run against a clean clone with
no `assets/`, no `launch-debug.json` and no recorded games, and the application boots on its default
port and serves.

Not verified: nobody has played a full game through the browser against this build, the roughly
3,450 card scripts are exercised by a single 32-input replay, and only Python 3.13 was tested even
though the install guide claims 3.10 and 3.14 work.

### Known and deliberate

`IsAuthenticate` still admits everyone when no password is configured, on every route other than
`/debug`. Failing closed would break four-player play for everyone who never set one, so the fix is
an auto-generated password on a non-loopback bind, which is a feature and is deferred. The exposure
is now griefing and privacy on a network you chose to expose, rather than code execution. Tracked
as F6c.

### Reported upstream

Issues [#4](https://github.com/irefrixs/marvel-lcg/issues/4),
[#5](https://github.com/irefrixs/marvel-lcg/issues/5),
[#6](https://github.com/irefrixs/marvel-lcg/issues/6),
[#7](https://github.com/irefrixs/marvel-lcg/issues/7) and
[#8](https://github.com/irefrixs/marvel-lcg/issues/8). Contributions are kept on `pr/*` branches
cut from `upstream/master` so each one is a readable diff on its own.

All five are answered as of 2026-08-18, and none is being fixed upstream. The project is sunset.
He confirmed #8 as a real bug and supplied the function that was deleted by mistake, agreed on #7
that the command blocklist is not a security boundary, and explained that both of the `test_task.py`
chores in #6 are intentional developer tools. The fixes live here.

### Branches

`main` is the trunk and the default branch: the stabilized game, and what you actually run. New work
is cut from it as `feat/<topic>`. Proposed features are tracked in
[docs/proposed_features.md](docs/proposed_features.md), the same way defects are tracked in
[docs/proposed_changes.md](docs/proposed_changes.md).

It was called `stable` until 2026-08-19, and the default branch was `master`, which meant the
repository's front page showed unmodified upstream code and none of the work. Both are fixed.

`master` is a deliberate mirror of `upstream/master` and is never committed to. It stays pinned so
that every `compare/master...pr/x` link posted in an upstream issue keeps showing what it showed
when it was written.

`work/engine-audit` is retired at `aababf0`. It is the stabilization line that became the trunk, kept
only as history.
