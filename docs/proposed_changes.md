# Proposed Changes Tracker

Running log of every proposed change to this codebase and its status. Add new items to the
table; do not delete rows — move them to `Done` or `Rejected` and keep the rationale.

**Last updated:** 2026-08-10

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

## 0. Upstream status

Checked 2026-08-10. Local `HEAD` is `2ac194a`, identical to `irefrixs/marvel-lcg@master`. No
upstream commits since 2026-08-07.

**The maintainer is active but the project is formally sunset.** irefrixs replied to both of our
issues on 2026-08-10, roughly 16 hours after they went up. He answers technical questions in
detail and engages with the substance. He is not taking contributions:

> Today we are treating the project as sunset – we're not accepting new feature updates or pull
> requests. (If you have an urgent bugfix that needs attention, let us know and we'll consider it
> on a case-by-case basis.)

That contradicts the issue #1 answer from 2026-08-05, *"we would be happy to accept your PR."*
The later statement wins, so the working assumption changes: **the door is one narrow exception
wide, "urgent bugfix," and we have to argue a fix through it rather than simply offering it.**
Everything queued below was written against the older, more open stance and needs re-aiming.

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

### Our contributions

| ID | Item | Status |
| --- | --- | --- |
| U1 | Issue #4, RNG divergence (F3) + state-capture cost (F1, F2). Posted 2026-08-09 as `hexate`. | **ANSWERED** 2026-08-10, both questions engaged, F1 cleanup invited |
| U2 | PVP feasibility issue (section H) | DRAFTED, **reconsider**, see pacing |
| U3 | Scene save/load defects (F5, F4). F5 is fixed on `pr/puzzle-save-mutation`, so this can carry a patch rather than just a report. | DRAFTED, needs re-aiming as a bug report |
| U4 | `command_validation.py` (F6) | DRAFTED, needs re-aiming as a bug report |
| U7 | Issue #5, unbounded retry in `ChooseEffects` (I7). Posted 2026-08-09 as `hexate`. Fix ready on `pr/cap-input-retries`. | **ANSWERED** 2026-08-10, **declined**, fork-only now |
| U6 | Comment on #4 correcting 34× to 18.9× in situ, and noting F9. Text in `docs/pending/issue4-comment-rng-figure.md`. | **SUPERSEDED** by U8, which folds the correction in. Do not post both. |
| U8 | Reply on #4: F1 patch as he asked for it, the `ChooseWithoutReplacement` gap in the implementation he recommended, and **F10**, which is the numpy-compatible pure-Python generator he said was intended but never built. Folds U6 in. | **POSTED** 2026-08-10 as `hexate`, [comment](https://github.com/irefrixs/marvel-lcg/issues/4#issuecomment-5243489423). Carries links to `pr/random-state-capture` and `pr/rng-numpy-parity`, both pushed to the fork. **Edited 2026-08-10 18:31 UTC**, before he replied, to correct the `AddCounter` figure and withdraw the F9 suggestion. Editing does not re-notify, so he may still hold the original by email. |
| U9 | Issue #6, `unit_test/test_task.py` commits to git and bumps the version when the suite runs (I8). Text in `docs/pending/issue-test-task.md`. | **POSTED** 2026-08-10 as `hexate`, [issue #6](https://github.com/irefrixs/marvel-lcg/issues/6) |
| U10 | Issue #7, `/debug` reaches `exec` and its auth wrapper is inactive by default (F6/F6a). Carries the fix as `pr/gate-debug-endpoint`. Text in `docs/pending/issue-debug-endpoint.md`. | **POSTED** 2026-08-10 as `hexate`, [issue #7](https://github.com/irefrixs/marvel-lcg/issues/7). The first item that plausibly meets his "urgent bugfix" exception. |

**Pacing, revised 2026-08-10.** The hold is over. He replied to both issues in detail, so the
question is no longer whether he is listening but what is worth sending.

