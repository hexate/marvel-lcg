# Proposed Changes Tracker

Running log of every proposed change to this codebase and its status. Add new items to the
table; do not delete rows — move them to `Done` or `Rejected` and keep the rationale.

**Last updated:** 2026-08-24

## Status legend

| Status | Meaning |
| --- | --- |
| `PROPOSED` | Identified, not yet agreed to |
| `ACCEPTED` | Agreed, not started |
| `IN PROGRESS` | Being worked on |
| `DONE` | Implemented and verified (note *how* it was verified) |
| `REJECTED` | Decided against, keep the reason |
| `BLOCKED` | Waiting on something external |

## Evidence markers

Claims in this doc are marked so we know what has actually been checked:

- ✓ **VERIFIED**: file read and/or behavior observed at runtime
- ? **INFERRED**: from grep/search only, not confirmed by reading
- ✗ **UNVERIFIED**: asserted, not yet checked

---

## 0. Upstream status, and why nothing goes there

**Read this section as history plus a standing decision.** Everything in it was written while this
repository was a fork queuing patches for someone else. It stopped being that on 2026-08-19: the
work continues here, and upstream is a source of answers rather than a destination for changes. The
U-series below is the record of what was offered and what came back, not a live queue. Nothing in it
is waiting on anyone.

The detail is kept in full because it is the evidence for the decision, and because the answers
themselves are still worth having: the numpy history, the save format and their test method all came
out of asking, and none of it is written down anywhere else.

Checked 2026-08-18. Local `HEAD` is `2ac194a`, identical to `irefrixs/marvel-lcg@master`. No
upstream commits since 2026-08-07, ✓ VERIFIED by `git fetch upstream` on 2026-08-18.

**The maintainer is active but the project is formally sunset.** irefrixs replied to both of our
first two issues on 2026-08-10, roughly 16 hours after they went up, and to issues #6, #7 and #8
in one pass on 2026-08-18, between 03:39 and 05:23 UTC. He answers technical questions in
detail and engages with the substance. He is not taking contributions:

> Today we are treating the project as sunset – we're not accepting new feature updates or pull
> requests. (If you have an urgent bugfix that needs attention, let us know and we'll consider it
> on a case-by-case basis.)

That contradicts the issue #1 answer from 2026-08-05, *"we would be happy to accept your PR."*
The later statement wins, so the working assumption changes: **the door is one narrow exception
wide, "urgent bugfix," and we have to argue a fix through it rather than simply offering it.**
Everything queued below was written against the older, more open stance and needs re-aiming.

**Revised 2026-08-18: the exception is narrower than that, and probably closed.** The three
replies of 2026-08-18 settle what "urgent bugfix, case-by-case" means in practice. J13 is the
strongest case anyone will get: he called it *"an actual bug in the open-source version,"* named
the commit-level cause himself, and pasted the deleted function. It still came with no fix and no
plan to make one. F6/F6a got the technical point conceded, *"a whitelist would be safer than a
blacklist,"* and then scoped away on the grounds that the shipped itch.io build cannot reach the
endpoint. I8 was answered as working-as-intended twice over.

The pattern across all five issues is consistent: he engages with the substance, usually concedes
it, and then declines to act. Three separate replies now end with a variant of *"feel free to
change it in your fork."* **Treat upstream as a source of answers, not a destination for patches.**
Report a defect when the answer would change what we build, which is exactly what happened with
issue #4 and J13. Do not spend effort packaging fixes for him to take.

### Already answered upstream: do not re-ask

