# Proposed Changes Tracker

Running log of every proposed change to this codebase and its status. Add new items to the
table; do not delete rows — move them to `Done` or `Rejected` and keep the rationale.

**Last updated:** 2026-08-09

## Status legend

| Status | Meaning |
| --- | --- |
| `PROPOSED` | Identified, not yet agreed to |
| `ACCEPTED` | Agreed, not started |
| `IN PROGRESS` | Being worked on |
| `DONE` | Implemented and verified (note *how* it was verified) |
| `REJECTED` | Decided against — keep the reason |
| `BLOCKED` | Waiting on something external |

## Evidence markers

Claims in this doc are marked so we know what has actually been checked:

- ✓ **VERIFIED** — file read and/or behavior observed at runtime
- ? **INFERRED** — from grep/search only, not confirmed by reading
- ✗ **UNVERIFIED** — asserted, not yet checked

---

## 0. Upstream status

Checked 2026-08-09. Local `HEAD` is `2ac194a`, identical to `irefrixs/marvel-lcg@master`.

**The maintainer is active.** Despite the 2026-07-31 discontinuation post, irefrixs answered
issues in detail on 2026-08-05 and pushed commits on 2026-08-07.

### Already answered upstream — do not re-ask

| Topic | Answer | Source |
| --- | --- | --- |
| License | "Considering Apache License 2.0, no final decision yet." No `LICENSE` file exists. | issue #1 |
| Community builds | Welcome, even pre-license. Credit as *"originally developed by the Irefrixs Team"* explicitly approved. | issue #3 |
| Contributions | "We have not finalized our contribution policy… we would be happy to accept your PR." | issue #1 |
| Test corpus | Cannot be shared — player-uploaded, >1 GB, kept off Git on a shared disk. | issue #1 |
| `launch-debug.json` | Developer-local file, intentionally not committed. Copy `launch.json`. | issue #1 |
| Issue etiquette | **"Split future questions into separate issues"** — an explicit request. Honor it. | issue #1 |

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
| **`Engine.SaveCrash` masks startup errors** | ✗ **not applied** — see A9 |

### Our contributions

| ID | Item | Status |
| --- | --- | --- |
| U1 | Issue #4 — RNG divergence (F3) + state-capture cost (F1, F2). Posted 2026-08-09 as `hexate`. | **POSTED** — awaiting reply |
| U2 | PVP feasibility issue (section H) | DRAFTED — hold until #4 gets a reply or ~1 week |
| U3 | Scene save/load defects (F5, F4) | DRAFTED — send a few days after U2 |
| U4 | `command_validation.py` (F6) | DRAFTED — send with U3 |

Drafts live outside the repo in the session scratchpad (`issues_draft.md`).

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
| U5 | **No `LICENSE` file exists.** Absent one, default copyright is "all rights reserved"; the issue-#3 comment is strong evidence of intent but is not a license grant with terms. Low risk for private/hobby work, real risk before any distribution or commercial use. He has already named Apache 2.0, so the ask is "please commit the file," not a new question — offer to send it. | PROPOSED |

**Fork discipline** — keep changes cherry-pickable, since he applies diffs rather than merging PRs:

