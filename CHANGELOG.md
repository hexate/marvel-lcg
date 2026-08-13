# Changelog

This is a fork of [irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg). Entries describe
what changed in the fork, newest first. The full reasoning behind every item, including the ones
deliberately not done, lives in [`docs/proposed_changes.md`](docs/proposed_changes.md).

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
[#6](https://github.com/irefrixs/marvel-lcg/issues/6) and
[#7](https://github.com/irefrixs/marvel-lcg/issues/7). Contributions are kept on `pr/*` branches
cut from `upstream/master` so each one is a readable diff on its own.

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
