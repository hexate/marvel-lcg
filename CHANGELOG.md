# Changelog

This is a fork of [irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg). Entries describe
what changed in the fork, newest first. The full reasoning behind every item, including the ones
deliberately not done, lives in [`docs/proposed_changes.md`](docs/proposed_changes.md).

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

`master` is a deliberate mirror of `upstream/master` and is never committed to. It stays pinned so
that every `compare/master...pr/x` link posted in an upstream issue keeps showing what it showed
when it was written.

`stable` is the fork's trunk: the stabilized game, and what you actually run. New work is cut from
it as `feat/<topic>`. Proposed features are tracked in
[docs/proposed_features.md](docs/proposed_features.md), the same way defects are tracked in
[docs/proposed_changes.md](docs/proposed_changes.md).

`work/engine-audit` is retired at `aababf0`. It is the stabilization line that became `stable`, kept
only as history.