- one topic branch per tracker item, small and self-contained
- keep upstream-contributable fixes (F1–F6, A9, I1, I4) separate from fork-only direction (I2, PVP)
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
| A3 | Untrusted-save guard tests `"crashs\\dl" in world.scene.path` — never matches on POSIX, so the `DebugBreak()` safety stop before `exec(cmd)` is skipped. | `game/world/cheat/cheat_cmd_helper.py:478` | Medium (debug-only, but it is a safety check) | PROPOSED |
| A4 | `IsDrivePath` only recognizes `C:\` / `C:/`. POSIX absolute paths (`/Users/...`) are not detected as drive paths, affecting the cheat command that loads a scene by absolute path. | `engine/file/manager.py:156` | Low | PROPOSED |
| A5 | `FormatPath` indexes `normalized_path[1]` without a length check → `IndexError` on a 1-character path. Platform-independent, found during the port. | `engine/file/manager.py:165` | Low | PROPOSED |
| A6 | `Beep` is a no-op on **every** platform since `winsound` was stripped — audio cues are gone, not just on macOS. Could be restored cross-platform (`afplay` on macOS, `paplay`/`aplay` on Linux) or the dead code removed. | `core/lib/beep.py` | Low | PROPOSED |
| A7 | `FileManager.EditCode` shells out to `code`; fails silently via `os.system` if the VS Code CLI is not on PATH. | `engine/file/manager.py:149` | Low | PROPOSED |
| A8 | `public/js/watch.bat` is Windows-only. A `watch.sh` companion would match the documented macOS/Linux flow. | `public/js/watch.bat` | Cosmetic | PROPOSED |
| A9 | **`Engine.SaveCrash` masks any startup failure.** Uses `Engine.game` (assigned at `engine.py:104`) but runs for crashes before that, so the handler itself raises `AttributeError` and hides the real exception. Found by `kmelkon` in #1; PR #2 was closed unmerged and **this piece never landed**. Still present at `engine/engine.py:161`. | `engine/engine.py:159-162` | Medium | PROPOSED — credit kmelkon |

### Not defects — documented for the next person

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
| B1 | **Runtime performance.** Python backend is "fast for development, but slow at runtime." UNDO in 4-player can take over a minute. | Critical | PROPOSED — needs profiling before any fix |
| B2 | **Function registration instead of Buff.** Centralized registered functions are easy to review but hard to serialize, which is what makes UNDO impractical. A `Buff` replacement was started and never finished. | Critical | PROPOSED — partial migration exists |
| B3 | **New FFG PVP rules.** The engine was not built to accommodate them; upstream estimated ~300 hours of refactor and expected many hard-to-find bugs. | Large feature | PROPOSED |

### B1 — UNDO cost

✓ VERIFIED (mechanism, not timing). Undo is implemented as *replay from the beginning*, not as
state rollback:

- `game/scene/` records the full list of player `inputs` for the session.
- `engine/controller/manager.py:50-89` — on a start-state with `is_undo`, the manager reloads the
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

Note `engine/task/manager.py` gates threading behind `enable_multiple_threads`, default `False`.
✗ UNVERIFIED — whether enabling it helps, or why it is off.

### B2 — Buff migration is barely started

✓ VERIFIED by count:

- **3,457** card scripts under `cards/pack/` (excluding `__init__.py`)
- **15** of them reference `Buff` at all

So the migration upstream described as "started" covers well under 1% of card scripts. The
infrastructure exists and is small:

- `game/buff/buff.py` — `Buff` base class: `by_effects` list, `OnGain`/`OnLost`, `OnRoundEnd`,
  `OnRecordPlayedFace`, UI text. Concrete buffs like `BuffIsTreatAsIfBlank` subclass it.
- `game/buff/manager.py` — `BuffManager.RegisterBuffer(type)`, forwards round-end and
  played-face events.
- `game/card/face/component/buffs.py` — card-face integration.

This is the single largest lever on B1: buffs are declarative state that can be serialized and
rolled back, whereas registered closures cannot. Any UNDO redesign probably depends on this
landing first.

**Open question for Q:** is finishing a 3,400-script migration realistic for this fork, or is the
better play a compatibility shim that lets both mechanisms coexist and converts scripts lazily as
they are touched?

### B-measure — Codebase size and measured performance (2026-08-09)

Taken to inform the "fix in Python vs. port to another language" decision.

**Size** (Python, excluding `__pycache__`):

| Area | Lines | Files | Nature |
| --- | --- | --- | --- |
| `cards/` | 102,461 | 3,859 | Card rules content — **63% of the Python codebase** |
| `game/` | 53,169 | 326 | Rules engine |
| `engine/` | 5,883 | 68 | Platform: web server, tasks, file I/O, config |
| `core/` | 666 | 16 | Utilities |
| `public/js/` | 10,535 | 38 | TypeScript frontend (language-independent; talks HTTP) |

**Measured** ✓ VERIFIED — macOS, Python 3.13.12, Apple Silicon:

| Measurement | Result |
| --- | --- |
| Config + `CardsDB.Initialize()` | 0.32 s |
| Import all 3,457 card scripts | 0.89 s total, 0.26 ms each, 0 errors |
| Card scripts loaded at startup | 0 — imports are lazy |

**Design note** ✓ VERIFIED: `game/event/manager.py` indexes effects as
`self.effects[category][message_type][priority]`. Dispatch is a dict lookup by message type, not
a linear scan over all registered effects. The hot path is not naively designed.

**Still unmeasured** ✗ — per-action game-logic time in a real multiplayer session. The repo ships
a replay-based test harness (`unit_test/entry.py`, `game/test/test_run.py`) that already reports
`Average Time` per input, but **no test scenes ship** — `Test.GetTestCases` reads from
`REPLAY_FOLDERS` (`./replays/`), which is absent. This is the one number that would settle B1.
See G1.

### B3 — PVP rules

✗ UNVERIFIED — no audit yet of what specifically in the engine assumes co-op (single villain,
shared encounter deck, non-adversarial targeting). The ~300h estimate is upstream's, for their
own codebase and standards. Do not treat it as a scoped estimate for this fork.

---

## C. Build and tooling

| ID | Item | Severity | Status |
| --- | --- | --- | --- |
| C1 | No pinned dependency versions — `requirements.txt` lists bare package names. A lockfile or version floors would make builds reproducible. | Medium | PROPOSED |
| C2 | No CI. Repo has `unit_test/` and `game/test/` but nothing runs them automatically. | Medium | PROPOSED |
| C3 | Compiled JS is gitignored and must be built before first run; there is no build script wrapping the Python + TypeScript steps. | Low | PROPOSED |

---

## D. Security

Carried over from the README's own warning: the engine `exec`s Python card scripts, so any
third-party card pack is arbitrary code execution. `engine/security/command_validation.py`
maintains a module blocklist (`subprocess`, `webbrowser`, `win32api`, …).

| ID | Item | Severity | Status |
| --- | --- | --- | --- |
| D1 | Assess whether `command_validation.py`'s blocklist approach is sound, or whether it is bypassable (blocklists usually are). This governs the safety of the whole custom-card ecosystem. | High | PROPOSED — needs audit |
| D2 | A3 above (the `crashs\\dl` guard) is part of this surface — the downloaded-save safety break does not fire on POSIX. | Medium | PROPOSED |

---

---

## F. Design audit findings (2026-08-09)

First pass over the core systems. Ordered by severity. Everything here was read or executed —
no grep-only claims.

| ID | Finding | Location | Severity | Status |
| --- | --- | --- | --- | --- |
| F1 | RNG state capture costs 34× and leaks unboundedly | `engine/lib/random.py:49,68,78` | **High** | PROPOSED |
| F2 | `numpy.random.choice` on object lists is 39× slower than stdlib | `engine/lib/random.py:45-70` | Medium | PROPOSED |
| F3 | Two RNG backends produce different sequences → replay incompatibility | `engine/lib/random.py` | **High** | PROPOSED |
| F4 | `World.LoadFromJson` is dead *and* cannot execute | `game/world/world.py:121-144` | Medium | PROPOSED |
| F5 | Saving a puzzle mutates the live replay log; second save raises | `game/scene/scene.py:113-117` | **High** | PROPOSED |
| F6 | Debug-console safety check is a bypassable blocklist | `engine/security/command_validation.py` | **High** | PROPOSED |
| F7 | Player count hardcoded as `(0,1,2,3)[:n]` | `game/world/world.py:94,127` | Low | PROPOSED |
| F8 | Cross-area targeting isolation is opt-in, not enforced | `game/card/card_finder/checker.py:174` | Medium (blocks PVP) | PROPOSED |

### F1 — RNG state capture: 34× slowdown and an unbounded leak

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

**Proposed fix:** capture state only when the debug-undo cheat is armed. Better, store
`(seed, counter)` — `Random.counter` is already maintained — and recover a prior state by
reseeding and fast-forwarding, which is O(1) memory.

### F3 — Two RNG backends, one save format

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

**Proposed fix:** commit to one backend, record it in the scene metadata, and refuse to replay a
scene recorded under a different one. Prefer the bundled MT19937 — it is self-contained and not
process-global. This is a prerequisite for trusting saves at all.

### F4 — `World.LoadFromJson` is dead and non-functional

✓ VERIFIED. Zero callers anywhere in the repo. It also cannot run:

- Line 127: `for i in (0, 1, 2, 3)[:world_descriptor.players]` — slices a tuple by
  `world_descriptor.players`, which is `List[PlayerDescriptor]`
  (`game/render/descriptor/world.py:61`). `TypeError` on entry.
- Lines 136 and 139: `CardFactory.GenerateCard(card.card_id, self.players[0].player_deck, self)`
  uses `players[0]` inside a loop over `i` — every player's cards would go to player 0.

Chesterton's fence applies, but the fence is provably not holding anything up: it has no callers
and raises immediately. Delete it, or fix and test it.

### F5 — Saving a puzzle corrupts the in-memory replay log

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

**Proposed fix:** deep-copy the inputs before stripping.

### F6 — The command blocklist blocks only the naive case

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

**Proposed fix:** either delete it and rely on the README's honest warning, or replace it with a
real boundary (separate process, restricted import hook, capability-limited API). A blocklist of
module names is not a security control. Decide which — the current state is the worst of both.

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
| E1 | Decision: remain on Python; treat B1 as an algorithmic fix (snapshot/rollback) rather than a rewrite. | PROPOSED — pending G1 |
| E2 | If a CPU wall is later confirmed, evaluate in-language escape hatches first: PyPy, and the existing `enable_multiple_threads` flag (`engine/task/manager.py`, default `False` — reason for the default is ✗ UNVERIFIED). | PROPOSED |

---

## G. Gates — do these before committing to a direction

| ID | Item | Why it blocks | Status |
| --- | --- | --- | --- |
| G1 | **Profile a real session.** Play a game via the web UI; it auto-saves into `./replays/`. Then run `test_min` and read the harness's `Average Time` per input. Extrapolate undo cost. Path is now unblocked — see section I. | The single number that decides E1. Everything in B1 and E is inference until this exists. | **ACCEPTED — unblocked** |
| G2 | Determine when `DoNotCheckFastUndo()` disables the fast-undo pruning path in `engine/controller/module/undo.py`, and how much that path actually saves. | If fast-undo is silently off in normal multiplayer, the reported "over a minute" may be a bug, not a design limit. | PROPOSED |
| G3 | ~~Ask upstream for a replay corpus.~~ | Asked and answered in issue #1: cannot be shared (player-uploaded, >1 GB, off-Git). Superseded by I3 — author our own. | **REJECTED** |

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
- `Scenario.GetVillain(game_area)` is **already area-aware** — per-area villains work today

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
| H5 | **Area isolation is opt-in (= F8)** | `world.py:52-55` comments claim cards/targeting cannot cross areas, but `CardFinder.game_area` defaults to `None` and only **11** call sites pass it. Harmless in co-op (one area); a correctness requirement in PVP. Auditing every finder call site is likely the largest hidden cost. | **Large — the sleeper** |
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
| I2 | **Build a unit-test layer that does not go through replay.** Construct a `World` directly, drive it with the existing debug commands (`gain`, `play`, `can`, `cannot` — documented in `public/js/marvel/debug/debug.ts`), assert on state. Independent of replay determinism, and survives behavior changes. | Breaks the circularity. Prerequisite for touching B2 or H5 safely. | PROPOSED |
| I3 | **Author a small replay corpus ourselves.** Play a few games; scenes auto-save to `./replays/`. Version-stamp them and accept they need regeneration on behavioral change. | Enough for G1 profiling and coarse smoke tests. Cheap. Do this first. | PROPOSED |
| I4 | Commit `launch-debug.json.example` and `.gitkeep` files for `replays/min_test/` and `replays/profiles/`, plus a short note in the docs. | Every newcomer hits the same wall; kmelkon and we both did. Good upstream contribution. | PROPOSED |

**Sequence:** I3 (unblocks G1 today) → I1 + I4 (trivial, contributable) → I2 (the real fix, and a
prerequisite for B2).

### I2 progress log (2026-08-09)

`unit_test/harness.py` and `unit_test/test_harness.py` are written. **The first test does not pass
yet** — one blocker remains. Three were found and fixed along the way, and two are upstream bugs
worth reporting on their own.

| # | Blocker | Resolution |
| --- | --- | --- |
| 1 | `KeyInput.IsInputReady` calls `input()` and blocks — the replay log is the engine's only non-human input source. | Wrote `ScriptedInput`, an `InputDevice` that answers from a policy. This was the missing primitive. ✓ |
| 2 | Start state `'InTesting'` turns skip mode on (`manager.py:74-77`); with skip on, `ChoiceOne` **discards the device's answer** and substitutes `convert_fallthrough_input` (`controller.py:158-159`), which is `"{}"` when no replay inputs exist. Same prompt repeated ~296k times in 60 s. | Use start state `'New'`, which takes the `is_new` branch and leaves skipping off. ✓ |
| 3 | **`ConsoleDevice` never implements `IsSyncReady`** — it inherits the abstract stub at `engine/device/base/output.py:17`, which returns `None`. `DoWaitSync` waits on that with `timeout=None`, so the first `Present()` deadlocks: main thread in `JobManager.WaitForAllJobsToComplete`, render job in `DoWaitSync`. Invisible in the replay harness because `world_render.py:114` only calls `WaitSync` when not skipping, and replay always skips. | Wrote `ScriptedOutput` with `IsSyncReady() -> True`. ✓ |
| 4 | Mulligan prompt repeated forever — 455k `ChoiceOne` calls in 90 s, no exception raised. Root cause: `DoGetInput` appends the player to `manager.asking_players` before waiting and returns **`None`** if they are still in that list on wake (`base.py:113`). `ChoiceOne` maps a `None` input to `return None, True` (the "cheat" flag) and `ChooseEffects` loops on `cheat` (`player_action.py:178`). Setting `payload.input_json` directly — the way `KeyInput` does it — never clears `asking_players`. | Answer via `manager.WhenInput(answer, player_id)`, which is what the web client calls: it removes the player from `asking_players`, stores the answer, and notifies. ✓ |

**Status: I2 is working.** `unit_test/test_harness.py` passes — 2 tests, 0.27 s total, no fixture on
disk. A full game (Peter Parker vs Rhino on *The Break-In!*, 6-card hand, 34-card deck) builds in
**0.22 s**, and the debug DSL drives it (`Gain('Enhanced Reflexes')` verified to land in hand).

That runtime matters: it is fast enough for a real TDD loop, which the replay harness never was.

| ID | Item | Status |
| --- | --- | --- |
| I7 | **`ChooseEffects` retries without bound.** `while True: … if cheat: continue` (`game/player/action/player_action.py:165-181`) has no iteration cap, no backoff, and no bail-out. A device that consistently fails to deliver input spins at ~5,000 iterations/sec indefinitely, silently. With a human web client this is the intended "show the error, let them re-enter" path; with any automated device it is an unkillable hang. A retry cap that raises after N attempts would have turned three of the four blockers above into instant, self-explanatory failures. | PROPOSED |

| ID | Item | Status |
| --- | --- | --- |
| I5 | **The console/keyboard device cannot drive a live game — two independent bugs.** (a) `ConsoleDevice` never implements `IsSyncReady`, so the first render sync deadlocks (only `WebDevice` implements it, `web_device.py:36`). (b) `KeyInput` sets `payload.input_json` directly instead of calling `WhenInput`, so `DoGetInput` always returns `None` and the caller retries forever (blocker 4). Neither surfaces in the replay harness: the sync call is guarded by `world_render.py:114`, which only runs when **not** skipping, and replay supplies inputs so `IsInputReady` is never reached. **Low practical severity** — nobody plays by typing JSON at a terminal — but the `-device` non-web path is dead code, and it blocks anyone building a headless mode. Report as a note, not a defect. | PROPOSED |
| I6 | `WorldRender.CalculateCRC()` runs on **every** `ChoiceOne` (`controller.py:54`) and walks every card calling `GetRenderInfo()`. Measured ~0.1 ms per call. Harmless per decision, but it is unconditional — including during skip/replay, where nothing renders. Worth checking against B1. | PROPOSED |

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
| 2026-08-09 | Added section F (design audit, F1–F8 — RNG leak measured, dead code, puzzle-save corruption, bypassable blocklist verified by execution) and section H (PVP feasibility, revises B3 downward — multi-board isolation already exists and ships in the Kang scenario). |
| 2026-08-09 | Added section 0 (upstream status): maintainer is active, license/contribution/test-corpus questions already answered publicly, prior work by kmelkon logged. Added A9 (kmelkon's `SaveCrash` fix never landed). Posted issue #4 upstream (U1). G3 **rejected** — corpus cannot be shared. G1 unblocked. |
| 2026-08-09 | Added section I (testing): harness verified working-but-empty; documented the circularity — the tests are replays, replays are version-pinned, and replay determinism is the very property F3 shows is broken. I2 (replay-independent unit-test layer) identified as the highest-value engineering work in this document. |