U6 was held until there was a live conversation to attach it to. There is one now, and the #4
title still says 34×, so send the correction.

U8 is the one contact with a standing invitation behind it. He asked for the state-capture cleanup
in writing, so F1 is not an unsolicited patch. Pair it with the `ChooseWithoutReplacement` finding:
he recommended a file that is one method away from numpy parity, and that is directly useful to the
goal he stated. This is a reply to an open thread, not a new issue, so it does not spend the
"split future questions into separate issues" budget.

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

### Branch layout and how to package a contribution

| Branch | Purpose | Upstream? |
| --- | --- | --- |
| `master` | tracks `upstream/master`, never committed to directly |, |
| `work/engine-audit` | fork integration: docs, tooling, direction | never |
| `pr/<topic>` | one contribution, cut fresh from `upstream/master` | yes |

A `pr/*` branch must be based **directly on `upstream/master`**, never stacked on
`work/engine-audit` — otherwise its diff carries unrelated fork commits and stops being readable.

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
| A1 | `tsconfig.json` uses `moduleResolution: "node10"`, removed in TypeScript 7 (`error TS5108`). The install guide says `npm install -g typescript`, which now installs 7.x. | `public/js/tsconfig.json:37` | High (blocks a clean build) | PROPOSED |
| A2 | Coverage key check hardcodes Windows separators: `name.startswith("cards\\pack\\")`. On macOS/Linux paths use `/`, so `GetKeyName` returns `""` for every card and card-script coverage silently reports nothing. | `engine/profile/coverage.py:19` | Medium (dev tooling, silent failure) | PROPOSED |
| A3 | Untrusted-save guard tests `"crashs\\dl" in world.scene.path`, never matches on POSIX, so the `DebugBreak()` safety stop before `exec(cmd)` is skipped. | `game/world/cheat/cheat_cmd_helper.py:478` | Medium (debug-only, but it is a safety check) | PROPOSED |
| A4 | `IsDrivePath` only recognizes `C:\` / `C:/`. POSIX absolute paths (`/Users/...`) are not detected as drive paths, affecting the cheat command that loads a scene by absolute path. | `engine/file/manager.py:156` | Low | PROPOSED |
| A5 | `FormatPath` indexes `normalized_path[1]` without a length check → `IndexError` on a 1-character path. Platform-independent, found during the port. | `engine/file/manager.py:165` | Low | PROPOSED |
| A6 | `Beep` is a no-op on **every** platform since `winsound` was stripped, audio cues are gone, not just on macOS. Could be restored cross-platform (`afplay` on macOS, `paplay`/`aplay` on Linux) or the dead code removed. | `core/lib/beep.py` | Low | PROPOSED |
| A7 | `FileManager.EditCode` shells out to `code`; fails silently via `os.system` if the VS Code CLI is not on PATH. | `engine/file/manager.py:149` | Low | PROPOSED |
| A8 | `public/js/watch.bat` is Windows-only. A `watch.sh` companion would match the documented macOS/Linux flow. | `public/js/watch.bat` | Cosmetic | PROPOSED |
| A10 | **`.gitignore` misses `save.json`.** The rule is `/save_*.json`, which does not match `save.json`, the exact filename the debug `/save` command writes (`ex_save_name = './save.json'`, `game/cheat/cheat.py:126`). Confirmed with `git check-ignore`. One-character fix; belongs on `pr/gitignore-dev-files`. | `.gitignore:6` | Low | PROPOSED |
| A9 | **`Engine.SaveCrash` masks any startup failure.** Uses `Engine.game` (assigned at `engine.py:104`) but runs for crashes before that, so the handler itself raises `AttributeError` and hides the real exception. Found by `kmelkon` in #1; PR #2 was closed unmerged and this piece never landed. | `engine/engine.py:159-162` | Medium | **DONE**, `pr/guard-savecrash`, credit kmelkon |

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

**Open question for Q:** is finishing a 3,400-script migration realistic for this fork, or is the
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
own codebase and standards. Do not treat it as a scoped estimate for this fork.

---

## C. Build and tooling

| ID | Item | Severity | Status |
| --- | --- | --- | --- |
| C1 | No pinned dependency versions, `requirements.txt` lists bare package names. A lockfile or version floors would make builds reproducible. | Medium | PROPOSED |
| C2 | No CI. Repo has `unit_test/` and `game/test/` but nothing runs them automatically. | Medium | PROPOSED |
| C3 | Compiled JS is gitignored and must be built before first run; there is no build script wrapping the Python + TypeScript steps. | Low | PROPOSED |

---

## D. Security

Carried over from the README's own warning: the engine `exec`s Python card scripts, so any
third-party card pack is arbitrary code execution. `engine/security/command_validation.py`
maintains a module blocklist (`subprocess`, `webbrowser`, `win32api`, …).

| ID | Item | Severity | Status |
| --- | --- | --- | --- |
| D1 | Assess whether `command_validation.py`'s blocklist approach is sound, or whether it is bypassable (blocklists usually are). This governs the safety of the whole custom-card ecosystem. | High | PROPOSED, needs audit |
| D2 | A3 above (the `crashs\\dl` guard) is part of this surface, the downloaded-save safety break does not fire on POSIX. | Medium | PROPOSED |

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
| F8 | Cross-area targeting isolation is opt-in, not enforced | `game/card/card_finder/checker.py:174` | Medium (blocks PVP) | PROPOSED |

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
| F6a | Gate `/debug` on loopback or a real password | **DONE**, `pr/gate-debug-endpoint`, reported upstream as [issue #7](https://github.com/irefrixs/marvel-lcg/issues/7) (U10) |
| F6b | Rename `command_validation.py` and its docstring so it stops implying a security control | PROPOSED |
| F6c | The same no-password-means-authenticated hole applies to **every** route using `IsAuthenticate`, not just `/debug`. Tracked as J2, and it is worth more than its Medium rating | PROPOSED |

---

## J. Second-pass defect audit (2026-08-09)

Deeper sweep after §F, targeting areas the first pass skipped: exception handling, concurrency,
web auth, save integrity. Ordered by how much they matter.

| ID | Finding | Location | Severity | Status |
| --- | --- | --- | --- | --- |
| J1 | Bare `except:` can silently drop a card ability | `game/card/face/effect/face_effect.py:55` | Medium (see measurement) | **DONE**, `pr/narrow-effect-filter-except` |
| J2 | `/authenticate` issues a cookie without checking the password, and 500s on a malformed body. **Not a bypass**, ✓ VERIFIED: the check happens later in `IsAuthenticate` and a wrong guess is refused | `engine/network/web_server.py:254` | Medium | **DONE**: verifies, 401/400, constant-time compare, warns when serving off-machine with no password |
| F6c | `IsAuthenticate` returns `True` for every caller when no password is configured, which is the shipped default, so every `*Security` route is open to anyone who can reach the port. The real exposure behind J2 | `engine/network/web_server.py:81` | **High** | PROPOSED, needs a decision: failing closed breaks multiplayer for anyone who never set a password |
| J3 | Save checksums default to ignored, and load proceeds on mismatch | `engine/lib/json.py:179` | Medium | PROPOSED |
| J4 | `JobManager.Simultaneous` is a sequential loop | `engine/job/manager.py:76` | Medium | PROPOSED |
| J5 | `RemoveJob` check-then-act race from worker threads | `engine/job/manager.py:43` | Low | PROPOSED |
| J6 | 519 `assert`s enforce game rules; `python -O` deletes them | engine-wide | Low, latent | PROPOSED |
| J7 | Mutable default arguments (10 sites) | various | Low, latent | PROPOSED |
| J8 | **Clicking Cancel on the End Phase prompt raises.** Reproduced in a real browser game. | `engine/controller/controller.py:274` | Medium, user-reachable | PROPOSED |
| J9 | **`-no_<flag>` on the command line is silently ignored for any already-declared variable.** `ParseArguments` writes the stripped name into `instance_command` but then calls `InitVariable(key)` with the `no_` prefix still attached, so the lookup misses `variable_dict` and nothing re-reads the value. The positive form works, because there the key matches. ✓ VERIFIED: `-no_disable_numpy_random` left the flag at its default, which is how the F10 tests nearly measured the wrong backend. Two-line fix, strip before the lookup | `engine/config.py:153-163` | Medium, silent | PROPOSED |

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

519 `assert` statements across `core/`, `engine/`, and `game/`, many of them validating game rules
rather than checking internal invariants. Python's `-O` flag removes every one. Nothing in the
repo currently sets it, so this is latent rather than live, but a PyInstaller spec or a packaging
tweak is all it would take to ship a build whose rule checks are absent.

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
| G1 | **Profile a real session.** See the attempt log below. | The single number that decides E1. Everything in B1 and E is inference until this exists. | **BLOCKED**, driver cannot sustain a long game |
| G2 | Determine when `DoNotCheckFastUndo()` disables the fast-undo pruning path in `engine/controller/module/undo.py`, and how much that path actually saves. | If fast-undo is silently off in normal multiplayer, the reported "over a minute" may be a bug, not a design limit. | PROPOSED |
| G4 | Record a real game through the browser and save the replay. | The synthetic driver stalls; a human-played scene sidesteps that entirely. | **DONE**, see below |
| G5 | Play a game **to completion** in the browser and save that. Attempted 2026-08-09 and abandoned, see the attempt note below. A mid-game replay cannot drive the test harness: it replays the recorded inputs and then asks for input N+1, which the debug device answers with `input()` and an `EOFError`. Fixtures have to be finished games. | The remaining blocker on G1. | PROPOSED |
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
| H5 | **Area isolation is opt-in (= F8)** | `world.py:52-55` comments claim cards/targeting cannot cross areas, but `CardFinder.game_area` defaults to `None` and only **11** call sites pass it. Harmless in co-op (one area); a correctness requirement in PVP. Auditing every finder call site is likely the largest hidden cost. | **Large, the sleeper** |
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
| I1 | Empty corpus fails with a bare `AssertionError` at `unit_test/entry.py:48` instead of reporting "no test cases found". Trivial fix, saves the next person an hour. | PROPOSED |

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
| I4 | Commit `launch-debug.json.example` and `.gitkeep` files for `replays/min_test/` and `replays/profiles/`, plus a short note in the docs. | Every newcomer hits the same wall; kmelkon and we both did. Good upstream contribution. | PROPOSED |

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
player data upstream will not take. Anyone cloning this fork starts with an empty `min_test` and
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
| I8 | **`unit_test/test_task.py` is not a test file and running the suite mutates your repository.** `test_IncreaseVersion` bumps `BUILD` in `build.py` and then runs `git add` and `git commit` through `os.system` (`build_marvel.py:19-20`); `test_zip_cards` writes a `cards-*.zip` into the repo root. Its own comment says *"Just use as a work, to help me increase the version number."* ✓ VERIFIED the hard way on 2026-08-10: running the standalone suite three times left three `Package version` commits on the work branch and pushed this fork's version from `0.5.9.201` to `204`, which matters because `Scene.GetSaveFileName` stamps the version into every save file. Anyone who runs `python -m unittest` across `unit_test/` gets the same surprise. Rename it out of the `test_` namespace, or guard it behind an explicit opt-in. Good upstream contribution, and cheap. | **REPORTED** as issue #6 (U9), fix offered but not written |
| I6 | `WorldRender.CalculateCRC()` runs on **every** `ChoiceOne` (`controller.py:54`) and walks every card calling `GetRenderInfo()`. Measured ~0.1 ms per call. Harmless per decision, but it is unconditional, including during skip/replay, where nothing renders. Worth checking against B1. | PROPOSED |

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