| Topic | Answer | Source |
| --- | --- | --- |
| License | "Considering Apache License 2.0, no final decision yet." No `LICENSE` file exists. | issue #1 |
| Community builds | Welcome, even pre-license. Credit as *"originally developed by the Irefrixs Team"* explicitly approved. | issue #3 |
| Contributions | "We have not finalized our contribution policy… we would be happy to accept your PR." | issue #1 |
| Test corpus | Cannot be shared, player-uploaded, >1 GB, kept off Git on a shared disk. | issue #1 |
| `launch-debug.json` | Developer-local file, intentionally not committed. Copy `launch.json`. | issue #1 |
| Issue etiquette | **"Split future questions into separate issues"**, an explicit request. Honor it. | issue #1 |
| Contributions (superseded) | Sunset. No new features, no PRs. Urgent bugfixes case-by-case if asked. | issue #5, 2026-08-10 |
| Why numpy is the default | Started on stdlib `random`, hit a bug in it, switched to numpy. **All existing save files carry numpy sequences.** | issue #4, 2026-08-10 |
| Why the bundled backend exists | Shipping numpy in version 1 means bundling a ~10 MB DLL, *"that's just bad."* The pure-Python path was meant to reproduce numpy's sequence, *"but that never really happened; we actually never used it."* | issue #4, 2026-08-10 |
| F1 state-capture cost | Accepted without argument: *"yes – we should release the state-capture cleanup. Thanks for flagging the performance issue."* | issue #4, 2026-08-10 |
| `cheat` retry loop (I7) | Declined. *"In our design `cheat` should never be true during normal gameplay, so we don't add any protection around that path."* Their tests use real save files and never hit it. | issue #5, 2026-08-10 |
| Why `test_task.py` is named `test_` (I8) | Intentional, both cases. `test_IncreaseVersion` *"is intentionally kept there because VS Code registers it as a test/button, which makes it convenient for us to run `IncreaseVersion` manually."* `test_zip_cards` builds the compiler bundle for the paid [Marvel LCG Scripts](https://irefrixs.itch.io/marvel-lcg-scripts) release, which is the build that runs custom card scripts. | issue #6, 2026-08-18 |
| **How their test suite actually works** | *"We run all existing save files through the game engine, and check that the CRC values in the save JSON still match."* After each file passes, `check_is_pass` in `test_run.py` **re-saves it under the new version number**, updating both the version key and the filename, and once the whole run passes they move the old saves to a different folder. They keep per-version corpora deliberately, so that a change which breaks save compatibility can be rolled back to. | issue #6, 2026-08-18 |
| `IsCommandSafe` as a boundary (F6) | Conceded, not fixed. *"Yes, I agree that `IsCommandSafe` is not a strong security boundary and that a whitelist would be safer than a blacklist."* Scoped away: the itch.io build does not allow debug or custom script execution by default, only the `-script` build runs Python, and that needs `cards_json_custom_file`/`cards_json_custom_files` set by the host at launch. *"We don't consider the current setup to be a strong security boundary for arbitrary configurations."* | issue #7, 2026-08-18 |
| Why `/save_local` has no handler (J13) | Confirmed as a real defect and explained. It lived on a `GameServerXXX(GameServerBase)` mixin that `GameServer` inherited, and existed to upload replays and bug-report saves to their private server. *"In the open-source version, we removed the server-related code because we don't want to expose or depend on our private server. Unfortunately, we removed this function along with it by mistake."* | issue #8, 2026-08-18 |

### What his RNG answer changes (F3)

His reply reframes F3 rather than confirming it. `pr/rng-backend-determinism` makes divergence
*loud* by refusing to load a scene recorded under the other backend. The direction he actually
wants is to make divergence *impossible*: numpy is the canonical sequence because every existing
save encodes it, and the pure-Python backend was always intended to reproduce numpy exactly so
version 1 could drop the 10 MB dependency. That was never built. The bundled
`engine/lib/mt19937.py` is abandoned, not an alternative, which is why nothing forces a choice
between the two backends.

He then pointed at another fork's implementation as a candidate:

> And I found that their code looks like it can generate the same sequences as NumPy does—without
> pulling in the NumPy library itself:
> <https://github.com/mggarofalo/marvel-lcg/blob/3c8743e/py_src/engine/lib/mt19937.py>

**We tested that claim. It is very nearly right, with one specific exception.** ✓ VERIFIED against
numpy 2.5.2 legacy `RandomState`, which is what `engine/lib/random.py` calls:

| Operation | Matches numpy? | Coverage |
| --- | --- | --- |
| seeding (`init_genrand`) internal state | ✓ exact, all 624 words and the position | 300 seeds |
| raw `uint32` stream | ✓ exact | 450,000 words |
| `Shuffle` vs `numpy.random.shuffle` | ✓ exact | 5,400 cases, `n` from 2 to 1025, incl. `2^k+1` rejection-heavy sizes |
| `Choice` vs `numpy.random.choice` | ✓ exact | 2,100 cases |
| 64 interleaved shuffle/choice ops off one stream | ✓ stayed in lockstep | 19,200 ops across 300 seeds |
| `ChooseWithoutReplacement` vs `choice(size=k, replace=False)` | ✗ **diverges** | first miss at seed 0, `n=10`, `k=3` |

The divergence has a single cause, ✓ VERIFIED over 1,500 cases: numpy's `replace=False` is
`permutation(n)[:k]`, a **full** shuffle truncated to `k`, consuming `n-1` draws. The fork does a
partial Fisher-Yates consuming `k`. So the fix is to implement it as shuffle-then-take-`k`, which
we confirmed reproduces numpy exactly. This matters more than one wrong result: the draw counts
differ, so a single `RandomChoice2` call desynchronizes the whole stream after it.

**The control run changed our picture of F3.** Running the same audit against our own
`engine/lib/mt19937.py` (`--bundled`) shows its MT19937 core is already **byte-exact with numpy**:
seeding lands on the same 624-word state for 300 seeds, and the raw stream matches for 450,000
words. Every failure is in the layer above the core:

- `randint` scales a float (`extract_number() / 2**32`) instead of numpy's masked rejection on the
  raw words, so the same words map to different indices and consume a different number of draws.
- `shuffle` performs `10 * len(X)` random transpositions rather than Fisher-Yates, spending `20n`
  draws where numpy spends `n - 1`.

So F3 is not "the bundled generator is wrong," it is "the bundled generator is right and its three
consumption functions are wrong." Roughly 40 lines, not a rewrite. That is a materially smaller and
safer fix than adopting an outside file, and it keeps the fork clear of code whose provenance and
license we do not control, which matters while U5 is unresolved.

**Done 2026-08-10**, tracked as [F10](#f10-the-bundled-generator-is-right-its-consumption-layer-is-wrong).
The bundled backend now reproduces numpy on every check in the table above, the stamp is versioned
`mt19937-v2`, and a scene recorded under either current backend loads under either. The
consequence for upstream is the interesting part: this is the missing piece of the thing irefrixs
said he wanted and never built, so **U8 now carries a working answer to his own problem rather than
a bug report.** The 10 MB numpy dependency can be dropped without invalidating a single save file.

Two limits on that result. Only small integer seeds were tested, which is the real range since
`Random.RandomSeed` uses `randrange(2**31-2)+1`; numpy routes seeds above 32 bits through
`init_by_array`, and the fork's `Seed` implements only `init_genrand` (its docstring says the
contract never uses `init_by_array`). And the file's stated purpose is a cross-engine contract
shared with a C# rewrite, not numpy parity, so the parity may be incidental and free to drift.
Its own docs (`docs/rng-contract.md`, `datasets/rng/vectors.json`) were not read.

Reproduce either run, and gate any future change to the bundled backend, with:

```sh
.venv/bin/python tools/rng_parity_check.py            # the file he recommended
.venv/bin/python tools/rng_parity_check.py --bundled  # ours, the control
```

He also restated the PVP position directly: *"this engine still has significant limitations…
it is not capable of handling features such as PvP properly. We are sharing the project primarily
for people who are interested in learning how we built the game."* Section H disputes this; issue
#4's follow-up (section H draft) addresses it respectfully.

### Prior community work

`kmelkon` filed issue #1 and PR #2 covering the macOS source install. **PR #2 was closed without
being merged** (`mergedAt: null`), but part of its content shipped as irefrixs's own commits.
Working model: he takes diffs and applies them himself. Write contributions as issues carrying
usable diffs; do not expect PR merges.

| kmelkon finding | Landed? |
| --- | --- |
| `numpy` missing from `requirements.txt` | ✓ applied (`ccb25a3`) |
| bogus `PIL` entry | ✓ applied (`ccb25a3`) |
| macOS/TS build steps in install guide | ✓ applied (`2ac194a`) |
| **`Engine.SaveCrash` masks startup errors** | ✗ **not applied**, see A9 |

`mggarofalo` is a third fork, last pushed 2026-08-10, and irefrixs is reading it. It is a deep
rewrite rather than a patch set: source moved under `py_src/`, an RNG behaviour contract written
down in `docs/rng-contract.md` with test vectors in `datasets/rng/vectors.json`, and a parallel C#
engine. Its `mt19937.py` is the file irefrixs recommended, and per the audit above it does
reproduce numpy for shuffle and choice. Worth watching: it is solving the same determinism problem
we are, one layer deeper, by writing the contract down first.

### Our contributions, closed

Historical. Every row is answered or superseded, and no new ones are added: see the section head for
why. Kept because "what was offered, and what he said back" is the reasoning behind the current
stance, and because two of these answers, the RNG history on #4 and the save format on #6, are the
only public record of how those parts of the engine came to be.

| ID | Item | Status |
| --- | --- | --- |
| U1 | Issue #4, RNG divergence (F3) + state-capture cost (F1, F2). Posted 2026-08-09 as `hexate`. | **ANSWERED** 2026-08-10, both questions engaged, F1 cleanup invited |
| U2 | PVP feasibility issue (section H) | DRAFTED, **reconsider**, see pacing |
| U3 | Scene save/load defects (F5, F4). F5 is fixed on `pr/puzzle-save-mutation`, so this can carry a patch rather than just a report. | DRAFTED, needs re-aiming as a bug report |
| U4 | `command_validation.py` (F6) | DRAFTED, needs re-aiming as a bug report |
| U7 | Issue #5, unbounded retry in `ChooseEffects` (I7). Posted 2026-08-09 as `hexate`. Fix ready on `pr/cap-input-retries`. | **ANSWERED** 2026-08-10, **declined**, fork-only now |
| U6 | Comment on #4 correcting 34× to 18.9× in situ, and noting F9. Text in `docs/pending/issue4-comment-rng-figure.md`. | **SUPERSEDED** by U8, which folds the correction in. Do not post both. |
| U8 | Reply on #4: F1 patch as he asked for it, the `ChooseWithoutReplacement` gap in the implementation he recommended, and **F10**, which is the numpy-compatible pure-Python generator he said was intended but never built. Folds U6 in. | **POSTED** 2026-08-10 as `hexate`, [comment](https://github.com/irefrixs/marvel-lcg/issues/4#issuecomment-5243489423). Carries links to `pr/random-state-capture` and `pr/rng-numpy-parity`, both pushed to the fork. **Edited 2026-08-10 18:31 UTC**, before he replied, to correct the `AddCounter` figure and withdraw the F9 suggestion. Editing does not re-notify, so he may still hold the original by email. **NO REPLY** as of 2026-08-18, eight days. He answered #6, #7 and #8 on 2026-08-18 and passed over this one, so read the silence as a decision rather than a miss. He had already said yes to the F1 cleanup in writing and never asked for the branch. Nothing here is blocked on him; F10 and F11 shipped in the fork on 2026-08-10. |
| U9 | Issue #6, `unit_test/test_task.py` commits to git and bumps the version when the suite runs (I8). Text in `docs/pending/issue-test-task.md`. | **ANSWERED** 2026-08-18, **declined as working-as-intended.** Both cases are deliberate: the `test_` prefix on `IncreaseVersion` is what makes VS Code draw a run button for it, and `test_zip_cards` packages the paid scripts build. *"Feel free to remove or rename them there if you prefer."* His second comment is the valuable part and had nothing to do with the report, see the already-answered table. Fixed locally on 2026-08-18 anyway (I8). |
| U10 | Issue #7, `/debug` reaches `exec` and its auth wrapper is inactive by default (F6/F6a). Carries the fix as `pr/gate-debug-endpoint`. Text in `docs/pending/issue-debug-endpoint.md`. | **ANSWERED** 2026-08-18, **conceded and declined.** He agrees the blocklist is not a boundary and that a whitelist would be safer, then argues the shipped itch.io build cannot reach the endpoint because scripting is off unless the host enables it at launch. He did not engage with the part the report was actually about, that the auth wrapper in front of it admits everyone by default. Fork-only now; `pr/gate-debug-endpoint` stands. |
| U11 | Issue #8, the game over "Save replay" button saves nothing and reports success (J13). Carries the fix as `pr/save-replay-handler`, one commit on `upstream/master`. | **POSTED** 2026-08-11 as `hexate`, [issue #8](https://github.com/irefrixs/marvel-lcg/issues/8). **ANSWERED** 2026-08-18: **confirmed as a real bug**, with the deleted function pasted in and the cause named. Still no fix and no plan for one, which is what dates the "urgent bugfix" exception. The reply is worth more than a merge would have been, because it tells us what the handler is supposed to do; see J13. |

**Pacing, revised 2026-08-10.** The hold is over. He replied to both issues in detail, so the
question is no longer whether he is listening but what is worth sending.

U6 was held until there was a live conversation to attach it to. There is one now, and the #4
title still says 34×, so send the correction.

U8 is the one contact with a standing invitation behind it. He asked for the state-capture cleanup
in writing, so F1 is not an unsolicited patch. Pair it with the `ChooseWithoutReplacement` finding:
he recommended a file that is one method away from numpy parity, and that is directly useful to the
goal he stated. This is a reply to an open thread, not a new issue, so it does not spend the
"split future questions into separate issues" budget.

**Revised 2026-08-18.** Every posted item is now answered except U8. Nothing above is waiting on
upstream any more, and nothing below should be written for upstream. U2, U3 and U4 were queued
against a stance that no longer exists: three separate replies have now conceded a technical point
and then declined to act on it, including one he called an actual bug. Recommend closing U2, U3 and
U4 as upstream items and keeping their content as fork direction. The one thing still worth asking
him for is U5, the licence, because that is a signature rather than a patch and only he can supply
it.

U7 is closed as an upstream matter. He declined it on design grounds and the fix lives on
`pr/cap-input-retries` for the fork. Note his reason does not engage with the three hangs in the
report that are reachable from a stock checkout and have nothing to do with `cheat` (the `KeyInput`
path, `InTesting` skip mode, `ConsoleDevice.IsSyncReady`); he read it as a request to harden a
cheat path. Not worth re-arguing. It **is** worth remembering that the three hangs are still real
for anyone writing a non-replay test device, which is exactly what I2 does, so the value of the cap
did not depend on his agreement.

U2 needs a decision rather than a send date. It argues PVP is more feasible than he has twice
stated publicly, and it lands as a 300-hour-refactor debate with someone who has just declared the
project sunset and is pointing contributors at other forks. It costs goodwill on the one channel
that is currently productive. Recommend holding it indefinitely and keeping section H as fork
direction.

U3 and U4 are still worth sending, but reframed. Under the sunset rule the only category he
accepts is "urgent bugfix," so lead with the defect and its reproduction and let the patch follow,
rather than presenting them as improvements.

U6 is committed at `docs/pending/issue4-comment-rng-figure.md`. U2, U3 and U4 drafts are still
only in the session scratchpad (`issues_draft.md`) and will be lost when it is cleaned up; move
them into `docs/pending/` before relying on them.

### Working on the fork does not depend on upstream replies

The fork is `hexate/marvel-lcg`, with `upstream` → `irefrixs/marvel-lcg` already configured. None
of the work in this document is blocked on a reply to issue #4.

irefrixs granted permission explicitly and in writing (issue #3):

> Yes, you are welcome to publish your own builds, even before we finalize the license… Our
> intention is to use a permissive license that allows everyone to freely modify and distribute
> this code, while also helping ensure that the game remains free for everyone to play.

He also pre-approved attribution wording — *"originally developed by the Irefrixs Team"* — and
another contributor (`z00lus`) is already maintaining a divergent fork with his knowledge.

| ID | Item | Status |
| --- | --- | --- |
| U5 | **No `LICENSE` file exists.** Absent one, default copyright is "all rights reserved"; the issue-#3 comment is strong evidence of intent but is not a license grant with terms. Low risk for private/hobby work, real risk before any distribution or commercial use. He has already named Apache 2.0, so the ask is "please commit the file," not a new question, offer to send it. | PROPOSED, **more urgent after 2026-08-10**: a sunset project may never get one, and he is actively pointing people at forks he cannot license |

### U11: the content layer, which no licence from upstream can settle

Raised by Q on 2026-08-19 while reviewing the README caveat, and the more consequential of the two
rights questions. U5 is about the engine, which is irefrixs's to license. This is about everything
the engine reads, which is not his and not ours.

**What this repository actually distributes.** ✓ VERIFIED rather than assumed:

- `data/cards.json` is tracked, 2.0 MB, and carries the printed text of **3,524 cards** verbatim.
  That is Fantasy Flight's expression, not game mechanics.
- `assets/` is **not** distributed. It is gitignored and sits at 328 MB locally only. The fetch
  URLs in `engine/file/cache.py:201-203` point at community databases, Cerebro and MarvelCDB, so
  art arrives on the player's machine from a third party or from their own itch.io download.
- The art carries its own notice. The Weapons Runner face reads "© MARVEL © 2019 FFG" along the
  bottom edge, legible in the centre preview.
- The repository name, and the game's name, are FFG and Marvel marks.

**The distinction that matters.** Rules and mechanics are generally not copyrightable, so an engine
that implements how the game plays sits on much firmer ground than the data it reads. Card text,
card art, character names and the product name are a different category, and a permissive licence
from irefrixs would settle U5 and change nothing here.

**What moves the risk**, as far as anyone here can judge: visibility, how easily it substitutes for
buying the game, and whether money is ever involved. Today it is a code repository plus card data,
with no build distributed and no art shipped, which is roughly what upstream did publicly for weeks.
A one-click bundle with art included, or wide promotion, is a different proposition.

**Note the sunset was not this.** The announcement gives three reasons and all three are technical:
Python's runtime cost, the unfinished buff migration, and a 300-hour PVP refactor. No legal reason
appears anywhere in it, and it explicitly opens the project "so the community can still build,
extend, and improve". Evidence that there was no takedown. Not protection.

**Status: PROPOSED, and deliberately not acted on.** Q's call on 2026-08-19 was to record it here
rather than in the README, on the reasoning that a prominent notice is itself a flag. Two things
follow for whoever picks this up. `assets/` staying out of the repository is load-bearing and should
not be re-included for convenience. And none of this is a lawyer's opinion, which is what "treating
this as the continuation" would need before it meant broad public distribution.

### F8 re-scoped: isolation is enforced, the gap is the `GetAll*` family

Investigated 2026-08-19. The row said cross-area isolation is opt-in and pointed at
`checker.py:174`, and H5 sized it as auditing every finder call site, "likely the largest hidden
cost". Both were wrong, and the correction cuts the work by more than an order of magnitude.

**Isolation is enforced by default, in the scopes.** ✓ VERIFIED by reading the path:

- `Worlds.CastGameArea(effect)` derives an area from the effect's own card, or for a player-triggered
  message from that player's identity card.
- `Worlds.GetPlayers` filters explicitly: `x.GetIdentity().card.GetGameArea() == game_area`.
- `Worlds.GetOnFieldCards` walks only the players in that area.
- `Worlds.FindCardsOnField` **defaults** the area from the effect when the caller omits it
  (`worlds.py:496-497`), which is the opposite of opt-in.

So the observation that 1 of 874 `CardFinder(` constructions passes `game_area` is true and means
almost nothing: the candidate set handed to the finder was already area-scoped. `checker.py:174` is
a second, narrower filter, not the mechanism.

**The real gap is a named family that is deliberately global**, and it is small enough to audit:

| Accessor | Call sites |
| --- | --- |
| `GetAllVillains` | 14 |
| `GetEncounterDiscardPileCards` | 12 |
| `GetAllMainSchemes` | 11 |
| `GetEncounterDeckCards` | 6 |
| `GetAllSideSchemes` | 3 |
| `GetAllLeaders` | 1 |
| `GetOnAllFieldScheme` | 0 |

47 sites across six functions, each of which returns everything in the world regardless of area.
Whether that is wrong depends on the site: some are surely meant to be global, and the names say so.
The work is deciding, per site, whether Kang's separated boards should see each other there.

**And this is live, not PVP-only.** `World.CreateGameArea` has exactly one caller,
`cards/pack/toafk/kang/__init__.py:107`, where Kang's stage 3 moves a player, the main scheme and
Kang himself into a new area. Multi-area play ships today. F8 has been filed as a PVP blocker since
2026-08-09 and it is really a Kang correctness question that PVP would also depend on.

**Not attempted, deliberately.** Each of the 47 needs a rules judgement rather than a mechanical
change, and getting one wrong alters game behaviour silently and invalidates recorded replays. It
also wants someone who has played Kang far enough to see stage 3, which nobody here has. What this
entry buys is that the next person audits 47 named call sites instead of 874 anonymous ones.

### Branch layout and how to package a contribution

**Revised 2026-08-19, when this repository became the project's continuation rather than a queue of
patches for upstream.** `stable` is now `main`, and `main` is the default branch. The rename is the
visible half; the reason is that a newcomer arriving at the repository should land on the project.
Before this, the default branch was `master`, so the front page showed unmodified upstream code and
none of the work.

| Branch | Purpose | Upstream? |
| --- | --- | --- |
| `main` | the trunk and the default branch. Everything stabilized, and what you actually run | no |
| `master` | pinned mirror of `upstream/master`, never committed to directly | no |
| `feat/<topic>` | one new feature or improvement, cut from `main` | no |
| `pr/<topic>` | historical. One contribution, cut fresh from `upstream/master` | closed |
| `work/engine-audit` | retired at `aababf0`. The stabilization line, kept as history | never |

`master` stays pinned to `upstream/master` and must stay there, even though nothing is being offered
upstream any more. Every `compare/master...pr/x` link posted in an upstream issue reads against it,
so moving it does not break those links, it silently rewrites what they show. Keeping it costs one
branch name.

The `pr/*` branches are a record of what was offered and declined, not a live queue. Do not cut new
ones. Their contents are already in `main`; they exist separately because a contribution had to be
readable as a diff against upstream, which is no longer a thing worth spending effort on. See
section 0 for how that was decided.

Feature work starts from `main`:

```sh
git checkout -b feat/<topic> main
```

Assume fork-only. Upstream declared sunset on 2026-08-10 and takes urgent bugfixes case by case, so
a feature is not a candidate unless it is small, self-contained and fixes something rather than
adding to it. When one does qualify, cut a separate `pr/*` branch from `upstream/master` and
cherry-pick, exactly as below. Do not offer a `feat/*` branch upstream directly.

```sh
git fetch upstream
git checkout -B pr/<topic> upstream/master
git cherry-pick -x <sha>            # commits on work/ are kept atomic for exactly this
./tools/make-upstream-patch.sh pr/<topic>
```

That writes `out/patches/pr-<topic>.patch` (git-am-able) and `.diff` (paste into the issue).

**Branches pushed to the fork, 2026-08-10.** `pr/rng-numpy-parity` now exists on `origin`, so U8
could link a readable comparison rather than paste 300 lines into a comment. Because the branch is
stacked, the useful URL compares it against its base, not against master:
`compare/pr/rng-backend-determinism...pr/rng-numpy-parity`. Every other `pr/*` branch was already
pushed.

**Deliver the diff, not the PR.** PR #2 was closed with `mergedAt: null` while its content
shipped as `ccb25a3` — he reads contributions and re-applies them himself. So the issue body
carrying a readable diff is the actual deliverable; a PR is a convenience link, not the mechanism.
Combined with his "split future questions into separate issues" request, the unit of contribution
is **one issue + one small diff per topic**.

Currently cut, all one commit off `upstream/master` unless noted:

| Branch | Contents | Size |
| --- | --- | --- |
| `pr/gitignore-dev-files` | ignore `launch-debug.json`, generated replays | 1 file 3 + |
| `pr/guard-savecrash` | A9, startup failures no longer masked (kmelkon's finding) | 2 files 55 + 1- |
| `pr/narrow-effect-filter-except` | J1, bare `except` narrowed to `TypeError` | 2 files 74 + 2- |
| `pr/rng-backend-determinism` | F3, RNG backend recorded on scenes, mismatch refused | 4 files 151 + 1- |
| `pr/random-state-capture` | F1, RNG state capture made opt-in | 2 files 112 + 3- |
| `pr/cap-input-retries` | I7, retry cap in `ChooseEffects` (issue #5) | 2 files 93 + |
| `pr/puzzle-save-mutation` | F5, puzzle save no longer mutates the live replay log | 2 files 99 + 5- |
| `pr/test-harness` | I2, replay-independent harness + first tests | 2 files 278 + |
| `pr/rng-numpy-parity` | F10, bundled generator reproduces numpy, stamp versioned. **Stacked on `pr/rng-backend-determinism`, not on `upstream/master`** | 4 files 304 + 38- |
| `pr/rng-undo-bundled` | F12, `Random.Undo` works on the bundled backend instead of silently doing nothing. **Stacked on `pr/random-state-capture`** | 3 files 108 + 14- |

**Two exceptions to the rule above**, both 2026-08-10. F10 needs F3's scene stamp in order to
retire the old backend name, and F12 needs F1's `enable_random_undo` flag and `states` list. Neither
can sit directly on `upstream/master`, so each is cut from the branch it depends on and its patch
generated against that base:

```sh
./tools/make-upstream-patch.sh pr/rng-numpy-parity pr/rng-backend-determinism
./tools/make-upstream-patch.sh pr/rng-undo-bundled pr/random-state-capture
```

A stacked branch is worth one extra check before it is offered: that it did not quietly absorb work
from a sibling. Cutting F12 caught exactly that. Its `GetState`/`SetState` hunk sits next to F10's
`randbelow` in the file, so the cherry-pick brought `randbelow` along and conflicted. Resolving it
by hand kept the state methods and dropped the rest.

Sent upstream, the two travel together or F10 goes second. Note the branch deliberately omits
`unit_test/test_rng_same_game.py`, which needs the I2 harness; that test stays on the work branch
and would ride with `pr/test-harness`.

**Decision, affirmed 2026-08-10.** Keep this layout. Contributing back is a goal in its own
right, not a byproduct of the work, so the per-fix isolation cost is worth paying even though
merging everything onto a fork trunk would be less effort. Do not collapse `pr/*` into the work
branch.

Worth remembering that "upstream" is not only irefrixs. `kmelkon` is doing install and
portability work, and `z00lus` is building a solo-first self-hosted fork (both visible in issues
#1 and #3). F1, F3, I7 and A9 are useful to them whether or not irefrixs ever replies, so a
silent maintainer does not make the patches worthless.

**Fork discipline** — keep changes cherry-pickable, since he applies diffs rather than merging PRs:

- one topic branch per tracker item, small and self-contained
- keep upstream-contributable fixes (F1–F6, F10, A9, I1, I4, I7) separate from fork-only direction
  (docs, tooling, PVP). I2 turned out to be contributable too and is cut as `pr/test-harness`.
- rebase on `upstream/master` periodically rather than letting the fork drift
- `launch-debug.json` is deliberately untracked upstream — add it to `.gitignore` locally, do not
  commit it

---

## A. macOS / portability

Source: local audit on 2026-08-09, macOS 15 (Darwin 25.5.0), Python 3.13.12, Apple Silicon.

**Baseline result: the game already runs on macOS.** ✓ VERIFIED — `pip install -r requirements.txt`
succeeded, `python main.py` started and bound `127.0.0.1:2345`, and `GET /main.html` with an
`app_version=0.5.9.201r` cookie returned the real menu page (not the version-mismatch page).
The items below are residual defects, not blockers.

Upstream had already done most of the port: `winsound` removed (e6572d5), `psutil` removed
(43e87c6), `SetTitle`/`Pause` guarded behind `platform.system() == "Windows"` (8bea418),
macOS build steps added to the install guide (2ac194a).

| ID | Item | Location | Severity | Status |
| --- | --- | --- | --- | --- |
| A1 | `tsconfig.json` set `moduleResolution: "node"`, which TypeScript 7 reports as `node10` and has removed (`error TS5108`). The install guide says `npm install -g typescript`, which now installs 7.x, so a fresh clone could not build the client | `public/js/tsconfig.json:37` | High (blocks a clean build) | **DONE**, option removed; clean compile and emit on 7.0.2 and 5.9.3 |
| A2 | Coverage key check hardcodes Windows separators: `name.startswith("cards\\pack\\")`. On macOS/Linux paths use `/`, so `GetKeyName` returns `""` for every card and card-script coverage silently reports nothing. | `engine/profile/coverage.py:19` | Medium (dev tooling, silent failure) | **DONE**, separators normalised before the comparison |
| A3 | Untrusted-save guard tests `"crashs\\dl" in world.scene.path`, never matches on POSIX, so the `DebugBreak()` safety stop before `exec(cmd)` is skipped. | `game/world/cheat/cheat_cmd_helper.py:478` | Medium (debug-only, but it is a safety check) | **DONE**, `IsUntrustedScenePath`, tested both separators |
| A4 | `IsDrivePath` only recognizes `C:\` / `C:/`. POSIX absolute paths (`/Users/...`) are not detected as drive paths, affecting the cheat command that loads a scene by absolute path. | `engine/file/manager.py:156` | Low **Half of this closed with A5:** `FormatPath` no longer pastes `./` onto an absolute POSIX path. `IsDrivePath` itself is unchanged, so `FindJsonFile` still fails to short-circuit on `/Users/...` and falls through to the folder search. | PROPOSED, narrowed |
| A5 | `FormatPath` indexes `normalized_path[1]` without a length check → `IndexError` on a 1-character path. Platform-independent, found during the port. | `engine/file/manager.py:165` | Low | **DONE**, length guard plus `os.path.isabs` |
| A6 | `Beep` is a no-op on **every** platform since `winsound` was stripped, audio cues are gone, not just on macOS. Could be restored cross-platform (`afplay` on macOS, `paplay`/`aplay` on Linux) or the dead code removed. | `core/lib/beep.py` | Low | PROPOSED |
| A7 | `FileManager.EditCode` shells out to `code`; fails silently via `os.system` if the VS Code CLI is not on PATH. | `engine/file/manager.py:149` | Low | PROPOSED |
| A8 | `public/js/watch.bat` is Windows-only. A `watch.sh` companion would match the documented macOS/Linux flow. | `public/js/watch.bat` | Cosmetic | **DONE** 2026-08-19 as a side effect of C3. `./build.sh --watch` is the cross-platform equivalent and needs no second script; `watch.bat` stays for Windows users who double-click it |
| A10 | **`.gitignore` misses `save.json`.** The rule is `/save_*.json`, which does not match `save.json`, the exact filename the debug `/save` command writes (`ex_save_name = './save.json'`, `game/cheat/cheat.py:126`). Confirmed with `git check-ignore`. One-character fix; belongs on `pr/gitignore-dev-files`. | `.gitignore:6` | Low | **DONE**, rule widened to `/save*.json` |
| A9 | **`Engine.SaveCrash` masks any startup failure.** Uses `Engine.game` (assigned at `engine.py:104`) but runs for crashes before that, so the handler itself raises `AttributeError` and hides the real exception. Found by `kmelkon` in #1; PR #2 was closed unmerged and this piece never landed. | `engine/engine.py:159-162` | Medium | **DONE**, `pr/guard-savecrash`, credit kmelkon |
| A11 | **A value that begins with `/` is parsed as another option name, so the option before it silently becomes the boolean `True`.** `ParseArguments` treats any token starting with `/` or `-` as a key, which is the Windows switch convention, and an absolute POSIX path is indistinguishable from it. `-game_statistics_file /tmp/x.json` therefore leaves `game_statistics_file` with no values, the `len(value) == 0` branch stores `True`, and `ConfigVariable.Str.SetValueInternal` stringifies that to `"True"`. The path itself is stored as a variable named `tmp/x.json` that nothing will ever read. ✓ VERIFIED twice: `ParseArguments(['-demo_file', '/tmp/x.json'])` yields `{'demo_file': True, 'tmp/x.json': True}`, and a real run passing an absolute `-game_statistics_file` wrote the entire statistics file to a file named `True` in the repository root. Every file and folder option is exposed, which is all of `config_files`, `game_statistics_file`, `test_result_file` and the folder lists. Only reachable from the command line, which is why play has never hit it. `ParseString` handles quoting but nothing quotes argv. The fix has to choose: keep `/` as a switch prefix and lose absolute paths, or drop the Windows convention on POSIX, where `A4` and `A5` show the codebase is already carrying that assumption in the path layer | `engine/config.py:138` | Medium, silent, POSIX only | PROPOSED |

### Not defects: documented for the next person

- **`assets/` is absent from the repo by design** (`.gitignore`). It must be pulled from the
  itch.io build. Without it the game still runs and falls back to the card-image CDN configured
  in `launch.json`; there is no local art or sound. ✓ VERIFIED — ran without `assets/`.
- **`launch.json` is the game's own config file**, not a VS Code debug config.
- **Case sensitivity is a latent risk, not a current one.** macOS APFS is case-insensitive by
  default, so mismatched-case imports would pass here and fail on Linux. ✗ UNVERIFIED — no audit
  of import casing has been done.
- **`engine/task/manager.py:10`** already guards `WindowsSelectorEventLoopPolicy` behind
  `sys.platform == 'win32'`. No change needed.

---

## B. Architectural issues cited by the original developer

Source: irefrixs, *"Marvel Champions: Digital Edition — The Final Update"*, itch.io devlog,
2026-07-31. These are the reasons given for discontinuing development and open-sourcing.
Full quotes and links are in [`docs/upstream_rationale.md`](upstream_rationale.md).

Each has been cross-checked against the code below.

| ID | Item | Severity | Status |
| --- | --- | --- | --- |
| B1 | **Runtime performance.** Python backend is "fast for development, but slow at runtime." UNDO in 4-player can take over a minute. | Critical | PROPOSED, needs profiling before any fix |
| B2 | **Function registration instead of Buff.** Centralized registered functions are easy to review but hard to serialize, which is what makes UNDO impractical. A `Buff` replacement was started and never finished. | Critical | PROPOSED, partial migration exists |
| B3 | **New FFG PVP rules.** The engine was not built to accommodate them; upstream estimated ~300 hours of refactor and expected many hard-to-find bugs. | Large feature | PROPOSED |

### B1: UNDO cost

✓ VERIFIED (mechanism, not timing). Undo is implemented as *replay from the beginning*, not as
state rollback:

- `game/scene/` records the full list of player `inputs` for the session.
- `engine/controller/manager.py:50-89`: on a start-state with `is_undo`, the manager reloads the
  scene, calls `SetReplayInputs(scene.inputs)`, and sets up `skip` to fast-forward.
- `engine/controller/module/skip.py` fast-forwards by re-executing game logic with rendering
  suppressed — it does not skip the computation.

So a single undo is O(actions-so-far) of full game-logic execution. Cost grows through the game
and multiplies with player count, which matches the reported "more than a minute" late in a
4-player game.

`engine/controller/module/undo.py` contains a "fast undo" path
(`PushFastUndo`/`GetFastUndoHandle`) that caches which card object IDs produced effects for a
given message, letting the replay prune effect evaluation. ✗ UNVERIFIED — how much this actually
saves, and when `DoNotCheckFastUndo()` disables it, has not been measured.

**Before proposing a fix:** profile a real 4-player session. The devlog blames "Python," but the
mechanism above suggests the cost is algorithmic (replay-from-zero), not interpreter speed. If so,
snapshot/rollback would beat any language change. Treat "rewrite it in a faster language" as
unproven until the profile says otherwise.

### B1a: RETRACTED. The skip guard already exists and works.

**This entry was wrong. Read the retraction before the measurement.**

The original claim was that replay rebuilds the world descriptor on every message and throws it
away, because line 96 of `PresentInternal` is unconditional. Line 96 *is* unconditional, but it is
unreachable during replay: `PresentInternal` returns early at **lines 59-73** whenever `skip` is
set, before any descriptor work happens.

✓ VERIFIED by direct measurement. Twenty `PresentInternal` calls on a live world:

| | descriptor builds |
| --- | --- |
| `skip=False` | 20 / 20 |
| `skip=True` | **0 / 20** |

**How the error happened, because it is worth not repeating.** The 62% figure below is real, but
it was measured on the test harness, which deliberately runs with start state `'New'` so that skip
is *off* (skip discards scripted input, which was blocker 2 when the harness was built). So the
number describes **live play**, where building the descriptor is the legitimate work of producing
the UI. It was then attributed to replay, which never executes that path. The measurement was
sound; the thing it was measured on was not the thing being claimed.

The comment upstream already sitting above that guard says as much: *"Comment out this to render
the game while testing, but it is VERY slow."* The problem was known and handled.

**What survives.** During live play, descriptor construction is 62% of runtime at 1.14 ms per
message and roughly 12.7 messages per recorded input. That is worth knowing for interactive
responsiveness, and it is why the harness is slow, but it says nothing about undo.

**What this means for the harness.** Running with skip off makes it unrepresentative of replay
performance by construction. Any future attempt to measure undo cost has to run with skip on,
which is the mode that breaks scripted input. That conflict is the real obstacle to G1, not the
driver stalling.

Original measurement, on a 10-input single-player game with 82 cards, **live play, not replay**:

| | |
| --- | --- |
| `ToDescriptor.World` calls | 127 |
| time in those calls | 0.145 s of 0.233 s wall |
| **share of runtime** | **62%** |
| per call | 1.14 ms |

That is roughly 12.7 descriptor builds per recorded input. During replay every one of them is
thrown away: the descriptor has exactly one consumer, `engine/device/web/server/server_sync.py:79`,
which serves it to a browser that is not watching.

**Why this matters for B1 and E.** The devlog attributes slow UNDO to Python being slow at
runtime. The dominant cost measured here is not interpreter speed and not the replay-from-zero
algorithm. It is rebuilding a UI payload nobody reads, once per message, throughout the replay.
Scaling the per-call figure by a 4-player card count and a few hundred inputs lands in the right
order of magnitude for the "more than a minute" in the devlog.

**Proposed fix.** Guard line 96 so the descriptor is only built when something will consume it.
Needs care: a browser polling `server_sync` mid-skip would receive the last pre-skip descriptor
instead of a current one. That is probably correct behaviour during a fast-forward, but it should
be confirmed rather than assumed.

| ID | Item | Status |
| --- | --- | --- |
| B1a | ~~Skip does not gate descriptor construction~~ | **RETRACTED**, the guard exists at `world_render.py:59`; 0/20 builds with skip on |
| B1b | Descriptor construction is 62% of **live play** runtime, 1.14 ms per message. Real, but it is the UI being produced, not waste. Relevant to interactive responsiveness only. | PROPOSED, low priority |

Note `engine/task/manager.py` gates threading behind `enable_multiple_threads`, default `False`.
✗ UNVERIFIED — whether enabling it helps, or why it is off.

### B2: Buff migration is barely started

✓ VERIFIED by count:

- **3,457** card scripts under `cards/pack/` (excluding `__init__.py`)
- **15** of them reference `Buff` at all

So the migration upstream described as "started" covers well under 1% of card scripts. The
infrastructure exists and is small:

- `game/buff/buff.py`: `Buff` base class: `by_effects` list, `OnGain`/`OnLost`, `OnRoundEnd`,
  `OnRecordPlayedFace`, UI text. Concrete buffs like `BuffIsTreatAsIfBlank` subclass it.
- `game/buff/manager.py`: `BuffManager.RegisterBuffer(type)`, forwards round-end and
  played-face events.
- `game/card/face/component/buffs.py`: card-face integration.

This is the single largest lever on B1: buffs are declarative state that can be serialized and
rolled back, whereas registered closures cannot. Any UNDO redesign probably depends on this
landing first.

**Open question for Q:** is finishing a 3,400-script migration realistic here, or is the
better play a compatibility shim that lets both mechanisms coexist and converts scripts lazily as
they are touched?

### B-measure: Codebase size and measured performance (2026-08-09)

Taken to inform the "fix in Python vs. port to another language" decision.

**Size** (Python, excluding `__pycache__`):

| Area | Lines | Files | Nature |
| --- | --- | --- | --- |
| `cards/` | 102,461 | 3,859 | Card rules content, **63% of the Python codebase** |
| `game/` | 53,169 | 326 | Rules engine |
| `engine/` | 5,883 | 68 | Platform: web server, tasks, file I/O, config |
| `core/` | 666 | 16 | Utilities |
| `public/js/` | 10,535 | 38 | TypeScript frontend (language-independent; talks HTTP) |

**Measured** ✓ VERIFIED — macOS, Python 3.13.12, Apple Silicon:

| Measurement | Result |
| --- | --- |
| Config + `CardsDB.Initialize()` | 0.32 s |
| Import all 3,457 card scripts | 0.89 s total, 0.26 ms each, 0 errors |
| Card scripts loaded at startup | 0, imports are lazy |

**Design note** ✓ VERIFIED: `game/event/manager.py` indexes effects as
`self.effects[category][message_type][priority]`. Dispatch is a dict lookup by message type, not
a linear scan over all registered effects. The hot path is not naively designed.

**Still unmeasured** ✗ — per-action game-logic time in a real multiplayer session. The repo ships
a replay-based test harness (`unit_test/entry.py`, `game/test/test_run.py`) that already reports
`Average Time` per input, but **no test scenes ship** — `Test.GetTestCases` reads from
`REPLAY_FOLDERS` (`./replays/`), which is absent. This is the one number that would settle B1.
See G1.

### B3: PVP rules

✗ UNVERIFIED — no audit yet of what specifically in the engine assumes co-op (single villain,
shared encounter deck, non-adversarial targeting). The ~300h estimate is upstream's, for their
own codebase and standards. Do not treat it as a scoped estimate for this project.

---

## C. Build and tooling

| ID | Item | Severity | Status |
| --- | --- | --- | --- |
| C1 | No pinned dependency versions, `requirements.txt` lists bare package names. A lockfile or version floors would make builds reproducible. | Medium | **DONE**, upper bounds at the next major of each, verified by installing into a clean venv. Floors deliberately omitted, see below |
| C2 | No CI. Repo has `unit_test/` and `game/test/` but nothing runs them automatically. | Medium | **DONE**, `.github/workflows/tests.yml`: 66 tests on push and PR, plus a client type check on TypeScript 5 and 7 |
| C3 | Compiled JS is gitignored and must be built before first run; there is no build script wrapping the Python + TypeScript steps. | Low | **DONE** 2026-08-19. `./build.sh` does both halves and is idempotent; `play.sh` calls it when anything is missing instead of printing instructions, and its instructions were stale anyway, still citing the `moduleResolution` problem fixed on 08-10. TypeScript is a devDependency of `public/js` with a tracked lockfile rather than a global install, so the version is pinned with the project instead of being whichever major `npm install -g typescript` gives you that month, which is exactly what broke the build on 08-10. ✓ VERIFIED by deleting every compiled file and rebuilding: 39 `.ts` in, 39 `.js` out, and the client then loads with all globals present and 92 cards rendered. Doing that also turned up the hazard now documented in `.gitignore` and `build.sh`: four vendored libraries under `public/js/lib/` are force-added past the blanket `*.js` ignore, so they look like build output and are not, and anything that cleans by deleting `*.js` there destroys them |

---

### C2 findings (2026-08-10): what CI can and cannot run here

The suite runs on a clean checkout. ✓ VERIFIED by cloning the repository to a scratch directory,
which therefore had no `assets/` (117 MB, gitignored and downloaded separately), no
`launch-debug.json` and no recorded games, and running all 66 tests there. They pass, and the clone
was left with no commits and no stray files.

Two modules stay out, and both are traps for `unittest discover` rather than oversights:

| Module | Why it is excluded |
| --- | --- |
| `test_all` | Replays recorded games, which are player data and are not in the repository (I3) |

`tools/run_tests.py` encodes that, prints what it skipped and why, and is what CI calls. It is also
the local command, which is worth more than it sounds: this session repeatedly ran the suite by
naming fourteen modules by hand, and one absent-minded `discover` is what produced the stray
version-bump commits that had to be rebased out this morning.

The workflow asks for `permissions: contents: read`. In a repository where a file under
`unit_test/` makes git commits, a CI job with no write token is a second line of defence rather
than a formality.

Pinned to Python 3.13, the only version the suite has actually been run on. The install guide
claims 3.10.5 and 3.14.2 work, and widening the matrix is worth doing once that is confirmed
instead of assumed. The client type check runs on TypeScript 5 and 7, which pins the compatibility
the A1 fix claims.

## D. Security

Carried over from the README's own warning: the engine `exec`s Python card scripts, so any
third-party card pack is arbitrary code execution. `engine/security/command_validation.py`
maintains a module blocklist (`subprocess`, `webbrowser`, `win32api`, …).

| ID | Item | Severity | Status |
| --- | --- | --- | --- |
| D1 | Assess whether `command_validation.py`'s blocklist approach is sound, or whether it is bypassable (blocklists usually are). This governs the safety of the whole custom-card ecosystem. | High | **DONE**, the audit is F6: bypassable, one payload in eight blocked, and the endpoint it guards is network-facing. Gated in `pr/gate-debug-endpoint`, reported as issue #7. Card scripts remain fully trusted by design, as the README says |
| D2 | A3 above (the `crashs\\dl` guard) is part of this surface, the downloaded-save safety break does not fire on POSIX. | Medium | **DONE**, same fix as A3: `IsUntrustedScenePath` normalises separators |

---

---

## F. Design audit findings (2026-08-09)

First pass over the core systems. Ordered by severity. Everything here was read or executed —
no grep-only claims.

| ID | Finding | Location | Severity | Status |
| --- | --- | --- | --- | --- |
| F1 | RNG state capture costs 34× and leaks unboundedly | `engine/lib/random.py:49,68,78` | **High** | **DONE**, `pr/random-state-capture` |
| F9 | `AddCounter` logs on every draw. Measured at 0.312 µs, fixable to 0.068 µs, but it runs once per draw and a game makes a handful | `engine/lib/random.py:82` | Low | **REJECTED**, saving is microseconds per game |
| F2 | `numpy.random.choice` on object lists is 39× slower than stdlib | `engine/lib/random.py:45-70` | Medium | **DONE** by F11: that call is no longer on the default path, and the bundled `choice` is 4.4× faster than it |
| F11 | Default `disable_numpy_random` to the bundled backend, now that F10 makes it produce numpy's sequence. Removes the numpy dependency and the process-global RNG exposure F3 left open | `engine/lib/random.py:5` | Medium | **DONE**, fork-only |
| F12 | `Random.Undo` hits a bare `pass` on the bundled backend, so the `Unshuffle` cheat silently does nothing whenever `disable_numpy_random` is set. Reachable upstream today, not only after F11 | `engine/lib/random.py`, `engine/lib/mt19937.py` | Medium | **DONE**, `pr/rng-undo-bundled`, stacked on `pr/random-state-capture` |
| F3 | Two RNG backends produce different sequences → replay incompatibility | `engine/lib/random.py` | **High** | **DONE**, `pr/rng-backend-determinism` |
| F10 | Bundled RNG core is byte-exact with numpy; only `randint` and `shuffle` diverge. Fixing them ends the F3 divergence instead of reporting it | `engine/lib/mt19937.py:64,69` | **High** | **DONE**, `pr/rng-numpy-parity`, stacked on `pr/rng-backend-determinism` |
| F4 | `World.LoadFromJson` is dead *and* cannot execute | `game/world/world.py:121-144` | Medium | PROPOSED |
| F5 | Saving a puzzle mutates the live replay log; second save raises | `game/scene/scene.py:113-117` | **High** | **DONE**, `pr/puzzle-save-mutation` |
| F6 | Bypassable blocklist is the only thing between the `/debug` HTTP endpoint and `exec`, and the auth wrapper in front of it passes everyone when no password is set | `engine/security/command_validation.py`, `engine/device/web/server/server_sync.py:107` | **High** | **DONE** for the gate (F6a), see the section for what remains |
| F7 | Player count hardcoded as `(0,1,2,3)[:n]` | `game/world/world.py:94,127` | Low | PROPOSED |
| F8 | ~~Cross-area targeting isolation is opt-in, not enforced~~ **Premise corrected 2026-08-19; the work is real but a fraction of the size.** | `game/operate/worlds.py`, the `GetAll*` family | Medium, and live in Kang rather than PVP-only | PROPOSED, re-scoped. See below |

### F1: RNG state capture: 34× slowdown and an unbounded leak

✓ VERIFIED by measurement. Every `Shuffle` / `RandomChoice` / `RandomChoice2` call does
`Random.states.append(numpy.random.get_state())` before the actual draw.

| Measured (macOS, Python 3.13, numpy) | Result |
| --- | --- |
| `shuffle` with `get_state()` append | 23.9 µs/call |
| `shuffle` without | 0.7 µs/call |
| Overhead | **34×** |
| Retained memory | **50 MB per 20,000 calls** |

`Random.states` is a class attribute. It is **never cleared** — not on new game, not on restart,
not on undo. The only consumer is `Random.Undo()`, which is called from **exactly one place**:
a debug cheat at `game/world/cheat/cheat_cmd_helper.py:390`.

So the entire mechanism exists to serve one debug command, and it taxes every shuffle in normal
play with a 34× slowdown and a permanent memory cost. It also compounds with B1: each undo
replays the session, re-running every random call and appending every state again.

**Fixed** on `pr/random-state-capture`. Capture now sits behind a new `enable_random_undo` config
variable, default off, via `Random.PushState()`. `SetSeed` clears the list, since positions
recorded against an old seed cannot be rewound to anyway. `Undo` asserts with an explanation when
capture is off instead of raising `IndexError` on an empty pop, so the debug cheat fails readably.

Measured over 20,000 `Random.Shuffle` calls on a 50-card list:

| | per call | retained |
| --- | --- | --- |
| capture on | 21.6 µs | 49.9 MB |
| capture off | 1.1 µs | 0 MB |

**Correction to the figure quoted in issue #4.** That issue reports 34×, which is the cost of the
capture measured in isolation against a raw `numpy.random.shuffle`, and is accurate as stated.
Removing it from the real API gives **18.9×**, not 34×, because `Random.Shuffle` carries other
per-draw overhead that the isolated benchmark excluded. Both numbers are true of different things;
the in-situ number is the one that matters. Worth a short follow-up comment on #4 so the
difference is on the record rather than looking like a walked-back claim later.

That overhead is now itself measurable: raw `numpy.random.shuffle` is 0.67 µs, `Random.Shuffle`
with capture off is 1.21 µs, so `AddCounter` costs 0.54 µs per draw, 45% of what remains. Logged
as F9.

Six tests in `unit_test/test_random_state_capture.py`, including one that rewinds the generator
and reshuffles to prove the debug cheat still behaves.

### F9: `AddCounter` logs on every draw

`Random.AddCounter` builds an f-string and calls `Log.DebugSilent` on every single random
operation, whether or not the category is enabled. Cheap to fix by checking whether the category is
live before formatting.

**Rejected 2026-08-10, after measuring it properly.** Two things were wrong with the case above.

The 0.54 µs was the whole wrapper, `Random.Shuffle` minus a raw `numpy.random.shuffle`, attributed
to logging. Broken down per call, `AddCounter` itself is 0.312 µs, and the largest single piece is
not the f-string:

| component | µs/call |
| --- | --- |
| `from engine.log import Log`, function-local | 0.148 |
| the f-string | 0.056 |
| `Log.DebugSilent` call | 0.031 |
| counter increment | 0.043 |
| category membership test | 0.010 |
| **`AddCounter` as written** | **0.312** |
| **with import and format behind the category check** | **0.068** |

The fix works, 4.6× on the function. It is still not worth making. `AddCounter` has exactly three
callers, all inside `Random` itself, so it runs once per draw, and F11 established that a game
makes 2 draws at solo setup and 6 at four players. The saving across a whole game is measured in
microseconds.

The import is function-local for a reason, incidentally, so nobody should hoist it later thinking
it is an oversight: `engine.log/__init__` imports `notify`, which imports `engine.lib`, so a
module-level import in `engine/lib/random.py` closes a cycle. Guarding it is the only cheap option.

We had already told irefrixs this was worth doing, in U8. The comment on issue #4 was edited on
2026-08-10 to correct the figure and withdraw the suggestion.

### F3: Two RNG backends, one save format

✓ VERIFIED by execution. `DISABLE_NUMPY_RANDOM` (default `False`) switches between
`numpy.random` and the bundled `engine/lib/mt19937.py`. Same seed (12345), same 10-element list:

```
bundled mt19937 : [3, 8, 9, 0, 4, 5, 7, 2, 1, 6]
numpy.random    : [0, 7, 3, 9, 6, 4, 1, 8, 5, 2]
```

They produce **different sequences from the same seed**. Since the save
file is an input log replayed through game logic, a scene recorded under one setting cannot be
faithfully replayed under the other — it will silently diverge into a different game.

Compounding: the numpy path uses numpy's **process-global** RNG. Any other code touching
`numpy.random` breaks replay determinism.

**Fixed** on `pr/rng-backend-determinism`, 3 commits, 151 insertions.

Scenes now carry an `rng` metadata field. `GameSetup` stamps it on a game being created and calls
`Random.CheckSceneBackend` before seeding a recorded one, asserting on a mismatch with a message
naming the flag value needed to load the file. Verified end to end against a real game:

| Case | Result |
| --- | --- |
| new game | `scene.rng == 'numpy'`, stamped at setup |
| scene claiming the other backend | `AssertionError`, refused |
| scene with no recorded backend | loads, stays unstamped |

**Superseded in part by F10.** The middle row no longer holds: the two current backends produce the
same sequence, so a scene recorded under either loads under either. What gets refused now is the
retired pre-F10 generator, and the check reads "can this build reproduce that sequence" rather than
"does the name match". The stamp, the plumbing and the traps below are unchanged.

Legacy scenes deliberately keep loading. There is no way to know which generator produced them,
and guessing would bake a false claim into the next save, so they carry the same risk as before.

Two implementation traps worth remembering. `GameSetup` calls `state.ResetStartState()` early, so
`start_state.is_new` has to be read before that line or it is always false. And keying the stamp
on `seed == -1` is wrong, because a new game started with an explicit seed takes the other branch
and never gets recorded.

Nine tests in `unit_test/test_rng_backend.py`. One of them used to pin the premise that the two
backends disagree, so the guard could not quietly become pointless. F10 removed the premise
instead, so that test now pins the opposite.

Both halves are now closed. F10 made the two backends produce the same sequence, so this change no
longer has to make divergence loud, and F11 took the process-global numpy path off the default, so
other code touching `numpy.random` can no longer perturb replay. The exposure returns for anyone
who sets `disable_numpy_random` back to false.

**Upstream context, 2026-08-10.** irefrixs confirmed the bundled backend was always meant to
reproduce numpy's sequence and never did, and that numpy is canonical because every existing save
encodes it. Eliminating the divergence, rather than reporting it, is the direction he wants, and a
candidate implementation exists that we measured as numpy-exact for shuffle and choice. See
[§0](#what-his-rng-answer-changes-f3) for the audit and the one method that does not match.

### F10: the bundled generator is right, its consumption layer is wrong

✓ VERIFIED by execution, `tools/rng_parity_check.py --bundled`. `engine/lib/mt19937.py` produces
**numpy's exact stream**: the same 624-word state after seeding for 300 seeds, and the same raw
words for 450,000 draws. F3 read as "the two backends disagree," which is true, but the cause is
not the Mersenne Twister. It is the two functions that turn words into game decisions.

| Function | What it does | What numpy does |
| --- | --- | --- |
| `randint` (line 64) | `int(random()/(1/(b-a)) + a)`, scaling a float from one word | masked rejection on the raw words, so the draw count varies |
| `shuffle` (line 69) | `10 * len(X)` random transpositions, `20n` draws | Fisher-Yates downward, `n - 1` draws |

`choice` and `choice_one` inherit the error through `randint`. Fixing the three functions to match
numpy is roughly 40 lines and closes the divergence rather than reporting it, which is the
direction irefrixs asked for in issue #4. The parity harness already exists, so the fix is
gated by a measurement rather than by inspection.

Preferred to vendoring the `mggarofalo` implementation. Ours needed a smaller change than that
file does (its `ChooseWithoutReplacement` is wrong for our purposes too, see §0), and adopting
third-party code while U5 is unresolved would add a licensing question to a fix that does not need
one.

**Fixed 2026-08-10**, 3 files. `randbelow` does numpy's masked rejection on the raw words,
`shuffle` is Fisher-Yates downward, and `choice(replace=False)` is a full shuffle truncated to `k`.
`randint` now delegates to `randbelow`, which is what fixes `choice_one` for free. The float
`random()` stays, unused, with a comment recording that scaling it was the original bug.

**The stamp is versioned**, per option 2 below. `BACKEND_BUNDLED` is now `mt19937-v2` and the old
`mt19937` is kept as `BACKEND_BUNDLED_RETIRED`.

`CheckSceneBackend` changed shape as a result. It used to ask "does the recorded backend match the
running one." That question is now meaningless, because the two current backends are
interchangeable, so it asks "can this build reproduce the recorded sequence" instead:

| Recorded value | Result |
| --- | --- |
| `numpy` or `mt19937-v2` | loads, either way, whichever backend is configured |
| `mt19937` (retired) | refused, with a message saying no config flag brings that sequence back |
| unknown value | refused |
| empty (pre-F3 scene) | loads, unchanged |

Verified four ways:

- `tools/rng_parity_check.py --bundled` passes all six checks it previously failed five of.
- 11 unit tests in `unit_test/test_rng_numpy_parity.py`, covering each operation the engine
  dispatches, object lists rather than ints, and 54 interleaved operations off one stream, which is
  what catches an operation consuming the wrong number of draws.
- End to end through the engine, no replay file involved: `rhino` + `spider_man` at seed 42 deals
  the identical six-card opening hand on both backends, and a different seed deals a different
  hand, so the comparison is not vacuous.
- Every scene in `replays/` is stamped `numpy`, so nothing on disk here is invalidated.

**F3's premise test had to be inverted.** It pinned that the two backends disagree, so the guard
could not quietly become pointless. That premise is what F10 removes, so the test now pins the
opposite, and `TestBackendsDisagree` is `TestBackendsAgree`.

**Second-order effect, and the reason this was not purely additive.** F3 stamps scenes with the
backend that recorded them, so a scene carrying `rng: "mt19937"` asserted it could be replayed
under the bundled path. Changing that path's sequence silently invalidates the promise: the stamp
still matches, the game diverges anyway. Two ways out:

1. Accept the break. irefrixs says every real save uses numpy, and the bundled path was "never
   used," so the affected population is probably empty outside our own test scenes.
2. Version the stamp, `mt19937-v2`, and refuse the old value. Honest, and cheap, since
   `CheckSceneBackend` already refuses on mismatch.

Q chose option 2 on 2026-08-10. It costs one string and keeps F3's guarantee intact.

### F11: the fork runs without numpy

Decided and implemented 2026-08-10, once F10 made the two backends interchangeable.
`disable_numpy_random` now defaults to `true`, so `engine/lib/random.py` never imports numpy on a
normal run.

**What it costs.** Measured per call through the `Random.*` wrappers, on lists of card objects
because that is what a deck is:

| operation | numpy | bundled | ratio |
| --- | --- | --- | --- |
| shuffle 52 objects | 1.19 µs | 41.11 µs | 34.5× slower |
| shuffle 30 objects | 0.95 µs | 22.93 µs | 24.0× slower |
| `RandomChoice2`, 6 of 52 | 6.04 µs | 42.12 µs | 7.0× slower |
| `RandomChoice` of 52 | 5.36 µs | 1.22 µs | **4.4× faster** |

The last row is F2 seen from the other side: `numpy.random.choice` rebuilds an object array from
the Python list on every call, so numpy loses the moment it is not handed an array.

**Why the slowdown does not matter.** The engine barely draws. ✓ VERIFIED by counting
`Random.counter` through a real `GameSetup`: 2 draws solo, 4 at two players, 6 at four. Shuffling
is a per-deck event, not a per-decision one. Even at a pessimistic 500 shuffles across a long
four-player game the bundled path costs about 20 ms more in total. Game setup wall time is
identical on both backends once caches are warm, 46 ms against 47 ms, and the first-run figure of
214 ms that looked like a backend difference was cache warmth, confirmed by alternating them.

**What it buys.** No 10 MB dependency, and it closes the half of F3 that was still open: the numpy
path uses numpy's *process-global* state, so any other code touching `numpy.random` perturbs
replay. The bundled generator cannot be reached that way.

✓ VERIFIED end to end with numpy made unimportable by a `sys.meta_path` blocker: a full game sets
up, `numpy` never enters `sys.modules`, and the opening hand is identical to the numpy-backed one
at the same seed.

numpy stays in `requirements.txt`. `unit_test/test_rng_numpy_parity.py` compares against it on
every run, which is exactly what would catch the bundled generator drifting. It is a test
dependency now rather than a runtime one.

**The flip needed a fix first, tracked as F12, and this is the part worth remembering.**
`Random.Undo` had a bare
`pass` on the bundled branch, and `PushState` was only called inside the numpy branches. Switching
the default would have turned the `Unshuffle` cheat at `cheat_cmd_helper.py:390` into a silent
no-op. Not a crash, not an error, just a debug command that stopped doing anything. The bundled
generator now has `GetState`/`SetState`, `PushState` records for either backend behind the same
`enable_random_undo` flag, and each snapshot is tagged with the backend that produced it so
restoring one into the other asserts instead of corrupting the generator.

### F4: `World.LoadFromJson` is dead and non-functional

✓ VERIFIED. Zero callers anywhere in the repo. It also cannot run:

- Line 127: `for i in (0, 1, 2, 3)[:world_descriptor.players]`: slices a tuple by
  `world_descriptor.players`, which is `List[PlayerDescriptor]`
  (`game/render/descriptor/world.py:61`). `TypeError` on entry.
- Lines 136 and 139: `CardFactory.GenerateCard(card.card_id, self.players[0].player_deck, self)`
  uses `players[0]` inside a loop over `i` — every player's cards would go to player 0.

Chesterton's fence applies, but the fence is provably not holding anything up: it has no callers
and raises immediately. Delete it, or fix and test it.

### F5: Saving a puzzle corrupts the in-memory replay log

`Scene.UpdateInputs` assigns `self.inputs = game.controller_manager.replay.history_inputs` — a
reference, not a copy. `PrepareSave` then does, for puzzles:

```python
for input in data.inputs:
    delattr(input, 'step'); delattr(input, 'event'); delattr(input, 'crc')
```

That mutates the **live** replay log objects. `Scene.Save` guards with an early
`if self.is_puzzle: return False`, but `game/game_run/game_session.py:133` calls `PrepareSave`
directly and bypasses that guard. Consequences: continuing to play after a puzzle save works on
stripped inputs, and a **second** save raises `AttributeError` on the already-deleted attribute.

**Fixed** on `pr/puzzle-save-mutation`. The list is copied before stripping and already-absent
attributes are skipped, so the strip is idempotent. Four tests: two that failed before the change
(the live log reported `step == -1`, and a second save raised `AttributeError`), plus two pinning
behaviour that had to survive, that the saved copy is still stripped and that a normal scene is
untouched.

Note for anyone cherry-picking: this conflicts with F3, which inserts the `rng` stamp immediately
above the same block in `PrepareSave`. Both belong; keep the stamp and drop the now-unused
`data = self`.

### F6: The command blocklist blocks only the naive case

✓ VERIFIED by execution against `IsCommandSafe`:

| Payload | Result |
| --- | --- |
| `import os` | blocked |
| `__import__('os').getcwd()` | **passes** |
| `import importlib` | **passes** |
| `open('/etc/hosts').read()` | **passes** |
| `().__class__.__base__.__subclasses__()` | **passes** |
| `getattr(__builtins__,'ev'+'al')('1+1')` | **passes** |
| `compile('x=1','<s>','exec')` | **passes** |

Scope matters: `IsCommandSafe` is called from **one** site — the debug console
(`game/world/cheat/cheat_cmd_helper.py:459`). Card scripts under `cards/pack/**` are imported as
ordinary Python modules with **no validation at all**.

So the honest security model is "card scripts are fully trusted," exactly as the README warns.
The problem is that `command_validation.py` implies a protection that does not exist.

**Correction, 2026-08-10. "The debug console" is an HTTP endpoint, and the original proposal to
delete the blocklist was written without knowing that.** ✓ VERIFIED by reading the whole chain:

```
GET /debug?<python>
  -> handle_debug_command            engine/device/web/server/server_sync.py:20
  -> Unquote(request.rel_url.query_string)
  -> console.SetCommand              engine/console/console.py:49
  -> RunCheat                        game/world/cheat/cheat_cmd_helper.py:411
  -> IsCommandSafe                   the blocklist, one payload in eight
  -> exec(cmd)                       game/world/cheat/cheat_cmd_helper.py:481
```

The route is registered through `AddAwaitGetSecurity`, which sounds sufficient and is not.
`IsAuthenticate` (`engine/network/web_server.py:81`) returns `True` for **everyone** when no
password is configured, and the shipped `launch.json` carries `"password": ""`. So in the default
configuration the wrapper is a no-op and the blocklist is the only thing in the path.

What keeps this from being an open door is the bind address: `server_addresses` defaults to
`127.0.0.1:2345` (`engine/device/manager/web/manager.py:11`). The exposure appears exactly when
someone sets `ip` to reach the LAN, which is what the devlog's 4-player mode asks people to do.
Host a game for friends without setting a password and any host that can reach the port has
arbitrary code execution.

**Fixed 2026-08-10.** `/debug` is registered through a new `AddAwaitGetDebugSecurity`, which
requires the request to come from this machine **or** to present a password that is actually
configured. `IsLoopback` fails closed: no peer address, an unparseable one, or a proxy's address
all count as remote. Refusal is a 403 rather than the login page, because the caller is a script.
Six tests in `unit_test/test_debug_endpoint_gate.py`, one of which pins the precondition that
`IsAuthenticate` passes a LAN client, so the gate cannot quietly be rewritten in terms of it.

The blocklist stays, with its security framing removed. It catches a typo; it is not a boundary,
and the file name was most of why anyone believed otherwise.

| ID | Item | Status |
| --- | --- | --- |
| F6a | Gate `/debug` on loopback or a real password | **DONE**, `pr/gate-debug-endpoint`, reported upstream as [issue #7](https://github.com/irefrixs/marvel-lcg/issues/7) (U10). **Answered 2026-08-18, conceded and declined**, see below |
| F6b | Rename `command_validation.py` and its docstring so it stops implying a security control | PROPOSED. Upstream now agrees with the premise in writing, *"a whitelist would be safer than a blacklist,"* so this is a fork-only rename with no risk of contradicting him |
| F6c | The same no-password-means-authenticated hole applies to **every** route using `IsAuthenticate`, not just `/debug` | **DECIDED 2026-08-10: do not fail closed.** Re-rated Medium. Fix is an auto-generated password on a non-loopback bind, deferred as a feature |

**Upstream's answer, 2026-08-18.** He conceded the technical point without argument: *"Yes, I
agree that `IsCommandSafe` is not a strong security boundary and that a whitelist would be safer
than a blacklist."* He then argued the exposure does not exist in the build people actually run.
The itch.io release does not allow debug or custom script execution at all; only the separate
[`-script` build](https://irefrixs.itch.io/marvel-lcg-scripts) runs Python, and that requires the
host to set `cards_json_custom_file` or `cards_json_custom_files` when launching. His conclusion:
*"we don't consider the current setup to be a strong security boundary for arbitrary
configurations,"* the project is sunset, and *"you're welcome to make the changes you suggested in
your fork."*

Two things that answer does not touch, and they are the two the report was about. It says nothing
about `IsAuthenticate` returning `True` for every caller when no password is set, which is F6c and
the actual reason the blocklist was load-bearing. And it is about the packaged itch.io build, not
this source tree, which is what anyone running from a clone is executing. So the gate stays, and
F6c stays open as a fork item rather than a shared one.

---

## J. Second-pass defect audit (2026-08-09)

Deeper sweep after §F, targeting areas the first pass skipped: exception handling, concurrency,
web auth, save integrity. Ordered by how much they matter.

| ID | Finding | Location | Severity | Status |
| --- | --- | --- | --- | --- |
| J1 | Bare `except:` can silently drop a card ability | `game/card/face/effect/face_effect.py:55` | Medium (see measurement) | **DONE**, `pr/narrow-effect-filter-except` |
| J2 | `/authenticate` issues a cookie without checking the password, and 500s on a malformed body. **Not a bypass**, ✓ VERIFIED: the check happens later in `IsAuthenticate` and a wrong guess is refused | `engine/network/web_server.py:254` | Medium | **DONE**: verifies, 401/400, constant-time compare, warns when serving off-machine with no password |
| F6c | `IsAuthenticate` returns `True` for every caller when no password is configured, which is the shipped default, so every `*Security` route is open to anyone who can reach the port. The real exposure behind J2 | `engine/network/web_server.py:81` | Medium, was High | **DECIDED**, not failing closed. See the F6 section for the reasoning and the auto-generated-password design that replaces it |
| J3 | Save checksums default to ignored, and load proceeds on mismatch | `engine/lib/json.py:179` | Medium | **DONE** for the bug: `"Restrict"` now refuses a mismatch. Whether scenes should move from `"Warn"` to `"Restrict"` is a decision, see below |
| J4 | `JobManager.Simultaneous` is a sequential loop | `engine/job/manager.py:76` | Medium | PROPOSED |
| J5 | `RemoveJob` check-then-act race from worker threads | `engine/job/manager.py:43` | Low | PROPOSED |
| J6 | 619 `assert`s enforce game rules; `python -O` deletes them | engine-wide | Low, latent | **DONE**, `Engine.Initialize` refuses to start with assertions disabled |
| J7 | Mutable default arguments (10 sites) | various | Low, latent | PROPOSED |
| J8 | **Clicking Cancel on the End Phase prompt raises.** Reproduced in a real browser game. | `engine/controller/controller.py:295` | Medium, user-reachable | **DONE**, the rule is now `Controller.CanDecline` and a client that breaks it is refused rather than crashing |
| J12 | **The image catch-all answered 200 for every path nothing else claimed.** `r'/{path:.+}'` is registered last and sent everything to `handle_image_request`, which returns `Cache.LoadImage`'s placeholder. `LoadImage` never fails, so a missing or misspelled route came back as a 254x352 grey JPEG with a 200 rather than an error. That is what hid J13 for an unknown length of time, and it would hide the next one. Fixed by having the game register every card id with the cache (`Cache.RegisterImageName`, called from `CardsDB.Initialize`, mirroring the existing `SetLinkPic` handoff so `engine/` still does not import `cards/`) and gating the route on `Cache.CanLoadImage`: a registered name, something already cached or on disk, or a card-id-shaped name that could still download. Everything else is 404. Cards we ship no art for keep the placeholder. The editor is unaffected, it has its own `handle_image` calling `LoadImage` directly | `engine/device/web/server/server_files.py:61`, `engine/file/cache.py:60` | Medium, masks other defects | **DONE**. ✓ VERIFIED: card art, backs, status and challenge cards serve unchanged; `2425_boss_rush` still degrades to the placeholder; unknown paths 404; New Game screen loads all 322 images; 76 tests pass |
| J13 | **The game over "Save replay" button saved nothing and reported success.** `Command.saveLocal` fetches `save_local` (`public/js/marvel/command.ts:27`, wired to the button at `public/js/marvel/message.ts:27`) and nothing served that path, so it fell through J12 and got a placeholder JPEG with a 200. The client did not check the status, called `.text()` on the image, and showed "Your save file has been saved in: " followed by the JPEG bytes. ✓ VERIFIED by playing a real game: statistics were written at game over but no file existed in `replays/`, the repo root, or the browser's download folder. Auto-save was separately off, which is the default, so nothing else caught it. Fixed by adding the handler the client was always calling, saving through `session.SaveScene(delete_old=False)` to match the `/save` debug command, 409 when there is no scene rather than tripping the assert in `SaveScene`, and checking `response.ok` on the client | `engine/device/web/server/server_new_game.py:58` | Medium, silent data loss | **DONE**, commit `3adbad1`, cut for upstream as `pr/save-replay-handler` and reported as [issue #8](https://github.com/irefrixs/marvel-lcg/issues/8) (U11). **Confirmed upstream 2026-08-18**, see below |
| J14 | **`IsPortAvailable` binds without `SO_REUSEADDR`, so a restart fails while a browser still holds the port.** `s.bind((address, port))` with a default socket, and the caller asserts on the result (`engine/device/manager/web/manager.py:61`). A browser tab left open on the game keeps keep-alive connections whose orphaned server-side sockets pin port 2345 after the process dies, so relaunching within that window dies with `AssertionError: ip='127.0.0.1', port=2345` and no explanation. ✓ VERIFIED the hard way on 2026-08-10: four consecutive failed restarts, `netstat` showing no listener, a raw `bind()` in a separate process succeeding once the tab was navigated away. Initially misdiagnosed as the port being slow to release. Two parts worth fixing: set `SO_REUSEADDR` on the probe socket and on the real bind, and make the assert say what is holding the port | `engine/network/net_lib.py:53-68` | Low, developer-facing | **DONE**. One correction to the fix as written above: the real bind never needed touching. `asyncio.create_server`, which opens the actual listener, already sets `SO_REUSEADDR` on POSIX by default, so only the probe lacked it. That is the whole defect, the probe was stricter than the bind it was standing in for and refused a port the server would have taken. `WhyPortUnavailable` replaces the bool and returns the OS error, the bare `except` narrows to `OSError` so a bad address stops being reported as a busy port, and the assert now names the errno and the two usual causes. ✓ VERIFIED by a paired A/B at the same instant on the same port, one second after killing the server with a browser tab still open: the old probe answered `Address already in use (errno 48)`, the new one answered bindable, and an immediate restart then came up and served 200. 5 tests, 3 of which fail against the old probe, the other 2 being regression guards that a live listener is still refused and a free port still accepted |
| J15 | **A failed art download becomes permanent, and hides a card that is changing the rules.** `LoadImage` ends at `ImageCreator.CreateNoImage` and then `Cache.SetCache(file_name, image_data)`, so the generated placeholder is cached in memory under the card's own name for the life of the process. Nothing retries, because the next call returns from `Cache.cache` at the top of the function. One 3-second timeout and that card stays blank for the whole session. Worse, `if SAVE_EMPTY_IMAGE.value and not is_time_out` writes the placeholder to disk as `{card_id}.jpg`: only `requests.exceptions.Timeout` sets `is_time_out`, so a CDN 404, a DNS failure or a reset connection all persist a fake JPEG that is byte-indistinguishable from real art, and `FindImageFile` then reports the card satisfied forever. ✓ VERIFIED: `assets/cache/90001.jpg` is byte-identical to the generated placeholder (`cdeafa0e…`, 2035 bytes) while `assets/pics/90001.jpg` holds the real 20 KB art, so the write branch has already fired here and only the folder search order hides it | `engine/file/cache.py:186-197` | Medium, user-reachable | **DONE**. A definitive miss is recorded as a `{name}.no_art` marker, which the three lookups ignore because they only read `.webp`/`.jpg`/`.png`; a transient failure is recorded nowhere and retried, capped per name, with a run-wide give-up after 10 consecutive failures so a dead network is not retried per card; timeout 3s to 10s. ✓ VERIFIED: 8 tests, all 8 confirmed to fail against the old policy re-applied to the same file |
| J16 | **`DrawText` cannot draw text, so `show_image_text` is a no-op and every placeholder is a blank colour swatch.** The loop that appends to `lines` is commented out (it called `draw.textsize`, removed in Pillow 10), `current_line` is initialised to `""` and never reassigned, so `if current_line` is false, `lines` stays empty and the draw loop at the end never runs. `words` is computed and unused. Every caller gets an unmodified image back. `launch.json` ships `show_image_text: true`, so the intended behaviour is a card rendered as its name, type and text, which would make J15 self-explaining instead of a mystery | `engine/lib/image_creator.py:96-122` | Low alone, Medium with J15 | **DONE**. Ported the loop to `draw.textlength`, and kept source newlines as line breaks since card text carries them and `split()` on all whitespace lost them. ✓ VERIFIED: `01153` now renders its name, type and full text; 4 new tests, each confirmed to fail with the draw suppressed again; safe suite 80 tests |
| J17 | **The version guard answers image routes with an HTML page at 200, and that page is then cached for a year.** `AddNonAwaitGetSecurity` serves images and `save_local`, never pages, but on a stale or missing `app_version` cookie it returns `LoadHtmlCleanCache()`. That goes through `ReadFile`, which stamps `HeaderCache` on release builds, and `build.py:5` sets `release = True` unconditionally. So one image request made during a version mismatch puts 4,483 bytes of HTML into the browser cache under a card's own URL with `max-age=31536000`, and nothing ever asks again. Restarting the server cannot help, because the server is correct. ✓ VERIFIED against the running server: `GET /stunned` with a stale cookie returns 200 `text/html` 4,483 bytes, the same URL with a current cookie returns 200 `image/jpeg` 6,192 bytes, and both carry `public, max-age=31536000`. Found from play, as a Stunned card that would not draw and stayed blank across new games and server restarts. This is J15 on the other side of the wire, a transient failure made permanent by a cache, and J12/J13 in shape, a route answering 200 with something that is not what was asked for | `engine/network/web_server.py:60`, `engine/network/web_server.py:50-55` | Medium, user-reachable | **DONE**, commit `03cbed4`. Guard pages go out `no-store`, and the resource routes refuse with 401 or 409 and a plain-text body instead of a page. 5 tests, each confirmed to fail against the old headers. ✓ VERIFIED against a running server on 2026-08-13: `/stunned` with a stale cookie now answers `409 Conflict`, `Cache-Control: no-store`, `text/plain`, "client version does not match the server", and with no cookie at all the same; with a current cookie it still serves the 6,192-byte JPEG. The recovery path is intact, `/` with a stale cookie still returns the Version Mismatch page at 200, now under `no-store` so it cannot outlive the mismatch it reports |
| J18 | **The only route that issues the `app_version` cookie is cached for a year, so a browser that loses the cookie can never get it back and is locked out of the game.** `handle_get_version` is the sole `set_cookie('app_version', ...)` in the codebase (`web_server.py:328`), and the same response is deliberately sent as `image/jpeg` with `HeaderCache`, commented "Hack, make browser treat it as images and store in cache". Once that response is in the browser cache, every later fetch is served locally, `Set-Cookie` never runs, and `IsVersionMatch` fails at `web_server.py:187` on the missing cookie. Every guarded route then answers with the mismatch page. The route itself is fine, registered `need_auth=False, need_check_version=False`, so nothing on the server refuses: the client simply stops asking. **The recovery path in the UI does not recover.** `public/clean_cache.html` binds "Try Reloading (Bypass Cache)" to `window.location.reload(true)` alone, with the `get_version()` call commented out directly above it, and `reload`'s force parameter is non-standard and ignored by current browsers, so the button reloads into the same wall forever. ✓ VERIFIED 2026-08-16 in Chrome against the running server: a fresh tab on `127.0.0.1:2345` served the Version Mismatch page, and its load-time `/get_version` fetch reported `transferSize: 0` with `encodedBodySize: 10`, a cache hit. A forced `fetch('/get_version', {cache:'reload'})` returned 200 `0.5.9.201r`, after which the guarded CSS route returned real CSS instead of the guard page, and a hard reload loaded the launcher. Same root as J17, `build.py:5` forcing `release = True` and stamping a year of caching on a response that carries state, but the other half of it: J17 cached the refusal, this caches the thing that lifts the refusal | `engine/network/web_server.py:324-334`, `public/clean_cache.html` | Medium, user-reachable, no working recovery in the UI | **DONE**, both halves. The route goes out `no-store` and drops the `image/jpeg` pretence, which only ever existed to buy the caching, so it is plain text again as it was before the hack. The button awaits a real `get_version()` instead of `reload(true)`, and `get_version` itself fetches with `cache: 'reload'`, which matters for the browsers already holding the old year-long copy: the server change only helps a client that has not stored it yet. 3 tests. Only one of the three fails against the old code, the `no-store` assertion, with `'public, max-age=31536000' != 'no-store'`; the other two pin the cookie still being issued and the route still answering a client that has no cookie, which the old code also satisfied. They are regression guards, not defect tests. ✓ VERIFIED against a restarted server: `/get_version` answers 200 `text/plain` with `Cache-Control: no-store` and `Set-Cookie: app_version=0.5.9.201r; Max-Age=31536000; Path=/`, the served `clean_cache.html` handler is `async` and awaits `get_version()` with no `reload(true)` left in it, and the launcher loads with no guard page. Safe suite 109 tests |
| J19 | **v2: an attacking card flies past its target, by more the further across the board the target sits.** `animation_attack_thwart` reads the target's `--x`/`--y` through `getOffset` and writes them into `translate3d(${nx}px, ${ny}px, 10px)` (`public/js/marvel/card_animation.ts:303`), overriding the card's own transform. Those are scene coordinates on the 1920x1080 canvas the board was authored against, not pixels. v1 multiplies them by `1px` and scales the whole camera, so raw pixels were exactly right. v2 keeps the coordinates and changes the unit to `--sux` across and `--su` down, each a fraction of the container, so the same string overshoots. ✓ VERIFIED in Chrome on a 1512x827 board by probing the three real attack pairings with cards injected into `#player-all-area-hero`, `#area-villain` and `#player-all-engaged-minions`: the attacker's centre missed the target's by 191, 149 and 85 px against a card 97 px wide, and the unit-correct string hit 0,0 in all three. The same probe on v1 gives 0,0 for both strings. Found from play, reported as an offset | `public/js/marvel/card_animation.ts:303` | Medium, cosmetic but misleading: the animation is how you see what attacked what | **DONE**. The translate is now `calc(${nx} * var(--sux, 1px))` and `calc(${ny} * var(--su, 1px))`. The fallback is what makes one string right in both layouts, since v1 defines neither variable, and it also protects any page that loads `card.css` without the v2 scene. `10px` on the z axis stays literal because `--t-z` is `calc(var(--z) * 1px)` in both. ✓ VERIFIED by the probe above and by a v1 regression run |
| J20 | **v2: `#scene .deck` positions the pile container, so every card in a deck is offset twice and lands off the board.** `layout.css:117-120` sets `left: calc(var(--x) * var(--sux))` and `top: calc(var(--y) * var(--su))` on the `.deck` element. v1 does the opposite on purpose: `pos-deck.css` pins `.deck { left: 0; top: 0 }` and lets each card inside carry an absolute scene coordinate in its own transform. An id beats a class, so the v2 rule wins and the container's offset is added to the card's. ✓ VERIFIED in Chrome: `#player-0-player-deck` computes `left: 15.75px, top: 742.768px`, the card inside it computes the identical translate, and the card therefore renders at y = 1485.5 on a board 827 px tall. The same element in v1 sits at top 0. The rule looks like a conversion of the wrong v1 line: every other `calc(var(--x) * 1px)` in v1 is on a pseudo-element, and the debug outline it most resembles, `pos-deck.css:112-119`, is separately and correctly restated later in `layout.css` as `#scene .deck::before`. The rule read `--x`/`--y` on a `.deck` as the pile's own coordinates. They are not: `pos-deck.css` pins `.deck { top: 0; left: 0 }` and then sets `--x`/`--y` per pile as the value its **cards** inherit, so `.player-deck { --y: 970 }` says where that deck's cards go, not where the box goes. The cards consume the same two variables through `#scene .card`, so positioning the box applied the coordinate twice | `public/css/marvel2/layout.css:117-120` | Medium, user-visible | **DONE**. Rule deleted, with a comment in its place recording what `--x`/`--y` on a pile actually mean. ✓ VERIFIED across seven piles: every one is back to `left: 0; top: 0`, and the card inside each now renders where v1 renders it once converted, the player deck at y 742.8 on an 827px board instead of 1485.5. **It also fixes the count labels**, which were double-offset by the same rule: `#area-advanced` and `#nemesis-pool` are the two the part-two comment says disappear off the right, and converting the label rule was only half of why. All four labels checked now land exactly where v1 puts them. One deliberate behaviour change beyond the piles: a clicked deck takes `top` from `.deck.clicked { top: unset }` in `deck.css`, which the deleted id rule was outranking, so the expanded browser was pinned at 742.8 and now resolves from flow the way v1 does. Both expanded decks measured fit the board |
| J21 | **v2: every card that activates drops a quarter of a card height and comes back, instead of growing on the spot.** `layout.css` carried `#scene .card.active, #scene .card.activating { --top: calc(var(--y) * var(--su) + var(--card-height) * .25) }` and an `.up` variant. Both formulas are real, both selectors were invented. v1 scopes every activation nudge to a pile (`.deck.player-deck .card.activating` and so on, `card-active.css:30-47`) and applies nothing at all to a card activating in play: `card-active.css:1-3` sets `--this-scale` and stops, and the growth comes from `card-face-image.css:57` scaling `.face .image`, an element inside the card, which never touches the card's own transform. So v1's card grows with its top edge where it was, and v2's dropped 33.7px first. `.card.active` and `.card.active.up` matched nothing in either layout: `ClassName.active_card` is `'activating'` and no `up` class exists in the client, so one rule was dead and the other over-applied. ✓ VERIFIED by probing an activating card in the hero, villain, ally and engaged-minion areas: v1 shifts 0px in all four, v2 shifted 33.69px, which is `--card-height * .25` exactly | `public/css/marvel2/layout.css:113-121` | Medium, user-visible on every activation | **DONE**. The invented rule is gone, with a comment in its place saying why there is no general one, so it does not come back. Deleting it would have left the piles short, so the two v1 pile rules the conversion had missed are restated: `encounter-deck`/`deck-top` (`--top: calc(var(--card-height) * .25)`, no `--y` term, which is v1's own arithmetic) and `player-discard-pile` added to the `--left` list, which v1 lists four selectors for and the conversion carried three. ✓ VERIFIED against v1 across five piles and four play areas: in play both layouts now shift 0, and all five pile shifts match v1 exactly once scaled. The card still grows, `--this-scale` goes 1 to 1.15 as before |
| J22 | **v2: a targeting line starts to the right of the card it comes from, and below it.** `UI.drawLine` mixes two spaces on one line: `const x1 = rectA.left + divA.offsetWidth / 2`. `getOffset` gives a scene coordinate and `offsetWidth` gives a layout measurement in real pixels. Under v1 those are the same unit so the sum is meaningful; under v2 the coordinate needs `--sux`/`--su` and the half-card does not, so the coordinate carried its whole unconverted remainder into the start point and the error grew with distance from the origin. The length and the angle are then computed from the mixed numbers as well, and in v2 the two axes no longer even share a unit, so the line was the wrong length and pointing slightly wrong. Predicted from reading while fixing J19, confirmed when it was reported from play | `public/js/marvel/ui.ts:371-378` | Medium, cosmetic but it is how you see what is targeting what | **DONE**. Only the coordinate is converted, through a new `Lib.client.sceneUnit()` that measures a scene unit in real pixels off a hidden probe, so the canvas size and the unit formula stay in `layout.css` alone and are not repeated in JS. It reads the used width via `getComputedStyle`, which ignores v1's camera transform where a rect would not, and keeps the fraction where `offsetWidth` would round it away. ✓ VERIFIED on three pairings in both layouts: v2 start and tip land within 0.12px of the two card centres with lengths matching to 0.01px, and v1 is exact at 0.00 with the unit measuring 1 on both axes, so the new line is arithmetically the old one there. The residual 0.12px in v2 is `offsetWidth` rounding 97.24 to 97 |
| J23 | **v2: `convertScenePosToWindowPos` has the same unit mistake, and `scene.ts` states it as fact.** `scene.ts` sets `Scene.scale = 1` for v2 with the comment *"v2 draws at 1:1, so scene coordinates are already screen pixels."* They are not: a unit is `--sux` across and `--su` down. The 1 is right in the narrow sense that there is no camera transform to divide out, but the reason given is the exact belief behind J19 and J22. `convertScenePosToWindowPos` computes `sceneX * Scene.scale + rect.left`, so under v2 it returns the raw coordinate, and `hover.ts:242-249` feeds it the revealed card's position to decide where the preview goes, along with `card_div.offsetWidth * Scene.scale` for the size. Expect the preview to pick its side from a position that drifts further out the further the card is from the origin | `public/js/marvel/scene.ts:56-61`, `public/js/marvel/hover.ts:242-249` | Low, the preview still appears, it just chooses badly | **DONE**. Two terms stand between a scene coordinate and a window pixel and each layout contributes to a different one, which is why one term alone looked right: v1 has unit 1 and scale 0.766, v2 has unit 0.7875/0.7657 and scale 1. The conversion multiplies by both now. ✓ VERIFIED against four card positions in both layouts by comparing the returned point with the card's own `getBoundingClientRect`: v2 was returning the raw coordinate, putting the hero card at 700,795 instead of 551,609, so 149px right and 186px low, and now matches to 0.01px; v1 matches exactly and the returned value is unchanged from the old line to 0.001px, so it is a no-op there. `getMousePositionInScene`, the exact inverse, is corrected the same way. Nothing calls it, and it is fixed rather than left because an inverse that disagrees with its forward function is a trap for whoever calls it first. The `scene.ts` comment is rewritten to say what the 1 does and does not mean |
| J24 | **v2: the hover preview can never switch sides, because the rects it tests against are all zero.** `HoverCard.onMouseMove` decides which of the two side panels to use by testing the hovered card against `HoverCard.rect_left`/`rect_right`, cached by `updateRect()`. That runs once in the class's static initialiser, before the panels are laid out, and its only other caller is `adjustSceneScale`, which v2 never runs because `Scene.init` returns early. ✓ VERIFIED in Chrome at 1512x827: under v1 `rect_left` is `left 90.7, top 109.2, 367.6x509.4` and matches the panel exactly; under v2 every field is 0 while the panel is in the identical place. A zero-size rect at the origin can never overlap, so `using_left` never flips and the preview stays on one side no matter which card is hovered. This is not a stale-cache bug, the value was never populated | `public/js/marvel/hover.ts:88-91`, `public/js/marvel/scene.ts:30-36` | Medium, the preview can cover the card you are reading | **DONE**. The v2 branch of `Scene.init` now registers the two measurements v1 got for free from `adjustSceneScale`: `DOMContentLoaded` and `resize`, both through `addEventListener` rather than `window.onresize =` so neither can quietly replace another handler. The panels are outside `#camera` and sized in `vh`, so there is no unit to convert; they only needed measuring once the layout exists. ✓ VERIFIED at 1512x827 with no manual intervention: the cached rects now match the panels on load, and driving `onMouseMove` with a card over each panel flips `using_left` false then true, where before it stayed true for both. The resize path is verified end to end by growing the panels with `hold-alt`, firing the event, and watching the cache follow 367.6 to 525.1 and back. v1 is untouched and still flips. **The first attempt at this was wrong and the way it was wrong is worth keeping:** it guarded the immediate call with `document.readyState === 'loading'`, but this module is `type="module"` and therefore deferred, so it executes at `'interactive'`, took the else branch, and measured too early to any effect. A listener added during `'interactive'` has not missed `DOMContentLoaded`, so the guard bought nothing and cost the fix. Registration is unconditional now, with an immediate call only for `'complete'`, which is reachable solely by a late dynamic import. Note also, pre-existing and shared with v1: `hold-alt` resizes the panels without firing `resize`, so the cache is stale while it is held |
| J25 | **v2: `--font-size-out` is frozen at its 16px fallback, so the chrome outside the board does not scale.** `adjustSceneScale` sets it to `--font-size * Scene.scale`, and v2 never runs it, so the static `16px` from `marvel.css:56` stands. ✓ VERIFIED at 1512x827: v1 computes `19.909px`, v2 reports `16px`, about 20% smaller, and v2's value does not move with the window at all. Consumers are the side bar, history log, prompts, `btn-ok`, `btn-options`, overlay and `res`. `layout.css` defines `--font-size: calc(26 * var(--su))` for inside the scene and has no equivalent for outside it | `public/js/marvel/scene.ts:136`, `public/css/marvel/marvel.css:56` | Low, cosmetic and consistent, just smaller | **DONE**, and stated in v2's own terms rather than ported. Q's call: no v1 dependencies. `#camera` is `100dvh` tall and the board takes every size from its block axis, so the chrome now takes the same block unit and scales with the board by construction. It cannot use `--su`, which is a container query unit belonging to `#camera`, because these elements are outside it; the canvas dimensions therefore moved from `#scene` to `:root`, where both the board and the chrome can see them, and the base size joined them as a unitless `--scene-font` so the 26 is written once instead of twice. `layout.css` is linked after `marvel.css`, so a `:root` rule there beats the 16px fallback on order at equal specificity. ✓ VERIFIED at 1512x827: the value resolves at the point of use to 19.9093px against an expected 19.9093, where it was frozen at 16px. The board is untouched by the constants moving, card 97.24x134.77 and a transform of 551.25/608.76, both exact, and the in-scene font still resolves to the same 19.9093. v1 is untouched, still set by `adjustSceneScale` as an inline style, with `layout.css` not loaded and `--scene-rows` absent from its root. The two now agree at any window at least 16:9, where v1's `min()` also picks the height, and differ only on a taller one, where v1 shrinks the chrome to the width and v2 does not, which is the same call the board itself makes |
| J26 | **v2: the expanded deck browser's vertical placement is a raw scene coordinate.** `deck.css:69-77` puts a clicked pile at `top: 185px` (encounter discard and deck-top) or `bottom: 150px` (everything else). Those are scene coordinates, shrunk by v1's camera to 141.7 and 114.9 real pixels at a 1512x827 window, and taken at face value by v2. `layout.css` converted the horizontal pair from the same rules, `left: 300` and `right: 150`, and left the vertical pair alone | `public/css/marvel/deck.css:69-77` | Low, cosmetic, the panel still fits | **DONE**. Both rules restated in `layout.css` beside the horizontal pair that was already there, against `--su` since these are block-axis insets. They are kept as two rules rather than merged because the specificities are load bearing: v1 lets `.deck.encounter-discard-pile.clicked` and `.deck-top.deck.clicked` (0,0,3,0) beat `.deck.clicked` (0,0,2,0), which is how a pile that opens downward from the top wins over the default of sitting on the bottom, and prefixing both with `#scene` raises them together and keeps that order. ✓ VERIFIED against v1 on three piles at 1512x827. v1 anchors the player deck 150 scene units off the bottom and the encounter deck and discard 185 off the top; v2 now resolves those to 114.86px and 141.66px, matching to 0.00, where before it took 150 and 185 as real pixels, so the panel moved 35.1px and 43.3px. The specificity order is intact in v2, the two encounter piles top-anchored and the player deck bottom-anchored, and all three fit the board. v1 cannot be affected: `layout.css` is linked only by `marvel2.html` |
| J27 | **The main scheme's threat readout clips at two digits either side.** `.info` is `overflow: hidden` and exactly as wide as the card, and the shared rule sizes the readout at `2 * var(--font-size)` with `.25` of letter spacing. That suits the three characters of "2/7" and not the five of "11/12", which measured 150.68px in a 126px box, so the last digit was cut through the middle | `public/css/marvel/game.css` | Reported from play by Q. Both layouts, since the rule is shared | **DONE** 2026-08-19. Breakdown of the 150.68: 116.3 glyphs, 23.2 letter spacing, 11.1 padding. Letter spacing is the part that grows with character count and was the biggest single contributor, but it is not enough alone, because the glyphs are 116.3 against 126 on their own. So the size came down too: `1.7 * var(--font-size)` with `.08` spacing measures 117.9, leaving 8px. All of it is in `--font-size`, so the headroom is a ratio and holds at any board size. Scoped to the two-number variant, which already had its own rule, so side schemes and the single-number case keep the larger size. Sized for five characters, the realistic worst case; six would still clip |
| J28 | **The "3D Render" setting does nothing, in two separate ways.** The setup page's checkbox is wired up correctly: `scene.html:1978` appends `&3d_scene` to the board URL and `settings.ts:24` reads it. Both consumers of the flag are then unreachable or broken. **(a) Inert under v2, which is the default.** `scene.ts:77` sits below the `if (Scene.isV2()) ... return` in `Scene.init`, and `scene.ts:152` is inside `adjustSceneScale`, which v2 never calls. So on the default layout the box is checked, the flag is true, and nothing reads it. **(b) The stylesheet has never loaded, in either layout.** `scene.ts:78` asks for `./css./marvel./scene-3d.css`. `Lib.loader.loadCSS` does no rewriting, it assigns `href` verbatim, and every other caller uses `./public/css/...`. That path is missing the `public/` segment and has `.` where `/` belongs twice. The file exists, at `public/css/marvel/scene-3d.css`, and there is no `css.` or `marvel.` directory and no server rewrite. So even under v1, where the flag is honoured, all that arrives is the `rotateX(20deg)` at `scene.ts:152` and a `scene-3d` body class with no rules behind it | `public/js/marvel/scene.ts:77-79,152`, `public/scene.html:1484,1978` | A setting the UI offers and the game ignores. Low harm, but it is the kind of thing that wastes someone's afternoon, and (b) is a one-character-class typo hiding a whole stylesheet | **DONE** 2026-08-19, both halves. The path is corrected to `./public/css/marvel/scene-3d.css` and v1's 3D works and looks deliberate: a perspective table with a horizon at the 20 degrees `scene.ts:152` has always applied. Dead since it was written. v2 gets its own tilt rather than that stylesheet, which is v1's and would reintroduce J19 through J26 wholesale. `Scene.init` adds a `scene-3d` class under v2 and `marvel2/layout.css` does the rest: perspective on `#camera`, `rotateX(8deg)` on `#scene`, origin 75%. Measured first, because a tilt costs room and `#camera` is `overflow: hidden`: it helps at the top, where the removed/nemesis/advanced pools already overhang by 103px untilted and only 72px at 8 degrees, and costs about 6px at the bottom, which is the hand and already overflows by design. `convertScenePosToWindowPos` now takes its origin from `#camera` under v2, since a tilted `#scene` reports a box moved -11px across and +22.9px down and would bias both `hover.ts` callers. ⚠ One trap worth keeping: the perspective was first written `calc(2600 * var(--su))` and silently did nothing, because `--su` is declared on `#scene` and `#camera` is its parent, so it is out of scope and the declaration is invalid. `perspective` fell back to `none` while everything else looked applied. Written in `dvh` now, the same substitution `--font-size-out` makes |
| J29 | **Landscape-printed cards are shown on their side in the setup screen.** Every card image the server sends is portrait, 710x1030, including the ones printed landscape (main schemes, both side scheme types, statuses, inserts), so they arrive lying on their side and something has to turn them back. The board does; the setup screen never did. Clicking a pack shows its scenario cards sideways underneath, and hovering one gives a sideways preview | `public/css/menu/set-detail.css`, `public/scene.html` | Reported from use by Q on Breakout and All Hail King Loki. 76 of 914 cached card images are landscape prints, so it is a class of card, not two | **DONE** 2026-08-19. The flag already existed and was simply not consulted here: `card_info.js:100` marks those five types and `card_preview.js:143` uses it, but only for the deck-editor preview. `const_card_dict` is published for the hover panel, which now reserves the transposed 448x320 box. ⚠ First version rotated the whole `#set-content` container, claiming that was safe because `scene.html` builds these from `data["schemes"][0]`. That is the third of three branches. The one above it reads `data["villain"][0]`, which despite the variable being named `scheme` is the VILLAIN, and villains are portrait. Most packs take that branch, so the Core Set and nearly everything else came out sideways. Caught by Q. Rotation is now per card, from the same `card_info.js` flag the preview uses, applied when the pack's cards are cloned in. Verified across three packs rather than one, which is what let the first version through. ⚠ The comment at `set-detail.css:252` had asserted the opposite, that all art is portrait so there is "no landscape case to handle", and both bugs follow from believing it. Checked against the SERVER, not the repo: `/07001a` is served 710x1030 portrait while `assets/cache/07001a.jpg` on disk is 1030x710 landscape. Reading the repo would have given the wrong answer. Extended 2026-08-19 to the deck editor and card viewer, which had the same bug: both load `preview.css` so their big preview was correct while every thumbnail behind it was sideways. Shared rule in `menu/style.css`, tagged where each page builds its card element. The replay list needs nothing (heroes and villains only, both portrait) and the board is separate (`--rotate-times`). ⚠ `.image-div` is itself a fixed 75x105, and an inline-block with an explicit size ignores its content, so the wrapper needs transposing as well as the image or rotated cards overlap their neighbours. ⚠ `.image-div img` is declared twice in `menu/style.css`, identically, at 307 and 325; the new rule is appended rather than folded into one of a pair. ⚠⚠ **The flag itself was wrong, found 2026-08-19 after Q reported modular sets still showing landscapes.** `card_info.js` matched on "EncounterSideScheme", which is not a type any card has; the real type is "SideScheme", 326 cards. So every encounter side scheme in the game was treated as portrait. Settled against `assets/cache`, whose originals keep their true orientation, unlike anything the server sends: of the 77 landscape files, 35 MainScheme, 37 SideScheme, 5 PlayerSideScheme and nothing else, so no other type may be added. The set grids (`#modular-sets`, `#encounter-sets`) also needed their own rule, being neither `.image-div img` nor `#set-content`; tagging alone left the class set with `rotate` computing to `none`. The dictionary race is fixed too: both sides sweep now, after `createSets()` and at the publish site, and `MarkLandscapeCards` toggles so whichever runs second is a no-op. Only scene needs it, since deck and cards render after awaiting the same load. Verified by simulating the race. ⚠ The image must be pinned to its portrait box before rotating, or the flex button stretches it to 140x100 first and the rotation lands back at portrait, distorted. `getBoundingClientRect` reports the post-transform box so it reads 140x100 either way and cannot detect this; it needs looking at |
| J30 | **v2 deleted the card's scale transition with a shorthand, and nobody noticed for a week.** `card-face-image.css:19-23` gives `.card .face .image` and its `::after` `transition: scale .8s cubic-bezier(0.19, 1, 0.22, 1), background-color .8s <same>`. That is what animates the 1.15x hover lift (`card.css:108-110`) and the activation pulse (`card-active.css:1-3`), both of which drive `--this-scale`, consumed at `card-face-image.css:56-57`. Then `cards.css:48-50` wrote `#scene .card .face .image { transition: box-shadow ... }` to animate the shadow it had just moved onto that element. `transition` is a shorthand, so it did not add `box-shadow` to the list, it replaced the list. Higher specificity and later in source, so it won outright | `public/css/marvel2/cards.css:48-50`, introduced by the N6 shadow work | Low individually, but it is the interaction the whole board's hover feedback runs through, and the failure is silent: every declaration involved is valid and nothing logs | **DONE** 2026-08-20, `public/css/marvel2/motion.css` section 3. ✓ VERIFIED in the browser before writing the fix, which is the only reason it was found: `getComputedStyle` on that element returns `scale, background-color` at `0.8s, 0.8s` under v1 and `box-shadow` at `0.3s linear` under v2. Since that commit a hovered card and an activating card have jumped to size under v2 with no transition at all, in both directions. The `::after` overlay escaped it, because `#scene .card .face .image` does not match `.card .face .image::after`, so that kept v1's 0.8s scale: the overlay has been easing while the art underneath it snapped. Fixed by restating the list whole, `::after` included, and removing the declaration from `cards.css` so one file owns `transition` for this element. ⚠ The general lesson is the shorthand, not this element. Any v2 override that declares `transition`, `background`, `font` or `border` on a box a v1 sheet already styled silently discards the rest of that shorthand's longhands, and the result still computes to something plausible. `transition` is the dangerous one here because the symptom is an absence of motion, which reads as a design choice |
| J31 | **The game log is black text on a dark grey panel, and hovering a card name makes it worse.** `history.css:8` sets `color: black` and `:14` sets `background-color: #333`, so the running record of what happened in the game is 1.66:1 on those two colours alone. `:30` then applies `opacity: .85` to the panel, and that is the real cause rather than the colour: `opacity` on a container fades everything inside it, so the panel was never translucent, the text was. Measured composited over the board, the log body reaches the eye at 1.53:1, against a 4.5:1 floor for text this size. Separately, `:64-66` gives `.log-card:hover` `background-color: silver`, which under any light foreground is 1.82:1 | `public/css/marvel/history.css`, shared by both layouts | Medium. Not a cosmetic complaint: the log is the only place that says what already happened, and the hover rule fires exactly when you are trying to identify a card | **DONE** 2026-08-20. The transparency moved into `background-color: rgba(51, 51, 51, .85)` and `opacity` is gone, so text, border and id chip all render at full strength. Body text is `#dcdce0` at 9.64:1, not pure white, which `marvel2/chrome.css` argues is the other dated tell. The id chip inherited its black from the panel and now states it, which is a restatement rather than a redesign: it was designed as black on slategray at 5.18:1 and the opacity was delivering 3.79:1. `.log-card:hover` is a translucent white instead of `silver`, lifting the background without touching the foreground. ✓ VERIFIED in a running game on both: log body 1.53:1 to 9.64:1, chip 3.79:1 to 5.18:1, panel `opacity` computing 1 with the fill still translucent, and stacking unchanged at `z-index: 200`. ⚠ The hover rule is shared with `#prompt-text`, whose text has always been white, so this has been destroying the contrast of the hovered card name in the prompt box since it was written, not just in the log. Verified there too: hovering "Peter Parker" measures 10.99:1 against 1.82:1 before. That is the same defect `marvel2/chrome.css` measured on the buttons, where hover threw the button's colour away and left the white label at 1.84:1, which makes three instances of one habit: signalling hover by lightening the fill under light text. The border or a translucent overlay does the same job for no contrast. ⚠ Fixed in the shared v1 file rather than as a `marvel2/` override, deliberately. Unreadable text is a defect rather than a reference look worth preserving, and the hover rule serves the prompt in both layouts. Second slice, 2026-08-21: `word-break: break-all` on `:7`, deferred above because Q scoped the first pass to contrast. It splits every word at whatever character reaches the edge, so the log wrapped like "the villa / in attacks". Now `overflow-wrap: anywhere`, which breaks only a word that cannot fit on a line of its own. ⚠ `anywhere` rather than `break-word`, and the difference matters here rather than being a coin toss. The text sits in the `1fr` track of `grid-template-columns: var(--width) 1fr`, and a grid track's automatic minimum is its content's min-content size. Only `anywhere` reduces that. `break-word` would wrap the glyphs but leave the intrinsic width alone, so one long token could still widen the column and push the panel out, which is the case `break-all` was presumably reaching for in the first place. ✓ VERIFIED on a narrowed panel with both cases present: ordinary prose now breaks only at spaces, an unbreakable 60-character identifier still breaks rather than overflowing, and `scrollWidth - clientWidth` is 0 so the grid did not widen |
| J32 | **The scrollbar styling is a web snippet with its `border-radius` lines dropped, and three scrolling pages never loaded it.** The whole file was `::-webkit-scrollbar { width: 10px }`, `::-webkit-scrollbar-track { box-shadow: inset 0 0 5px grey }` and `::-webkit-scrollbar-thumb { box-shadow: inset 0 0 5px black }`. Neither part is given a background, so what is left is an inner glow with no shape: on a dark panel a soft dark smudge on a soft grey smudge. No hover or active state, so nothing acknowledges you reaching for it. No `height`, so a horizontal scrollbar kept the browser default and did not match the vertical one beside it. `::-webkit-scrollbar-corner` unset, which the browser paints white, a bright square on a dark panel wherever both scrollbars appear. And it was linked only by `marvel.html` and `marvel2.html`, so the setup screen, the deck editor and the card viewer had the stock scrollbar | was `public/css/marvel/scrollbar.css`, now `public/css/scrollbar.css` | Low on its own. It is on this list because it is on every page and costs almost nothing to correct | **DONE** 2026-08-20. Track and thumb get real fills and a radius, the thumb is inset with a transparent border plus `background-clip: padding-box` so it reads as riding in the groove rather than filling it, and hover and active lift the same fill rather than swapping in a colour, which is the J31 lesson. `width` stays 10px deliberately: it is the gutter every scrolling box on the board is already laid out around and `#history-text` reserves it, so changing it would move text. ⚠ The interesting part is why the standard properties could not just be added alongside. ✓ VERIFIED in Chrome 151 on a probe: setting `scrollbar-color` on an element makes it ignore `::-webkit-scrollbar` outright and fall back to the platform scrollbar. The measured layout gutter goes 10px to 0, because macOS then supplies an overlay scrollbar that reserves no width and auto-hides, so adding it globally would have silently reflowed every scrolling box. `scrollbar-width: auto` alone leaves the webkit rules intact; `scrollbar-color` alone is enough to break them. The two are therefore split by capability rather than by sniffing a browser: `@supports not selector(::-webkit-scrollbar)` is false in Chrome and Safari and true in Firefox, which has had the stock scrollbar since the beginning. ⚠ The file moved out of `css/marvel/` because it is not board CSS and three of the pages that want it are not the board. `font-awesome.css` already sits at that level for the same reason. That is the part to object to if the placement is wrong; it makes this five HTML files rather than two. ✓ VERIFIED on both board layouts, the setup screen and the card viewer: sheet loading from the new path, the board gutter unchanged at 18px (10 scrollbar plus 8 border), the thumb brightening under the cursor, and the deck browser's deliberate `.deck.clicked::-webkit-scrollbar { display: none }` opt-out still in the cascade and still winning |
| J33 | **The save-slot buttons are teal and tomato on their own near-black fill.** `option-page.css` gives `.do-load` `color: teal` and its neighbour `color: tomato`, and `#ex-buttons .button` gives every button in that row `--color: #333` as an opaque background. Teal on `#333` measures **2.65:1** and tomato **4.29:1**, against a 4.5:1 floor at the 19.9px these render at | `public/css/marvel/option-page.css`, the `QLoad`, `Load 1-3`, `Save 1-3`, `Load` and `Save` buttons in `#ex-buttons` | Low. These are debug and save-slot controls rather than anything in the normal run of play, and the labels are short and predictable, which is the only reason 2.65:1 has been survivable | PROPOSED. ⚠ Explicitly **not** caused by the N8 or N18 chrome work, and worth saying so because it was found by the sweep looking for exactly that. These buttons carry their own opaque `#333`, so the panel behind them never reached the text and the ratios are unchanged from before that work. The sweep found no foreground that the panel recolouring broke, `#current-round` having already been caught and fixed under N18. Method, which is the reusable part: walk every text-bearing element inside the chrome panels, composite each ancestor's `background-color` and `opacity` down onto the board fill to get the true backdrop, and compare against the 4.5:1 and 3:1 floors by computed font size and weight. Attribution comes from asking which ancestor supplies the first fully opaque background: if that is the panel, a fill change could have broken it, and if it is the element itself, the fill change is irrelevant. Suggested fix if taken: lighten both to clear 4.5:1 on `#333` rather than changing the fill, since the colours are carrying meaning, load against save |
| F12 | **Whether an encounter set is a "standard" set or a modular one is decided by its NAME, in four places.** The test is `startswith("standard") or startswith("expert")`, re-derived independently at `game/operate/worlds.py:763` (`GetStandardEncounterSets`), `worlds.py:773` (`GetModularSets`, the same test inverted), `game/ability/factory/setup.py:120` (`SetModularSetsAside`) and `public/scene.html:957` (which fieldset a set appears in). There is no type, flag or field on the set saying which it is | `game/operate/worlds.py:763,773`, `game/ability/factory/setup.py:120`, `public/scene.html:957` | The distinction does real work rather than being cosmetic. In `SetModularSetsAside` the two halves are treated completely differently: modular sets are capped to the number the scenario allows and their cards go to `set_aside_modular_card_ids`, while `message.encounter_set_names` is REPLACED with only the standard ones. So a misfiled set does not just appear in the wrong box in the UI, it takes the wrong path through setup | PROPOSED. Low urgency, because the convention currently holds: 6 of the 148 sets in `data/encounter_sets/` match the prefix (`standard`, `standard_ii`, `standard_iii`, `expert`, `expert_ii`, `expert_campaign`) and all 6 are meant to. Nothing merely contains those words without starting with them. ⚠ Two ways it bites. A new set named badly is silently misclassified with no error at any of the four sites. And the rule cannot be changed in one place: all four re-derive it, and one of them is in the client, so client and engine can disagree about the same set. The fix is a field on the encounter set json rather than a prefix, with the four tests reading it. Not urgent, but worth doing before someone adds a set called something like "expert_only_minions" and spends an afternoon on it. Found while explaining the Standard Sets box to Q, not from a failure |
| J9 | **DONE.** `-no_<flag>` on the command line was silently ignored for any already-declared variable. `ParseArguments` writes the stripped name into `instance_command` but then calls `InitVariable(key)` with the `no_` prefix still attached, so the lookup misses `variable_dict` and nothing re-reads the value. The positive form works, because there the key matches. ✓ VERIFIED: `-no_disable_numpy_random` left the flag at its default, which is how the F10 tests nearly measured the wrong backend. Two-line fix, strip before the lookup | `engine/config.py:153-163` | Medium, silent | **DONE**, two tests, one per form |
| J34 | **A flag set by a config group cannot be overridden later on the same command line, and the override is accepted in silence.** `ConfigVariable.Base.SetValue` returns early when the variable's `set_from` already equals the incoming one, so the first command-line write to a variable wins and every later one is dropped. Groups make this reachable without anyone writing a duplicate flag: `-test` expands inline to `-device -no_editor -no_statistics ...`, that expansion sets the variable straight away because it is already declared by then, and the outer pass afterwards writes the user's own `-statistics` into `instance_command` and calls `InitVariable`, which returns having done nothing. The store and the variable are then disagreeing, which is what makes this hard to see from either end. ✓ VERIFIED two ways: with `-test -statistics`, `instance_command['statistics']` reads `True` while the variable reads `False` from `CommandLine`; and in isolation, `SetValue(False, 'CommandLine')` followed by `SetValue(True, 'CommandLine')` leaves the value at `False`. Cost so far: statistics cannot be turned back on for a `-test` run, so verifying N19 meant expanding the group by hand. Distinct from J9, which was the `no_` prefix left on the lookup key. ⚠ The early return is not simply deletable. It is what makes a repeated read idempotent, and `InitVariable` is called more than once per variable, at parse time and again from `SetupVariables`. Without it the second call reaches the `assert self.set_from == "DefaultValue"` one line below and fails. A fix has to tell a re-read of the same source from a genuine later override | `engine/config.py:33-34`, group defined at `engine/engine.py:27` | Medium, silent | PROPOSED |
| J35 | **The crash handler writes into the repository root and kills the process, and in a unit test it does both.** `SaveCrash` saves the scene to a hard-coded `./crash.json` (`engine/engine.py:185`), then `exit(-1)` when `Engine.in_unit_test` (`:189-190`). The path is not a config variable, unlike every other file the engine writes, so it lands wherever the process was started. Reached from `log.py:232` and `replay.py:161`, meaning any logged error during a test takes the runner down with it and overwrites whatever was in `crash.json` on the way out. ✓ VERIFIED the hard way: a batch of simulated games hit a policy exception and destroyed a real crash repro that had been sitting there since 2026-08-19, and it is gitignored so there was nothing to restore. Every tool written against the engine since has had to stub `SaveCrash` defensively, which is the tell that the default is wrong. `unit_test/test_save_crash.py:28` already sets `in_unit_test = False` around its own call with the comment "otherwise SaveCrash calls exit(-1)", so the trap was known and worked around rather than fixed. Two separable fixes: make the path a `ConfigVariables.File` like `crash_file` at `log.py:13` already is, and do not overwrite an existing crash without a suffix | `engine/engine.py:179-190` | Medium, destructive | PROPOSED |
| J36 | **`GameOverReason.players_won` is a type annotation, not a value, so reading it raises on any game that did not end in a win or a loss.** `game_over.py:67` declares `self.players_won: bool` and never assigns it; the only write is at `:96` inside `SetGameOver`. A game that ends by `SetExit` or `SetUndo` therefore has a `GameOverReason` with `is_game_over` true, a `reason`, and no `players_won` at all, and asking for it is an `AttributeError` rather than an answer. ✓ VERIFIED: a run that ended on Exit raised `'GameOverReason' object has no attribute 'players_won'` from code that had worked for hundreds of finished games, which is the shape of the problem: it is invisible until the first game that ends some other way. `game/rule/statistics.py:44` reads it directly and is safe only because it runs off the game-over message rather than the reason object. Either initialise it to `None` and let callers test for it, or expose the question as a method that cannot be absent | `game/world/game_over.py:67`, written at `:96` | Small, silent | PROPOSED |
| J37 | **`Random.PushState` does nothing unless a config flag is set, while `Random.Undo` asserts that it is, so recording a generator position silently fails and only the paired call complains.** `PushState` returns early on `not ENABLE_RANDOM_UNDO.value` (`engine/lib/random.py:102`) and `Undo` asserts on the same flag (`:181`), which defaults to False (`:16`). The asymmetry is the defect: the call that records is quiet about being disabled and the call that consumes is loud, so the failure surfaces at the wrong end and looks like a missing state rather than a disabled feature. The docstring explains why capture is off by default, copying a 624-word buffer per draw, which is a good reason for the default and not a reason for the silence. ✓ VERIFIED: code that pushed and restored the generator around a simulated rollout appeared correct, did nothing, and let the rollout consume the real game's draws; identical play ran seven rounds instead of six until the flag was turned on. A one-line fix either way: have `PushState` warn once when it is asked to record while disabled, or have it raise the same way `Undo` does | `engine/lib/random.py:88-109`, `:175-190` | Small, silent | PROPOSED |

### J13 confirmed upstream, and what his original looked like

irefrixs answered issue #8 on 2026-08-18 and confirmed the defect outright: *"So yes, this is an
actual bug in the open-source version."* He also gave the cause, which no amount of reading the
open-source tree would have produced. `save_local` was never missing by design. It lived on a
mixin that is not in this repository at all:

```python
class GameServerXXX(GameServerBase):

    async def save_local(self, request: web.Request) -> web.Response:
        result = self.game.session.SaveScene(delete_old=False)
        return web.Response(text=result)

    @override
    def __init__(self) -> None:
        self.AddAwaitGetSecurity('/save_local', self.save_local)
```

with `class GameServer(..., GameServerXXX)` in `server.py`. The mixin existed to upload replays and
bug-report saves to their private server. Stripping the server code for the open-source release
took this function with it: *"Unfortunately, we removed this function along with it by mistake."*

Three things worth keeping from that.

**`delete_old=False` was right.** We inferred it from the `/save` debug command. His original uses
the same argument, so the reasoning and the answer both hold.

**Our registration is the better of the two, and the reason is J17.** He registered it with
`AddAwaitGetSecurity`; we used `AddNonAwaitGetSecurity`. ✓ VERIFIED at
`engine/network/web_server.py:120-140`: on a failed check the await variant returns
`LoadHtmlAuthenticate()` or `LoadHtmlCleanCache()`, a **200 with an HTML body**. `Command.saveLocal`
prints the body as the path it saved to, so his version reproduces J13's exact symptom, a save that
never happened reporting a page as its filename, on any version mismatch. The non-await variant
answers 401 or 409 with a plain-text body since J17, which is the shape the client can actually
tell apart. Keep ours.

**His handler blocks the event loop.** `SaveScene` writes the file synchronously inside an `async
def`. `AddNonAwaitGetSecurity` runs the handler through `TaskManager.ToThread`, so ours does not.
Minor for a one-shot save, but it is the second reason not to copy his registration.

There is no fix upstream and no plan for one. The value of the reply is the specification, not a
merge.

### J18: the cookie route caches itself out of existence

Two parts, and only the second is obvious.

The button is the easy half. Uncomment the `get_version()` call in the `reloadButton` handler in
`public/clean_cache.html` and await it before reloading, so the click actually refetches the cookie
rather than trusting `reload(true)`, which has not forced anything in years. That alone turns a
permanent lockout into one click.

The caching was the half that needed a decision, and the decision was to take it out. The
`image/jpeg` content type and the `HeaderCache` header are labelled a hack in the source, so they
were done on purpose, and the reason remains ✗ UNVERIFIED. What was checked before changing it is
the dependency question, and it comes back clean: `clean_cache.html` is the only caller of
`/get_version` anywhere, and the one in `main.html:212` is commented out. So nothing downstream
relies on it being a cache hit, and the most the hack could have been buying is one round trip on a
page you only ever see when something is already wrong. A response whose entire job is to issue a
`Set-Cookie` cannot be cached and still do that job.

One consequence worth stating plainly, because it decides whether the client half is optional. It is
not. `no-store` only governs responses a browser has not already stored, so every browser still
holding the old year-long copy stays locked out no matter what the server sends. The `cache:
'reload'` on the client fetch is what rescues those, and it is self-cleaning: the forced request
comes back `no-store`, which evicts the stored entry. That last step is spec-level reasoning rather
than something measured here, since resource-timing entries are not recorded for fetches issued from
an injected script context, which is the only handle the tooling gave.

There is a third option, and the pieces for it are already sitting in the tree unwired.
`Lib.cookie.setString` at `public/js/marvel/lib.ts:90` is typed to accept exactly one name,
`"app_version"`, and nothing in the client ever calls it. ✓ VERIFIED, the only `setString` hits in
`public/js/marvel/` are the definition and its `getString` neighbour. Meanwhile `get_version()`
fetches the version string and throws it away except for a `console.log`. So the client already has
a function whose only possible purpose is to write this cookie, and the value to write, and never
connects them. Having the client set the cookie from the fetched text would survive the response
being cached, since it does not depend on a header surviving the cache. Whether that was the
original plan is ✗ UNVERIFIED, but it reads like a half-finished one.

Worth noting what this cost in practice: it is invisible. The server is correct, restarting it
changes nothing, and the page tells the player to clear their cache while offering a button that
cannot. Nothing in the UI distinguishes it from the game being broken.

### J15/J16: a blank card that was silently changing the rules

Found from play, 2026-08-11, in the same Spider-Man vs Rhino session that has been running since
21:05 the previous evening. The report was two symptoms that sounded unrelated: allies were being
discarded after attacking or thwarting, and Rhino had an attachment whose art would not render, so
the card could not be identified.

Most of the ally deaths are the rules. Allies take consequential damage after using a basic power,
which the data encodes as the `*` count in the printed ATK/THW and `can_attack.py:48` /
`can_thwart.py:23` parse back out. Core allies have 2 or 3 hit points, so two or three activations
end them. The rest is the attachment: the only card in the core set that grants retaliate to the
villain is `01153` Concussion Blasters from the Under Attack modular, ✓ VERIFIED as
`GiveKeywordToAttached(Villain, retaliate=1)` in its script. Retaliate adds 1 damage to every ally
that attacks, on top of the consequential damage, which is why attacking cost allies faster than
thwarting did. ? INFERRED that this is the card in play, from elimination plus the art being absent
from disk; the live scene was not inspected.

The point for this document is what the two defects do together. `01151` from Under Attack has art
cached but `01152`, `01153` and `01154` did not, and the Cerebro CDN serves all three fine on
demand, ✓ VERIFIED at 200 and roughly 370 KB in 0.6s each. So the fetch failed once, at the moment
the card first entered play. Because the file was not written to disk, ? INFERRED that it was the
`Timeout` branch, the only one that skips the write. J15 then pinned the placeholder in memory for
the remaining eleven hours of the session.

J16 is what turned that from cosmetic into misleading. `CreateNoImage` resolves the render data
correctly, ✓ VERIFIED by calling it directly: `01153` yields name `Concussion Blasters`, type
`Attachment`. It hands that to `CreateImage`, which paints the aspect background and then calls
`DrawText` three times, and `DrawText` returns without drawing. The output is a single-colour
254x352 image, ✓ VERIFIED at exactly one distinct pixel value, `(135, 147, 159)`, which is
`aspect_dict[""]`. Byte-identical for `01096`, `01152` and `01153`, which is the tell: three
different names, one output.

So the player was shown a blank rectangle for a card that had silently given the villain retaliate,
and the fallback designed to name that card had been dead the whole time. Same shape as J12: a
rendering path that cannot fail, and therefore cannot report.

All five parts are now done. What was decided, in the order they were listed:

1. **Nothing generated is persisted under a card's name.** A definitive miss is recorded as
   `{name}.no_art` in the cache folder instead. `LoadImage`, `FindImageFile` and `CanLoadImage` all
   read only `.webp`, `.jpg` and `.png`, so a marker is invisible to every one of them, and it says
   in its own body why it exists and that deleting it makes the game ask again. `SAVE_EMPTY_IMAGE`
   keeps its meaning, it now controls whether the marker is written rather than whether a fake JPEG
   is. The reason for keeping the flag at all is the case it was presumably added for: a card-id
   shaped name the CDN does not carry, which is what `90001` is, would otherwise cost a request on
   every run forever.
2. **Definitive and transient are now different outcomes.** A status is an answer, so 4xx other than
   408 and 429 records a marker. No status, or 5xx, 408, 429, is not an answer: nothing is recorded
   and the next request tries again. Where several servers are configured, any transient result wins
   over a definitive one, because the cautious choice is to ask again rather than persist a negative
   we are not sure of.
3. **Retry, capped twice.** Per name, `image_download_attempts` (3) tries before that name settles
   for a placeholder for the run. Run-wide, `image_download_failure_limit` (10) consecutive transient
   failures stops asking altogether, and any success resets the count. The second cap is the reason
   raising `timeout=3` to `image_download_timeout` (10) is safe: retries multiplied by a longer
   timeout across every card on a 322-image New Game screen is exactly the disconnected-machine case,
   and it now costs at most ten timeouts before the run gives up. Both routes run on worker threads
   via `TaskManager.ToThread`, so none of this blocks the event loop, but it would still have been a
   ten-fold regression on the wall clock.
4. **`DrawText` fixed**, in `b8715c9`. Shipping a config flag that does nothing is worse than not
   having it, because it reads as a fallback that exists. Done first because it is the part that
   makes every future instance of J15 diagnose itself: a card with no art now says what it is, which
   is all that was needed here.
5. **A placeholder now says so.** `Log.Warn` on the transient and give-up paths, which is the case
   that went silent for eleven hours. Deliberately `Log.DebugInfo` for a card we simply have no art
   for, because warning once per name would put 322 lines in front of anyone on a fresh clone and
   bury the two lines that matter.

Two things left by hand. `assets/cache/90001.jpg` is still the poisoned placeholder from before this
change and wants deleting, harmless only because `assets/pics/90001.jpg` is searched first; a scan
for files under 4 KB across `assets/` found it to be the only one. And the placeholder still cannot
render `→`, which the default font has no glyph for, so `resources → discard this card` comes out
with a box in the middle. Legible enough to identify a card, and not worth a font dependency.

### J17: a status card no server restart could fix

Found from play, 2026-08-13. Reported as a grey attachment on Spider-Man that could not be
identified, then again two games later as "stunned is still not showing the image when it's
attached". The word that mattered was "still": it had survived new games, a new hero, a new
scenario and server restarts.

The server was innocent, and proving that took most of the work. Every one of the 403 files in
`assets/cache/` is healthy, the smallest 244 KB and none zero length, so J15's marker policy is
holding. Of the 74 distinct cards in the session, exactly two have no art anywhere, `stunned` and
`tough`, and both render legibly as generated placeholders now that J16 draws text: green with
STUNNED across it, orange for TOUGH, ✓ VERIFIED by fetching both from the running process. So the
image the client was asking for existed and was correct.

I got the first diagnosis wrong and it is worth recording why. The log showed that Stunned being
gained at entry 601 and discarded at 660, so I ruled out the status card and looked for another
attachment. That was answering the wrong question. The card leaves play; the cache entry does not.

What is actually broken is that the guard in front of the image routes answers with a *page*.
`AddNonAwaitGetSecurity` wraps `/sets/{path}`, the `/{path:.+}` image catch-all and `save_local`,
none of which can render HTML, and on a version mismatch it returned `LoadHtmlCleanCache()`. Two
things then compound:

- The status is 200. A 200 is success, so neither the browser nor `Command.saveLocal` had anything
  to treat as a failure. This is exactly J12 and J13 again, and J13's own fix was to start checking
  `response.ok`, which is why that half already degrades correctly.
- The body carries `Cache-Control: public, max-age=31536000`, because `ReadFile` stamps
  `HeaderCache` on every release build. A page whose entire purpose is to describe the state of one
  request was being cached for a year, under the URL of whatever it refused.

So the failure window is small and the consequence is permanent, which is the same shape as J15.
Any card image requested while the cookie was stale is blank for a year, on that client, for every
game. Status cards are the most exposed because they are requested mid-session rather than during
page load, so they miss the window where a normal reload would refresh them.

The fix is two small changes. `NoStore` overrides the header on both guard pages, so neither can
outlive the condition it reports. `RefuseResource` replaces the page on the resource routes with
401 or 409 and a plain-text body, so a refusal reads as a refusal.

Neither change can repair a client that has already cached one. That needs the site data cleared,
and a plain reload is not reliably enough, because the status image is fetched through a CSS
variable after the document has loaded rather than as part of it.

Not verified end to end. The tests cover the handler and the headers, but confirming it against a
live server means restarting one, and a game was in progress.

### J8: Cancel on a multi-option forced prompt asserts

✓ VERIFIED by playing the game, 2026-08-09. Spider-Man vs Rhino, seed 42, end of turn 1. The
"Spider-Man End Phase (1~6)" prompt offers a Cancel button; clicking it produces:

```
File "engine/controller/controller.py", line 274, in ChoiceOne
    assert len(effect_descriptors) == 1 and effect_descriptors[0].target_num_range[0] == 0, f"{is_forced}"
AssertionError: True
UndoRequest
```

Declining sends `id == 0`, and the assert on that path only tolerates a single descriptor needing
no targets. The End Phase prompt has more than one, so a legal-looking UI action raises. The game
recovers by offering the error dialog with Ignore/Report and an undo, so it is not fatal, but the
Cancel button is offered in a state where it cannot be honoured.

Worth checking whether Cancel should be suppressed for this prompt shape, or whether the assert is
too narrow. Note the harness hit the same assert from the other direction while building I2, which
suggests the decline contract is genuinely underspecified rather than just mis-clicked here.

**Fixed 2026-08-10.** The rule the assert encoded is real and is kept: a forced prompt can only be
declined when its single option asks for nothing, otherwise it was not forced. What changed is what
happens when the rule is broken. The rule now has a name, `Controller.CanDecline`, and five tests
in `unit_test/test_decline_contract.py`.

The engine takes that id from a client over HTTP, so a client offering a button the engine will not
honour must get a refusal, not a stack trace. `ChoiceOne` already has a way to say "I cannot use
this input", returning `(None, True)`, and the caller asks again. That is now what happens.

**The subtlety worth keeping.** Skip and replay fallthrough feed the engine its own input, and
`"{}"` parses to id 0, so the decline path is reachable without any client involved. Refusing
generated input would just produce the same answer forever, so that case stays a loud failure with
a message naming the prompt. Only client input gets the refuse-and-ask-again treatment. Without
that split this fix would trade a crash for a spin, which on this branch would be bounded by I7's
retry cap but upstream, where I7 was declined, would be an unbounded hang.

Not verified end to end: reproducing the original browser click needs a live game driven to the end
of turn 1, which the harness cannot currently reach. The rule is unit-tested, the wiring is four
lines, and the replay suite plus 56 unit tests exercise `ChoiceOne` heavily without regression.

### J1: a bare `except` can silently disable a card

In `FindGiven`, which filters the effects an ability can see:

```python
try:
    # Fix "43007"
    if when != None and not issubclass(effect.ability.when, when):
        continue
except:
    continue
```

The `try` exists to absorb a `TypeError` from `issubclass` when `ability.when` is not a class, a
workaround for one card. But a bare `except` catches everything, and the handler is `continue`,
which **drops the effect from the returned list**.

So any unexpected error while filtering makes a card ability quietly not exist for that query. No
log, no crash, no failed test. The game keeps playing and one card just does not work.

**Severity correction.** An earlier revision of this entry rated it High and asserted that cards
silently stop working. That overstated what was measured, and the claim is walked back here.

What is confirmed:

- The branch is live and runs often. The only caller passing `when=` is
  `HasCost.CanPlayBy` (`game/card/face/attribute/has_cost.py:46`), which the engine hits whenever
  it decides whether a card is playable. Instrumenting one Spider-Man hand showed **23 invocations
  from 6 cards**.
- Of those 23, **every one completed cleanly**. Zero `TypeError`, zero anything else.
- `FaceEffect.FindAbility`, the other `when=` caller, is dead. Its only reference is a commented
  assert at `game/card/factory.py:127`.

So this is a real hazard sitting on a hot path, not an observed bug. No card is known to be broken
by it. It is worth fixing because the failure mode is invisible if it ever does fire, and because
the fix is three lines, not because anything is currently misbehaving.

**Fixed** on `pr/narrow-effect-filter-except`. The handler is now `except TypeError:`, which keeps
the 43007 union behaviour byte-for-byte and lets everything else propagate. Two tests in
`unit_test/test_effect_filter.py`: one asserts a non-`TypeError` escapes, and fails without the
change; the other pins the union case so the clause cannot be narrowed further by accident.

### J2: the auth endpoint does not check the password

```python
async def handle_authenticate(request):
    data = await request.json()
    password_attempt = data.get('password')
    session_token = hashlib.md5(password_attempt.encode()).hexdigest()
    response.set_cookie('session_token', session_token, max_age=31536000, httponly=True)
```

It hashes whatever the client sends and hands it straight back as a cookie. The real check happens
later in `IsAuthenticate`, which compares that cookie to the server's hash, so access control does
work. But the design has consequences:

- No rate limiting anywhere, so guessing is unbounded.
- Unsalted MD5, so one captured cookie is offline-brute-forceable back to the plaintext password.
- `secure=True` and `samesite` are commented out (`web_server.py:214-215`) and the server is plain
  HTTP, so the cookie travels in clear.
- 1-year lifetime, and the token is the password hash, so it never rotates.
- `password_attempt` is `None` if the key is absent, so `None.encode()` returns a 500 to an
  unauthenticated caller.

For LAN play with an optional password this is roughly proportionate. It is worth writing down
because at least one community fork (`z00lus`, issue #3) is explicitly targeting self-hosted
servers, and someone will eventually port-forward this.

**Partly fixed 2026-08-10.** ✓ VERIFIED first that this is not an authentication bypass, because
the terse row in the table above reads like one: with `password` set to `hunter2`, a cookie built
from the guess `wrong` is refused and one built from `hunter2` is accepted. The endpoint is
careless, not open.

What changed:

- `/authenticate` verifies the password and answers `401`, issuing no cookie. It used to answer
  `200` with a cookie for every attempt, so a client could not tell whether it had got in.
- A body that is not JSON, or that omits `password`, gets `400` instead of the `500` from
  `None.encode()`.
- The comparison goes through `hmac.compare_digest`, since comparing secrets in constant time is
  free here.
- Serving on a non-loopback address with no password logs a warning naming the address. `0.0.0.0`
  and `::` count as reachable, which is the case that matters, and an unparseable address warns
  rather than staying quiet.

**Rate limiting is deliberately not implemented, and the bullet above is misleading.** The cookie
*is* `md5(password)`, so an attacker never has to touch `/authenticate`: they compute guesses
locally and present them to any protected route. Limiting one endpoint does not reduce the guess
rate, it just moves it. Rate limiting worth having would have to sit on `IsAuthenticate`, and a
stronger password hash matters more than either.

Still open, and now tracked as F6c: `IsAuthenticate` returns `True` for everyone when no password
is configured, which is the shipped default. That is the real exposure, it applies to every
`*Security` route, and the fix is a decision rather than a patch, since refusing would break
multiplayer for everyone who has not set a password. `/debug` is already gated separately because
it reaches `exec`.

**Decided 2026-08-10: do not fail closed. Re-rated from High to Medium.**

What the risk is, after F6a. An unauthenticated stranger who can reach the port can no longer
execute code. What remains is reading game state and submitting inputs through `/post`, so this is
griefing and privacy rather than compromise, and it only exists once someone has deliberately
exposed the port. That is a Medium.

Why not fail closed. Refusing non-loopback requests without a password breaks the thing the game is
for. The devlog tells people to play four-player with friends, nothing in the setup suggests a
password is load-bearing, and the first symptom would be friends meeting a login page for a game
that worked yesterday. People answer that by downgrading or by hunting for the setting that turns it
off. A control the normal workflow has to defeat is not a control.

What to build instead, when features are back on the table. If the server binds a non-loopback
address and no password is configured, generate one and print it with the join URL in the startup
output the host is already reading. Localhost keeps working with no password and no configuration,
so solo play is untouched. Friends get a URL and a short password, which is the model Jupyter uses
for exactly this problem. No change is needed below that: an auto-generated password simply fills
`hash_password` and the existing cookie flow works.

Regenerate it per run rather than persisting it. A stored secret in a config file people copy
around is how these leak, and re-sharing costs a sentence.

Deferred deliberately: it is a feature, not a hardening of existing behaviour, and it wants a small
UI touch to be worth anything, since a password printed only to a console the host may not be
watching is half a solution. Roughly an hour when the time comes.

Untouched: unsalted MD5, plain HTTP, the one-year cookie that never rotates.

### J3: checksums are computed, then ignored

`Types.DictChecksum` is SHA-256 over sorted-key JSON, which is fine. The problem is the plumbing:

- `Json.Load` and `Json.LoadAs` default to `check_sum="Ignore"` (`json.py:179`, `192`).
- Even with checking on, a mismatch calls `Notify.Error(...)` and then **returns the object
  anyway**. Nothing refuses to load.
- The hash is unkeyed, so it detects corruption but not modification. Anyone editing a replay can
  recompute it.

Given that replays and puzzles are shared between players, "warn and load anyway" is the part
worth revisiting.

**Fixed 2026-08-10, the half that is a bug.** `"Restrict"` did not restrict: it and `"Warn"` ran
the same code, notified, and returned the object. `game/statistics/game_statistics.py:66` asks for
`"Restrict"`, wraps the call in `try/except` that sets `file_broken`, and `Save` then refuses to
overwrite a broken file. The handling was written for a refusal that never arrived. A mismatch
under `"Restrict"` now raises `ChecksumError`, and both `Load` and `LoadAs` go through one place so
they cannot drift apart.

Only a genuine mismatch. `"Not Found"` and `"Version Error"` mean the file carries no checksum to
contradict, which is true of anything written before checksums existed or with the default
`ignore_check_sum=True`, and refusing those would reject files that are old rather than damaged.
Six tests, including that carve-out.

**Still a decision, not done.** Scenes and puzzles still load with `"Warn"`
(`game/scene/loader.py:32`, `server_new_game.py:121`). Moving them to `"Restrict"` would refuse to
open a save whose checksum has drifted, which is right for a file arriving from another player and
harsh for a player's own library if anything ever wrote a stale checksum. That is a call about
other people's files, so it is left open deliberately.

Unchanged and still true: the hash is unkeyed, so it detects corruption and not modification.
Anyone editing a replay can recompute it. That is a design limit rather than a defect.

### J4: `Simultaneous` runs sequentially

```python
@staticmethod
def Simultaneous(process: Callable[[T], None], objects: List[T]):
    for object in objects:
        process(object)
```

Four call sites, all `process_player` over `const_players` (`world.py:326,331,385`,
`event/manager.py:327`). Sequential is almost certainly correct here, since parallel player
processing would destroy replay determinism. The defect is the name: it tells a reader that
multiplayer work is already parallel, which is both wrong for anyone profiling B1 and an
invitation for someone to "fix" it and silently break replay.

Rename, or add a comment saying the serialism is deliberate.

### J6: the rules engine is enforced by `assert`

619 `assert` statements across `core/`, `engine/`, `game/` and `cards/`, many of them validating
game rules rather than checking internal invariants. Python's `-O` flag removes every one. Nothing
in the repo currently sets it, so this is latent rather than live, but a PyInstaller spec or a
packaging tweak is all it would take to ship a build whose rule checks are absent.

**Fixed 2026-08-10 by refusing to run that way.** `Engine.Initialize` now calls
`Engine.CheckAssertionsEnabled`, which raises when `__debug__` is false, naming the flag and saying
why. Converting 619 asserts into explicit checks is a different and much larger project; refusing
to start costs four lines and removes the whole failure mode.

The check cannot itself be an assert, for obvious reasons, and a unit test that passes the flag by
hand only proves the branch works rather than that it is ever reached. So one of the four tests
launches a real `python -O` subprocess and confirms it exits non-zero with the message. ✓ VERIFIED
the same way by hand: `python -O` into `Engine.Initialize` refuses.

---

## E. Strategic direction: stay in Python, or port?

**Recommendation as of 2026-08-09: stay in Python. Fix the algorithm, not the language.**
Reasoning below; the decision is not final until G1 lands.

**The port cost is the card scripts.** 102,461 lines across 3,457 card scripts is 63% of the
codebase and represents ~2 years of rules encoding. A port has only two shapes:

- *Rewrite the card scripts in the target language* — that is the entire project again, and it
  cannot ship until it is finished.
- *Keep Python as an embedded scripting layer* — but card scripts **are** the hot path. Event
  dispatch exists to call them. A Rust/Go core would still pay Python execution plus an FFI
  crossing per effect evaluation, plausibly making the measured problem worse.

**The measured infrastructure is healthy.** 0.26 ms to import a card script, 0.32 s engine init,
indexed event dispatch. Nothing found so far looks like an interpreter wall.

**The known problem is algorithmic and language-independent.** Undo replays the session from
zero. Rewriting that in a faster language buys a constant factor on a cost that grows linearly
with game length. Snapshot/rollback fixes it in any language, Python included.

**PVP (B3) is a rules-model problem, not a language problem.** No language choice makes it easier.

**Honest cost of staying:** snapshot/rollback depends on B2, and B2 is a migration across 3,457
scripts. That is the real price. It is still smaller than a 102k-line rewrite, and unlike a
rewrite it can be done incrementally behind a shim while the game keeps working.

**What would change this recommendation:** G1 showing per-action logic cost high enough that even
with snapshot/rollback the game is too slow — i.e. a genuine constant-factor wall rather than an
algorithmic one.

| ID | Item | Status |
| --- | --- | --- |
| E1 | Decision: remain on Python; treat B1 as an algorithmic fix (snapshot/rollback) rather than a rewrite. | PROPOSED, pending G1 |
| E2 | If a CPU wall is later confirmed, evaluate in-language escape hatches first: PyPy, and the existing `enable_multiple_threads` flag (`engine/task/manager.py`, default `False`, reason for the default is ✗ UNVERIFIED). | PROPOSED |

---

## G. Gates: do these before committing to a direction

| ID | Item | Why it blocks | Status |
| --- | --- | --- | --- |
| G1 | **Profile a real session.** See the attempt log below. | The single number that decides E1. Everything in B1 and E is inference until this exists. | **DONE 2026-08-19**, once G5's premise turned out to be false. Profiled the 152-input Black Panther session through `test_profile_profile`: 1.30s total, debug build so assertions are included. The message broadcast path dominates: `message.py:66(Send)` 2154 calls at 1.128s cumulative and `manager.py:628(BroadcastMessage)` 2158 at 1.126s, which is 87% of runtime on one stack. The cost is not in those two, whose self time is 0.010s and 0.026s, but in what they call: `FilterAvailableEffects` 1126 calls at 0.772s, `manager.py:575(check)` 1100 at 0.662s, and `CheckCondition` 6481 at 0.656s. **This profiles replay, not live play**, so it does not answer B1's undo cost, which still needs the skip-mode work in the postscript below |
| G2 | Determine when `DoNotCheckFastUndo()` disables the fast-undo pruning path in `engine/controller/module/undo.py`, and how much that path actually saves. | If fast-undo is silently off in normal multiplayer, the reported "over a minute" may be a bug, not a design limit. | PROPOSED |
| G4 | Record a real game through the browser and save the replay. | The synthetic driver stalls; a human-played scene sidesteps that entirely. | **DONE**, see below |
| G5 | Play a game **to completion** in the browser and save that. | Was thought to be the remaining blocker on G1. | **RESOLVED 2026-08-19 without doing it, because the premise was wrong.** "Fixtures have to be finished games" does not hold: of the seven replays already on this machine, six drive the harness to a clean pass and only the 4-input one raises `EOFError`. The real constraint is the narrower one I3 arrived at later, that a fixture has to end where nothing else is asked, and most saves already do. No game had to be played to completion; the corpus needed for G1 was sitting in `replays/` the whole time |
| G3 | ~~Ask upstream for a replay corpus.~~ | Asked and answered in issue #1: cannot be shared (player-uploaded, >1 GB, off-Git). Superseded by I3, author our own. | **REJECTED** |

---

## H. PVP feasibility (revises B3)

Audited 2026-08-09. **Upstream's framing — "this engine was built without fully considering
changes like that" — is more pessimistic than the code supports.** The two hardest primitives
PVP needs already exist and one of them ships working in a released scenario.

### What already exists

**1. Multi-board isolation is built, threaded, and live.** ✓ VERIFIED

`GameArea` (`game/world/game_area/game_area.py`) is a real object with `AddPlayer`, `AddCard`,
`FindAllPlayers`, and enter/leave hooks. It is threaded through the codebase:

- every `Card` carries `.game_area` (`game/card/card.py:76`)
- `CardFace` implements `OnEnterGameArea` / `OnLeaveGameArea` (6 implementations)
- `Worlds.GetOnFieldCards / GetVillains / GetMainSchemes / GetOnFieldMinions` all take a game area
- `CardFinder` accepts a `game_area` filter, enforced at `card_finder/checker.py:174-175`
- moves carry `target_game_area` (15 sites)
- `Scenario.GetVillain(game_area)` is **already area-aware**: per-area villains work today

And it is not theoretical: **`cards/pack/toafk/kang/__init__.py:107` creates a second game area
in a shipped scenario.** The Once and Future Kang splits players onto separate boards, each with
their own Kang and main scheme, then merges them back via `JoinOtherGameArea`. That is
structurally the same problem PVP poses.

**2. The threat side is already a first-class actor.** ✓ VERIFIED

`Scenario(User)` and `Player(User, ...)` share a common base (`game/player/user.py`). The villain
side already owns decks, is an effect controller, and answers `GetGameArea()`. The
`Player`/`Scenario` asymmetry is shallow: only **11** `is_scenario` branch points exist across
the entire `game/` layer.

### What is actually missing

| ID | Gap | Detail | Est. difficulty |
| --- | --- | --- | --- |
| H1 | **Threat side has no controller** | `Player` binds to a `Controller` (input device); `Scenario` acts only through automated rules. PVP requires the threat side to accept input. This is the core work. | Large |
| H2 | **Exactly one `Scenario` per world** | `World.__init__:46` hardcodes a single instance. Two opposing sides need two, or a re-framing of what "scenario" means. | Medium |
| H3 | **Turn structure is co-op-shaped** | `World.OnGameLoop`: `start_round → PlayerPhase (all players) → PlayersEndPhase → VillainPhase → end_round`. PVP needs alternating or interleaved turns. | Medium |
| H4 | **Nothing iterates `world.game_areas`** | 0 loops over it. `CreateGameArea` has 1 caller. `game/card/factory.py:133` hardcodes every new card into `GetFirstGameArea()`. The plumbing exists; the engine only ever drives area[0]. | Medium |
| H5 | ~~**Area isolation is opt-in (= F8)**~~ **Retracted 2026-08-19.** The count was right and the conclusion from it was wrong: 1 of 874 `CardFinder(` constructions passes `game_area`, but that filter is a refinement, not the mechanism. Isolation is enforced by the scopes, by default. Not the sleeper, and not large. | See the F8 re-scope below | **Was "Large, the sleeper". Now medium and bounded at 47 call sites** |
| H6 | **Player count capped at 4** (= F7) | `(0,1,2,3)[:player_num]`. PVP team formats may want more. | Small |

### Assessment

The ~300 h estimate upstream gave is plausible *for their standard of completeness*, and H5 is
probably why: the isolation guarantee is documented in a comment but enforced only where someone
remembered to pass the filter. Making it structural — so cross-area leakage is impossible rather
than merely usually-absent — means touching every query site.

But this is a **refactor along a seam the codebase already has**, not a rebuild. That is a
materially different proposition from what the devlog implies.

### Recommended sequencing

Do **not** start PVP first. In order:

1. **F1–F3 + G1** — fix the RNG leak and settle the determinism question. PVP multiplies state;
   do not build on an RNG you cannot trust or replay.
2. **B2 / snapshot-rollback** — PVP makes undo strictly worse (more boards, more state). Fix undo
   before adding to what it has to reconstruct.
3. **H5** — make area isolation structural. This is independently valuable: it hardens the
   existing Kang scenario, which today relies on the same opt-in filtering.
4. **H1–H4** — then build PVP on a seam that is actually load-bearing.

| ID | Item | Status |
| --- | --- | --- |
| H0 | Adopt the sequencing above; revise B3 down from "engine wasn't built for it" to "refactor along an existing seam." | PROPOSED |

---

## I. Testing: the circularity problem

Investigated 2026-08-09. This is the biggest structural obstacle to every other item in this doc,
and it is not simply "no fixtures ship."

### The harness works. It has no inputs.

✓ VERIFIED. `unit_test/test_all.py` needs three things that are absent from the repo:

| Path | Referenced at |
| --- | --- |
| `launch-debug.json` | `unit_test/test_all.py:26-27` |
| `./replays/min_test/` | `unit_test/test_all.py:42` |
| `./replays/profiles/` | `unit_test/test_all.py:43` |

All three are intentionally absent, per irefrixs in issue #1 — `launch-debug.json` is a
developer-local config, and the replays are player data. Supplying them locally
(`cp launch.json launch-debug.json`, `mkdir -p replays/min_test replays/profiles`) makes the
suite run:

```
<I> --- Test Start ---
<I> --- Test End --- (0/0)
AssertionError                     # unit_test/entry.py:48, `assert world`
```

So the infrastructure is sound; it finds zero cases and then dies on a bare assert.

| ID | Item | Status |
| --- | --- | --- |
| I1 | Empty corpus fails with a bare `AssertionError` at `unit_test/entry.py:48` instead of reporting "no test cases found". Trivial fix, saves the next person an hour. | **DONE**, fails at the check with the folder named and how to fill it |

### What upstream's suite actually does, in his words (2026-08-18)

Answering issue #6, he described the method, and it confirms the reading of this section from the
outside rather than by inference:

> We run all existing save files through the game engine, and check that the CRC values in the save
> JSON still match.
>
> After processing a save file, we also re-save it using the new version number. `check_is_pass` in
> `test_run.py` updates the version key in the saved JSON and the filename. Once all tests pass, we
> move the old saves to a different folder.
>
> We may introduce changes in the future that make saves incompatible between versions. Keeping
> saves for different versions makes it easier for us to roll back to an older version when needed.

Three consequences.

**The version bump is load-bearing for them, not a stray side effect.** I8 read `test_IncreaseVersion`
as a chore that had leaked into the test namespace. It is closer to a step in the ritual: bump,
run the corpus, re-stamp every save that passed, archive the old ones. That does not change the fix
here, where nobody has their corpus, but it does explain why a nine-year-old file that commits to
git has never bothered anyone upstream.

**Their test is a compatibility test, not a behaviour test.** The oracle is a CRC that the engine
itself computed on a previous version. It answers "does this build still reproduce what the last
build produced," which is exactly the property that makes it useless for verifying a fix and
excellent for catching an accidental change. It is the same circularity described below, stated
from their side.

**It confirms why the corpus cannot be replaced by generating our own.** Their saves are player
data accumulated over years across many versions, and the archive folders are the history. I2 is
still the answer for us: tests that do not depend on a replay at all.

### Why this is worse than a missing-fixtures problem

**The tests are replays, and replays are exactly what is fragile.**

1. **Fixtures are version-pinned by design.** irefrixs keeps them "organized by version number,
   since the data and file names change with each update." `Scene.GetSaveFileName` stamps
   `[{Ver.version}]` into the filename, and `SaveScene` moves superseded files into
   `./replays_{ver}/`. These are version snapshots, not a stable regression suite.

2. **Any behavioral change invalidates the corpus.** A replay reproduces a game only if the engine
   still makes identical decisions. Fix a rules bug and every fixture touching that rule diverges.
   You cannot distinguish "my change broke something" from "my change correctly altered the
   recorded outcome" without replaying by hand.

3. **The harness depends on the very property F3 shows is broken.** Replay determinism underpins
   the tests, and F3 proves determinism is backend-dependent. **You cannot write a regression test
   for the RNG divergence using the replay harness, because the harness presupposes the thing
   under test.**

4. **B2 is the exception that proves the rule.** An earlier revision of this doc claimed the
   replay corpus is useless for the `Buff` migration. That was wrong, and worth correcting: a
   representation change that *preserves* behavior is exactly what golden-master/characterization
   tests are for, and with 3,457 card scripts they are the only economically viable way to verify
   102k lines of card behavior is unchanged. Hand-written unit tests for that corpus are not a
   realistic alternative.

   The genuine risk for B2 is narrower: if replacing registered functions with buffs changes the
   **order in which effects are evaluated**, it changes RNG consumption order, and replays diverge
   even though observable card behavior is identical. That is a real hazard, and it is a reason to
   land F3 (deterministic, non-global RNG) *before* B2 — not a reason to distrust replay testing.

Upstream is candid about this: *"the current testing feature is still quite limited. We have not
invested much effort into improving it because it is not intended to be included in the release
version."*

### Way forward

| ID | Item | Rationale | Status |
| --- | --- | --- | --- |
| I2 | **Build a unit-test layer that does not go through replay.** Construct a `World` directly, drive it with the existing debug commands (`gain`, `play`, `can`, `cannot`, documented in `public/js/marvel/debug/debug.ts`), assert on state. Independent of replay determinism, and survives behavior changes. | Breaks the circularity. Prerequisite for touching B2 or H5 safely. | **DONE**, `pr/test-harness`; see the I2 progress log below |
| I3 | **Author a small replay corpus ourselves.** Play a few games; scenes auto-save to `./replays/`. Version-stamp them and accept they need regeneration on behavioral change. | Enough for G1 profiling and coarse smoke tests. Cheap. Do this first. | **STARTED**, three scenes recorded, one of them not usable as a fixture. See below |
| I4 | Commit `launch-debug.json.example` and `.gitkeep` files for `replays/min_test/` and `replays/profiles/`, plus a short note in the docs. | Every newcomer hits the same wall; kmelkon and we both did. Good upstream contribution. | **DONE**, with one deviation: no `.example` file, since it would duplicate `launch.json` byte for byte and drift. The guide documents the `cp` instead |

**Sequence:** I3 (unblocks G1 today) → I1 + I4 (trivial, contributable) → I2 (the real fix, and a
prerequisite for B2).

### I3 findings (2026-08-10): a replay fixture has to end where nothing else is asked

Investigated because `test_min` dies with `EOFError` and nothing on record explained it. All of the
below is ✓ VERIFIED by execution.

Three scenes exist on disk, none tracked by git (`.gitignore:12` covers `/replays/**/*.json`), which
is why no history explains them. The `(N)` in each filename is the recorded input count:

| Scene | Inputs | Recorded | Replays unattended? |
| --- | --- | --- | --- |
| `replays/…-(4)-(42).json` | 4 | 2026-08-09 21:38, 393 s | ✗ `EOFError` |
| `replays/…-(6)-(1605461179).json` | 6 | 2026-08-10 08:46, 74 s | not tried |
| `replays/…-(32)-(1605461179).json` | 32 | 2026-08-10 08:07, 189 s | ✓ `Test End (1/1)`, exit 0 |

`replays/min_test/` holds a byte-identical copy of the 4-input scene, made a minute after it was
recorded. So the corpus is one hand-picked save, and it happens to be the one that cannot replay.

**Why that one fails.** It replays all four inputs, reaches `4 / 4`, and then the game asks a fifth
question nobody recorded an answer to. The recording stops immediately after the player ends their
turn, and the next thing the engine does is:

```
player_phase.py:82   EndPhase
player_phase.py:23   MayDiscardHandCardsAndDrawUpToMax
player_ask.py:314    AskDiscardFaces
player_ask.py:214    AskChooseSelect      -> no recorded input -> keyboard device -> EOFError
```

Somebody quit the game one prompt before the end-of-turn discard. So this is not a broken corpus
mechanism and not a broken harness: the 32-input scene from the same session replays perfectly
through the same code path.

**The criterion, which is the useful part.** A saved scene is only usable as an unattended fixture
if the game asks nothing more after its last recorded input. Mid-turn saves are fine to load and
keep playing, which is what a save is for, and useless as a test fixture. In practice that means
recording until the game ends, or checking a candidate before adding it.

This is the same family as I7 and issue #5: an input source that is not a person meets a prompt.
The retry cap would have made this failure readable instead of an `EOFError` out of `input()`.

**Not caused by F10 or F11.** Checked explicitly, because the scene is stamped `rng: "numpy"` and
the default is now the bundled generator. It fails identically under both, at the same prompt.

**Done 2026-08-10.** `min_test` now holds the 32-input scene, and
`python -m unittest unit_test.test_all.TestMain.test_min` passes: `--- Test End --- (1/1)`, `OK`.
That is the first time the replay suite has run green in this repo. The 4-input scene was removed
from `min_test` only; the identical original is still in `replays/`.

The corpus is still untracked and always will be, since `.gitignore` covers it and the scenes are
player data upstream will not take. Anyone cloning this repository starts with an empty `min_test` and
gets I1's bare `AssertionError`, which is why I1 and I4 are worth more than their size suggests.

### G1 attempt log (2026-08-09): not answered

Three approaches, all defeated by the same thing: a scripted policy cannot sustain a long game.

| Approach | Result |
| --- | --- |
| Decline everything, drive `GameLoop` | Runs. Reaches round 3 in 0.13 s, but only 7 recorded inputs. Passing on everything is not a game. |
| Take the first legal option instead | 300 policy calls produced 11 inputs in 1.21 s, then stalled. A 200-input target ran 10 minutes without finishing. |
| Replay a captured scene at increasing depth | `LoadScene` + `GameSetup` under a scripted device hung at 7 minutes. |
| Save a 40-input game as a fixture | Stalled at 4 minutes. |

**What was measured and holds up:**

- Game setup costs **~0.10 s**, repeatable across runs. That is the fixed part of any undo, and it
  is nowhere near a minute.
- A 3-round single-player game with 7–11 recorded inputs completes in 0.13–1.21 s.
- The decision loop runs roughly **27 policy invocations per recorded input** (300 calls, 11
  inputs). Most prompts never reach the replay log.

**What was not measured:** replay cost at realistic depth, which is the actual undo number. A
single-player game of 11 inputs cannot be extrapolated to the 4-player session irefrixs described,
and doing so would be guessing dressed as data.

**What the failure itself says.** The stall is indistinguishable from slowness from outside, which
is exactly the complaint filed as issue #5 (I7, unbounded retry with no cap and no logging). The
tooling built to investigate the performance problem was defeated by a separate defect that hides
whether anything is progressing. Fixing I7 locally would likely turn these four dead ends into
readable failures.

**Unblocking path.** G4: record a real game through the browser and save the replay, which is what
irefrixs described in issue #1. A human-played scene sidesteps the driver problem completely.

### G4 result: a real game was recorded (2026-08-09)

Played Spider-Man vs Rhino on *The Break-In!*, seed 42, through the browser against a locally
running server. Produced `replays/[0.5.9.201]-spider-man-rhino-(4)-(42).json`, 4 inputs.

Three things this settled that nothing else had:

- **The game is genuinely playable on macOS end to end.** Menu, deck upload, scenario select,
  mulligan, form change, attack, end phase. Card art streams from the CDN, so the absent `assets`
  folder is not a blocker. It self-populated 325 images into `assets/pics/` on first run.
- **F3 is confirmed live.** The saved scene carries `"rng": "numpy"` in its metadata, written by
  the fix, through the real UI and the real save path rather than a test.
- **J8**, a user-reachable crash, was found by ordinary play.

Practical notes for the next attempt:

- The browser UI **cannot be driven reliably by automation on first load**. Clicking "Create
  Scene" times out the renderer while the server fetches card art one file at a time. Creating the
  game over HTTP instead works: `GET /new?data=<NewGameDescriptor JSON>`. Once art is cached the
  in-game UI is responsive and clickable.
- Saving mid-game works via the debug console: `GET /debug?/save`. It queues and runs at the next
  input request. `/save_replay_data` is *not* equivalent, it serialises the scene without calling
  `PrepareSave`, so `inputs` comes back empty.

**Still not G1.** The fixture replays its 4 inputs and then asks for input 5, which the debug
device answers with `input()` and dies on `EOFError`. See G5.

### G5 attempt: abandoned (2026-08-09)

Second browser session. Fresh game created over HTTP, server started with `-auto_save_after_game_over` so completion would save itself, mulligan cleared, turns cycled to **1/7 threat**. Then it stopped converging.

What defeated it: during the villain phase the encounter-card reveal puts a large card preview over the centre of the screen, and clicks stop reaching the game. Clicking the OK element opened the side menu (Log / Pause / Undo / Redo / QSave) instead of advancing. A queued `/debug?Threat('The Break-In!', 12)` intended to force a loss never visibly applied, and the server log stayed empty because output is buffered, so the game's actual state was not observable from outside.

The UI has hover previews, animation overlays, and context-sensitive buttons at the same screen position. Coordinate and element clicking handles simple prompts and falls apart during the villain phase.

**Recommendation: a human plays this one.** Staying in alter-ego makes the villain scheme rather than attack, so threat climbs to 7 and the game ends in a loss in a handful of End Turn clicks. Avoid Cancel on the End Phase prompt in hero form, that is J8. With `-auto_save_after_game_over` set the replay writes itself.

Also learned: `auto_save_after_game_over` defaults to **False** (`game/game.py:20`), so a finished game does not save unless that flag is set.

**Postscript.** The "stall" was not a stall. The driver runs with skip off, so every message built
a full world descriptor, which is 62% of runtime. It was progressing the whole time, just slowly,
and slowly for a reason that does not apply to replay. See the B1a retraction.

This also sharpens what G1 actually needs. Measuring undo means running with **skip on**, and skip
is the mode that discards scripted input (harness blocker 2). Reconciling those two is the real
prerequisite, not a better policy.

### A note on two retractions in one session

J1 was rated High on a failure mode that measurement showed had never fired. B1a was reported as a
live defect that measurement showed was already guarded. Both followed the same shape: a mechanism
was read correctly out of the source, and then a number measured on an adjacent path was attached
to it.

The check that would have caught both: before claiming a cost or a severity, confirm the code path
being measured is the code path being described. Reading the mechanism is not the same as
observing it run.

### I2 progress log (2026-08-09)

`unit_test/harness.py` and `unit_test/test_harness.py` are written. **The first test does not pass
yet** — one blocker remains. Three were found and fixed along the way, and two are upstream bugs
worth reporting on their own.

| # | Blocker | Resolution |
| --- | --- | --- |
| 1 | `KeyInput.IsInputReady` calls `input()` and blocks, the replay log is the engine's only non-human input source. | Wrote `ScriptedInput`, an `InputDevice` that answers from a policy. This was the missing primitive. ✓ |
| 2 | Start state `'InTesting'` turns skip mode on (`manager.py:74-77`); with skip on, `ChoiceOne` **discards the device's answer** and substitutes `convert_fallthrough_input` (`controller.py:158-159`), which is `"{}"` when no replay inputs exist. Same prompt repeated ~296k times in 60 s. | Use start state `'New'`, which takes the `is_new` branch and leaves skipping off. ✓ |
| 3 | **`ConsoleDevice` never implements `IsSyncReady`**, it inherits the abstract stub at `engine/device/base/output.py:17`, which returns `None`. `DoWaitSync` waits on that with `timeout=None`, so the first `Present()` deadlocks: main thread in `JobManager.WaitForAllJobsToComplete`, render job in `DoWaitSync`. Invisible in the replay harness because `world_render.py:114` only calls `WaitSync` when not skipping, and replay always skips. | Wrote `ScriptedOutput` with `IsSyncReady() -> True`. ✓ |
| 4 | Mulligan prompt repeated forever, 455k `ChoiceOne` calls in 90 s, no exception raised. Root cause: `DoGetInput` appends the player to `manager.asking_players` before waiting and returns **`None`** if they are still in that list on wake (`base.py:113`). `ChoiceOne` maps a `None` input to `return None, True` (the "cheat" flag) and `ChooseEffects` loops on `cheat` (`player_action.py:178`). Setting `payload.input_json` directly, the way `KeyInput` does it, never clears `asking_players`. | Answer via `manager.WhenInput(answer, player_id)`, which is what the web client calls: it removes the player from `asking_players`, stores the answer, and notifies. ✓ |

**Status: I2 is working.** `unit_test/test_harness.py` passes — 2 tests, 0.27 s total, no fixture on
disk. A full game (Peter Parker vs Rhino on *The Break-In!*, 6-card hand, 34-card deck) builds in
**0.22 s**, and the debug DSL drives it (`Gain('Enhanced Reflexes')` verified to land in hand).

That runtime matters: it is fast enough for a real TDD loop, which the replay harness never was.

| ID | Item | Status |
| --- | --- | --- |
| I7 | **`ChooseEffects` retries without bound.** `while True: … if cheat: continue` (`game/player/action/player_action.py:165-181`) has no iteration cap, no backoff, and no bail-out. A device that consistently fails to deliver input spins at ~5,000 iterations/sec indefinitely, silently. With a human web client this is the intended "show the error, let them re-enter" path; with any automated device it is an unkillable hang. A retry cap that raises after N attempts would have turned three of the four blockers above into instant, self-explanatory failures. | **DONE**, `pr/cap-input-retries`, posted upstream as issue #5 |

| ID | Item | Status |
| --- | --- | --- |
| I5 | **The console/keyboard device cannot drive a live game, two independent bugs.** (a) `ConsoleDevice` never implements `IsSyncReady`, so the first render sync deadlocks (only `WebDevice` implements it, `web_device.py:36`). (b) `KeyInput` sets `payload.input_json` directly instead of calling `WhenInput`, so `DoGetInput` always returns `None` and the caller retries forever (blocker 4). Neither surfaces in the replay harness: the sync call is guarded by `world_render.py:114`, which only runs when **not** skipping, and replay supplies inputs so `IsInputReady` is never reached. **Low practical severity**, nobody plays by typing JSON at a terminal, but the `-device` non-web path is dead code, and it blocks anyone building a headless mode. Report as a note, not a defect. | PROPOSED |
| I8 | **`unit_test/test_task.py` is not a test file and running the suite mutates your repository.** `test_IncreaseVersion` bumps `BUILD` in `build.py` and then runs `git add` and `git commit` through `os.system` (`build_marvel.py:19-20`); `test_zip_cards` writes a `cards-*.zip` into the repo root. Its own comment says *"Just use as a work, to help me increase the version number."* ✓ VERIFIED the hard way on 2026-08-10: running the standalone suite three times left three `Package version` commits on the work branch and pushed this fork's version from `0.5.9.201` to `204`, which matters because `Scene.GetSaveFileName` stamps the version into every save file. Anyone who runs `python -m unittest` across `unit_test/` gets the same surprise. Rename it out of the `test_` namespace, or guard it behind an explicit opt-in. Good upstream contribution, and cheap. | **DONE** 2026-08-18. Both chores moved to `tools/package.py`, which takes a required subcommand, so running it bare prints usage and changes nothing. Verified: `unittest discover` over `unit_test/` now leaves HEAD, `build.py` and the repo root untouched, and the file selection is byte-for-byte the same 921 files. Excluding it by name in `tools/run_tests.py` had only protected that one runner. Reported as issue #6 (U9), and **answered 2026-08-18: both cases are intentional upstream.** The `test_` prefix on `IncreaseVersion` is what makes VS Code draw a run button for it, and `test_zip_cards` packages the paid scripts build. So this was never an oversight, it is a developer tool wearing a test's name, and the surprise is real only for someone who runs the suite without knowing that. His answer explicitly blesses the fork's fix: *"feel free to remove or rename them there if you prefer."* The change stands as made |
| I6 | `WorldRender.CalculateCRC()` runs on **every** `ChoiceOne` (`controller.py:54`) and walks every card calling `GetRenderInfo()`. Harmless per decision, but it is unconditional, including during skip/replay, where nothing renders. | **INVESTIGATED and CLOSED 2026-08-19 as not worth doing, with the proposed fix withdrawn as unsafe.** Measured first: 152 calls at 0.117s in a 1.30s session, 9% of runtime and 0.77ms per call rather than the ~0.1ms a microbenchmark suggested. Then the premise collapsed. **"Skip it when nothing renders" would break the thing it exists for.** The CRC is not a render artifact despite living on `world.render`: `replay.py:87` compares it against the recorded value to detect divergence, and `controller.py:375` stamps it into every recorded operation. It is needed *precisely* during replay, when nothing renders, and `check_crc` defaults to true with exactly one caller disabling it. The cost is also inherent rather than incidental. 92% of `GetInfoDict`'s time is in the `getattr` that evaluates about a dozen computed attributes per on-field card; the dict churn around it was tightened and measured identical across three runs either side. The only remaining lever is caching those attributes, and a stale cache means a wrong checksum, which is the exact failure the CRC exists to catch. Finally the 9% is a **test-suite** cost, not a gameplay one: 0.77ms per decision is imperceptible in play and only matters when replaying a corpus. Left as it is; the tightening is kept because it is strictly better code, with a comment saying it measured neutral so nobody repeats it |

Note: I2 is the most valuable engineering work identified anywhere in this document. Every large
change — snapshot/rollback, the Buff migration, PVP area isolation — is gated on having a
regression net that does not itself depend on replay.

---

## Change log

| Date | Change |
| --- | --- |
| 2026-08-09 | Doc created. Sections A (macOS audit), B (upstream rationale, cross-checked), C, D seeded. Nothing implemented yet. |
| 2026-08-09 | Added B-measure (codebase sizing + startup/import benchmarks), section E (Python-vs-port recommendation), section G (decision gates G1–G3). Recommendation: stay on Python, pending G1. |
| 2026-08-09 | Q decided: **stay on Python.** E1 accepted in principle; G1 still worth running to size B1. |
| 2026-08-09 | Added section F (design audit, F1–F8, RNG leak measured, dead code, puzzle-save corruption, bypassable blocklist verified by execution) and section H (PVP feasibility, revises B3 downward, multi-board isolation already exists and ships in the Kang scenario). |
| 2026-08-09 | Added section 0 (upstream status): maintainer is active, license/contribution/test-corpus questions already answered publicly, prior work by kmelkon logged. Added A9 (kmelkon's `SaveCrash` fix never landed). Posted issue #4 upstream (U1). G3 **rejected**, corpus cannot be shared. G1 unblocked. |
| 2026-08-10 | **F6 reassessed and gated.** The "debug console" the blocklist guards is an HTTP endpoint, `GET /debug?<python>`, ending at `exec`. Its auth wrapper passes everyone when no password is set, which is the shipped default, so the bypassable blocklist was the whole boundary. Only the `127.0.0.1` default bind keeps that from being reachable, and hosting for friends is precisely the case that removes it. `/debug` now requires a loopback request or a configured password, failing closed on an unknown peer. The earlier proposal to delete the blocklist and rely on the README was written without knowing the endpoint was network-facing. Raises J2, which is the same hole on every other route. |
| 2026-08-10 | **F11: the fork now runs without numpy.** `disable_numpy_random` defaults to true. Benchmarked first, since U8 had already advised irefrixs to do this without checking the cost: the bundled shuffle is 34.5× slower per call but a whole game makes a handful of draws (2 at solo setup, 6 at four players), so the real cost is roughly 20 ms across a long game, and `RandomChoice` is 4.4× *faster* because numpy rebuilds an object array per call. Verified by making numpy unimportable and setting up a full game. Flipping first required giving the bundled backend undo support: `Random.Undo` had a bare `pass` there, so the switch would have silently broken the `Unshuffle` cheat. Closes F2, and the half of F3 about numpy's process-global state. |
| 2026-08-10 | **F10 implemented.** The bundled generator now reproduces numpy operation for operation: masked rejection instead of float scaling, Fisher-Yates instead of `10n` swaps, and `replace=False` as a truncated full shuffle. Stamp versioned to `mt19937-v2` with the old value refused by name, and `CheckSceneBackend` re-framed from "does the backend match" to "can this build reproduce that sequence". 11 new tests including an end-to-end check that both backends deal the same opening hand at seed 42. Every local scene is stamped `numpy` so nothing on disk is invalidated. F3's premise test inverted as a consequence. Not yet cut as a `pr/` branch: it depends on F3's stamp, so it cannot sit directly on `upstream/master` the way the others do. |
| 2026-08-10 | Upstream replied to both issues. Project declared **sunset**, no features or PRs, urgent bugfixes case-by-case, which supersedes the earlier "happy to accept your PR." F1 state-capture cleanup explicitly invited. I7 declined on design grounds, now fork-only. F3 reframed: numpy is canonical, the bundled backend was meant to reproduce it and never did. Audited the `mt19937.py` he recommended (`mggarofalo` fork) with `tools/rng_parity_check.py`: numpy-exact for seeding, raw stream, shuffle and choice, diverges only in `ChooseWithoutReplacement` because numpy truncates a full permutation. The control run also showed **our** bundled MT19937 core is byte-exact with numpy and only its `randint`/`shuffle` layer diverges, so F3 can be closed by fixing ~40 lines of ours instead of vendoring a third-party file, tracked as **F10**. U6 unblocked, U8 proposed, U2 recommended for indefinite hold. |
| 2026-08-09 | Added section I (testing): harness verified working-but-empty; documented the circularity, the tests are replays, replays are version-pinned, and replay determinism is the very property F3 shows is broken. I2 (replay-independent unit-test layer) identified as the highest-value engineering work in this document. |
| 2026-08-10 | **J13, J12, J14 added from a play session.** Playing a real game surfaced a save that silently did nothing: the game over "Save replay" button fetches a route the open-source server never registered. The reason nobody noticed is J12, the image catch-all, which answers every unclaimed path with a placeholder JPEG and a 200, so a missing route is indistinguishable from a card we lack art for. J13 is fixed and committed, J12 is fixed by registering card ids with the cache and 404ing anything else, and a sweep of every client `fetch` target found no other live endpoint without a route. J14 logs the `SO_REUSEADDR` restart papercut that cost four failed restarts during the same session. Separately, the missing itch.io `assets` folder was installed, which is what the grey scenario tiles and status cards were about; the published build ships challenge art only through `2424`, so `2425_boss_rush` has data but no art anywhere. |
| 2026-08-11 | **J15 and J16 added from play.** A blank attachment on Rhino turned out to be Concussion Blasters, which had silently given the villain retaliate 1 and was the reason allies kept dying on attack. Two defects behind it: a failed art fetch is cached in memory under the card's name and never retried, and written to disk as a fake JPEG on any failure that is not a timeout, which is already true of `assets/cache/90001.jpg` here; and `DrawText` has had its line-accumulation loop commented out since the Pillow 10 `textsize` removal, so `show_image_text: true` produces a single-colour swatch rather than the card's name and text. The fallback that existed to identify an unrenderable card has never worked. Both fixed the same day, J16 first since it is what makes any future J15 diagnose itself. J15 turned on distinguishing a definitive miss from a transient one: markers instead of fake JPEGs, retry with a per-name cap and a run-wide give-up, and a longer timeout that the give-up makes affordable. Missing art for `01096`, `01152`, `01153` and `01154` fetched into `assets/cache/`; the running process keeps its cached placeholder until restarted. `assets/cache/90001.jpg`, the one already-poisoned file, still wants deleting by hand. |
| 2026-08-13 | **J17 added from play.** A Stunned card that would not draw, and would not start drawing again after new games or server restarts. The art was fine and so was the cache; what was wrong is that the version guard answers image routes with the clean-cache *page*, at status 200, under `max-age=31536000`. One image request during a mismatch poisons that card's URL in the browser for a year, which is J15's "one bad moment becomes permanent" on the client side and J12/J13's "200 with the wrong thing" in shape. Fixed by sending guard pages `no-store` and refusing resource routes with 401/409 and a plain-text body. My first read blamed the status card leaving play, which was the wrong question: the card goes, the cache entry stays. Also confirmed while looking: J16 is working, both status placeholders render their names legibly. Separately, the three engine fixes sitting uncommitted since the previous session are now committed with tests (`9f0ac06`, `e23249f`, `5cc37a5`), each test confirmed to fail against the old behaviour, and each commit green on its own. That surfaced a new open question: the `UnitCannotDefend` fix takes Puppet Master (`55061`) from unloadable to loading with an `"AnyPlayer"` defense ban, which is broader than its text, and wants deciding. |
| 2026-08-18 | **Upstream answered the three open issues, and the answers close the contribution question.** #6: both `test_task.py` chores are intentional, the `test_` prefix is what gives VS Code a run button, and `test_zip_cards` builds the paid scripts release. His follow-up describes their whole test method for the first time, run every save through the engine, check the CRC, re-save under the new version, archive the old folder, which is recorded in section I because it confirms the circularity from their side and explains why the version bump matters to them. #7: conceded that `IsCommandSafe` is not a boundary and a whitelist would be safer, then scoped it away on the grounds that the itch.io build cannot reach the endpoint, without addressing F6c. #8: **confirmed as a real bug** and pasted the deleted `GameServerXXX.save_local`, which validates our `delete_old=False` and shows his registration used `AddAwaitGetSecurity`, a route that answers a failed version check with a 200 HTML page and would reproduce J13's symptom, so ours stays on the non-await path. No fix upstream for any of the three. U9, U10 and U11 answered, U8 passed over in silence after eight days. Section 0 revised: treat upstream as a source of answers, not a destination for patches, and close U2, U3 and U4 as upstream items. |
| 2026-08-18 | **J19 and J20 added, one fixed.** The v2 board flies an attacking card past its target, reported from play. Cause is that `animation_attack_thwart` is the one place JavaScript asserts a scene coordinate is a pixel: it writes the target's `--x`/`--y` straight into a `px` translate, which v1's 1:1 canvas made true and v2's fractional units make false. Fixed by expressing the translate in scene units with a `1px` fallback, so one string is right under both. `layout.css` claims its coordinate-consumer list is complete, and it is, for CSS; the JS consumers were never swept, so that section now points at this one. Verifying it turned up J20, which is worse and separate: `#scene .deck` positions the pile container, but v1 pins `.deck` to `left: 0; top: 0` on purpose and puts absolute coordinates on the cards inside, so under v2 a deck card is offset twice and computes to y = 1485 on an 827 px board. Left PROPOSED rather than fixed, because deleting someone's rule wants their word first. |
| 2026-08-18 | **J21 added and fixed.** Reported from play: a v2 card drops and springs back when it activates, where v1 grows it in place. Same shape as J19 and J20, a v1 rule converted onto the wrong selector, and the third one this session. The formulas were transcribed correctly and the selectors were not, so a nudge that v1 applies only to cards lifting out of a pile was being applied to every card on the board. Two pile rules the conversion had missed are restated at the same time, because removing the over-broad one is what exposed them. The pattern across all three is worth naming: converting a stylesheet rule by rule catches the arithmetic and loses the scoping, and nothing in the v2 file records which v1 selector each rule came from. The restated rules now carry a `Mirrors <file>:<lines>` comment for exactly that reason. |
| 2026-08-19 | **F8 re-scoped and H5 retracted.** F8 said cross-area targeting isolation is opt-in and H5 sized it as auditing every finder call site, the largest hidden cost in the document. Reading the path says otherwise: `CastGameArea` derives an area from the effect, `GetPlayers` filters on it explicitly, and `FindCardsOnField` defaults it from the effect rather than requiring it. The candidate set is already scoped before any finder sees it, which is why 1 of 874 `CardFinder(` constructions passing `game_area` means almost nothing. The genuine gap is the `GetAll*` family, six functions that return everything in the world by design, at 47 call sites. Also corrected: this is not PVP-only. `CreateGameArea` has one caller, Kang's stage 3, so multi-area play ships today and F8 is a live Kang question. Left unattempted because each site needs a rules judgement, not a mechanical change. |
| 2026-08-19 | **U11 added: the content layer.** Q asked whether the underlying IP matters, given the game is built on rights belonging to neither him nor the original developer. It does, and more than U5 does: a licence from irefrixs would settle the engine and leave the card text, the art, the character names and the product name exactly where they are. Recorded what the repository actually ships, since that is checkable and the rest is not: 3,524 cards of printed text tracked in `data/cards.json`, art excluded and fetched from community databases, "© MARVEL © 2019 FFG" printed on the faces themselves. Kept in the tracker rather than the README at Q's direction, on the reasoning that a prominent notice is itself a flag. |
| 2026-08-18 | **J20 fixed**, closing the third and last of the v2 conversion misses found today. Deleting `#scene .deck`'s positioning turned out to fix more than the piles: the card-count labels were riding the same double offset, which means the part-two note blaming the label rule for `#area-advanced` and `#nemesis-pool` disappearing off the right had diagnosed half the cause and converted the wrong half. It also unpinned the expanded deck browser, which the id rule had been holding at a coordinate while `deck.css` was asking for flow. Noted in passing and not fixed: `deck.css:71` puts a clicked `.deck-top` at a literal `185px`, which v1's camera shrank and v2 takes at face value. It fits the board, so it is cosmetic, but it belongs to the part-three class of raw pixel coordinates. |
| 2026-08-19 | **J22 fixed, J23 logged.** The targeting lines were the instance predicted when J19 was fixed, and reported from play a day later. Same cause as J19, JavaScript treating a scene coordinate as a pixel, but a different remedy: J19 could push the arithmetic into a CSS `calc`, and a line cannot, because a hypotenuse and an angle have to be computed in one consistent space. So the unit itself is now readable from JS as `Lib.client.sceneUnit()`, measured off a probe rather than computed, which keeps `layout.css` the only place that knows the canvas is 1920x1080. Auditing the callers of `getOffset` for the same mixing turned up J23, where `scene.ts` does not just make the mistake but writes it down as a comment. That comment is the common ancestor of J19, J22 and J23 and is worth correcting on its own. |
| 2026-08-19 | **J23 fixed**, which closes the whole family: J19, J20, J21, J22 and J23 in two days, every one a v1 rule or assumption that survived the v2 conversion with its arithmetic intact and its meaning changed. The comment in `scene.ts` that stated the misconception outright is rewritten, since it was the common ancestor of three of them. Worth recording how the last two were found, because it was not from play: J22 and J23 both came out of auditing the callers of `getOffset` after J19, and both were written down as predictions before either was reported. The audit is now complete, `getOffset` has no remaining caller that treats its result as pixels. Two measurement traps cost time and are worth knowing for the next session. `window.Scene` is not exported, so a probe that reads `window.Scene.scale` silently gets `undefined` and compares local pixels against screen ones. And the board's modules load from `/public/js/...`, so importing `/js/...` in the console gets a second, uninitialised copy of the module whose `Scene.scale` is still 0. |
| 2026-08-19 | **Audit of the v2 conversion, after J19 to J23 all turned out to be the same mistake.** Swept four surfaces rather than waiting for the next report. Every v1 rule consuming a scene coordinate, checked against `layout.css` one by one: all covered. Every v1 rule writing a scene coordinate as a literal pixel: one miss, J26. The two stylesheets v2 drops, `scene.css` and `pos-area.css`: fully reproduced apart from the `.area::after` debug outline, whose `content` is commented out so it never generates. Every JS reader of `--x`/`--y`: `move-card.ts` has seven and touches no pixels anywhere, so its arithmetic is scene-to-scene and the unit cancels; its constants come from `:root`, where both `--card-width: 127px` and `--scene-width: 1920` are scene-unit values under either layout. What the sweep did turn up is a different question with the same answer: not what v2 converted wrongly, but what v1 did in JavaScript that v2 dropped along with it. `adjustSceneScale` is the only caller of two things v2 still needs, giving J24 and J25. Also confirmed harmless: the rotation family is confined to the centre preview, since a board scheme rotates only its art through `.face .image::before` and never the card, so no board text reads sideways. `scene-3d.css` is linked by neither board page and loads on demand behind `?3d`; it carries unconverted scene coordinates, so 3D mode under v2 is presumed wrong, unmeasured and not tracked as a defect because nothing reaches it by default. |
| 2026-08-19 | **J24 fixed.** The audit's own finding, and the first defect this session that came from what v2 stopped doing rather than what it converted wrongly. `adjustSceneScale` was the only thing refreshing the preview panel rects, so under v2 they sat at zero from module load onward and the preview could never change sides. Fixing it took two attempts, and the failed one is recorded on the row because the mistake is easy to repeat: `readyState === 'loading'` is false for a deferred module script, which runs at `'interactive'`, so the guard inverted the intent. J25 and J26 stay open, both cosmetic, and J25 wants a decision rather than a patch. |
| 2026-08-19 | **J26 fixed**, leaving J25 as the only open item from the audit. The rule was half converted: the pass that did `left: 300` and `right: 150` on the expanded deck browser stopped there and left `top: 185` and `bottom: 150` from the same block of `deck.css` alone. Nothing subtle, just an incomplete edit, which is worth noting because it is the second time in this family that a conversion took one axis and dropped the other. |
| 2026-08-19 | **J25 fixed, closing the audit.** The last thing `adjustSceneScale` was still needed for is gone, so nothing v2 skips is missed any more. Written from v2's own numbers rather than ported from v1, which forced a small tidy that was overdue: the canvas dimensions were on `#scene` where only the board could see them, and are on `:root` now, with the base font size beside them as `--scene-font` so it stops being written twice. J19 to J26 are all closed. |
| 2026-08-19 | **G5 dissolved and G1 answered.** G5 asked for a game played to completion because a mid-game replay was believed unable to drive the harness. It can: six of the seven replays already on disk pass cleanly, and only a 4-input one hits the `EOFError` that the belief was built on. The real rule is I3's, that a fixture must end where nothing else is asked. So the corpus G1 needed had been sitting in `replays/` since 2026-08-09 and the browser work was never necessary. Profiled the 152-input session: 87% of runtime is one stack, `Send` into `BroadcastMessage`, and the weight inside it is effect filtering and condition checking rather than the broadcast itself. Also measured I6 in situ at 9% of runtime, against a ~0.1ms per call estimate that turned out to be 0.77ms. What this does not answer is B1: profiling a replay is not profiling undo in live four-player play, and the skip-mode blocker in the G5 postscript is still the thing standing in front of that. |
