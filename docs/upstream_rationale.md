# Upstream Rationale: Why This Was Open-Sourced

Reference copy of the original developer's discontinuation announcement, plus a code-level
cross-check of each technical reason given. Tracked items derived from this live in
[`proposed_changes.md`](proposed_changes.md) section B.

**Source:** irefrixs, *"Marvel Champions: Digital Edition — The Final Update"*
Published 2026-07-31 on itch.io
<https://irefrixs.itch.io/marvel-lcg/devlog/1610250/marvel-champions-digital-edition-the-final-update>

The GitHub open-sourcing commit (`47e9866 Open source initial commit`) matches this announcement
in timing.

> **Update 2026-08-09 — "discontinued" does not mean "gone."** irefrixs answered GitHub issues in
> detail on 2026-08-05 and pushed commits on 2026-08-07, both after the final devlog. Treat him as
> an active, responsive maintainer who has stopped adding features — not as someone who has left.
> Current engagement status and everything he has already answered publicly is tracked in
> [`proposed_changes.md` §0](proposed_changes.md#0-upstream-status).

---

## The three technical reasons, verbatim

> - This game uses Python as the backend. It's fast for development, but slow at runtime. You
>   might notice this issue when you play with friends (4-player mode). For example, taking an
>   UNDO can take more than a minute. We tried to optimize it, but it's still not good enough.
>
> - While building this game, in many cases we used function registration instead of creating a
>   buff. This approach is great for development: it keeps logic centralized and makes code review
>   easier. However, it's very difficult for serialization. The game records players' actions and
>   replays/processes them through the game logic. This is good for replay, but not for a simple
>   UNDO feature. We started using Buff to replace registered functions, but there are too many
>   card scripts, and it's really hard to refactor everything in a safe and complete way.
>
> - In the new Marvel release, FFG created a new PVP rule. This engine was built without fully
>   considering changes like that. Implementing it would require a huge refactor, around 300
>   hours. It also means the new version could introduce many bugs that are difficult to find.
>   Instead of repeatedly patching the old engine, creating a new engine would be the better
>   choice.

On the open-sourcing itself:

> We know this might feel like an ending, but it doesn't have to be the end of your journey with
> the game. We didn't want to simply step away. So we prepared a new version on GitHub and opened
> the project so the community can still build, extend, and improve.
>
> This repository includes the game's source code, along with a Card Editor and a Debug Console.
> It also includes documents explaining how to add a new card. You can check the repository to
> learn how the engine works and how to run the game on Linux or Termux. Both only require a
> Python environment.

Note the platform framing: **Linux and Termux are the platforms upstream mentions. macOS is not
named anywhere in the announcement** — though the `docs/install_guide.md` fix on 2026-08-07
(commit `2ac194a`) added macOS build steps after the fact.

## Context from the same post

- First published ~2 years before the announcement; grew out of wanting a LUA helper script for
  Tabletop Simulator, then "why not make the whole experience ourselves?"
- First prototype: ~1 month, console-only, no UI.
- Community reached 1000+ downloads.
- Last regular release before the finale was `Changelog 0.5.9.200` (2026-05-04); the repo sits at
  `0.5.9.201`.
- Sign-off: *"AND SEE YOU NEXT GAME! Irefrixs Team."*

---

## Cross-check against the code

Done 2026-08-09. Detail and open questions are in
[`proposed_changes.md` §B](proposed_changes.md#b-architectural-issues-cited-by-the-original-developer).

| Claim | Finding |
| --- | --- |
| UNDO is slow | ✓ **Mechanism confirmed.** Undo is replay-from-the-start, not state rollback (`engine/controller/manager.py:50-89` reloads the scene, replays `scene.inputs`, fast-forwards via `skip`). Cost is O(actions-so-far) of real game logic per undo. A "fast undo" effect-pruning cache exists in `engine/controller/module/undo.py`. Timings not measured. |
| Buff migration incomplete | ✓ **Confirmed, and it is barely started.** 3,457 card scripts under `cards/pack/`; **15** reference `Buff`. Infrastructure (`game/buff/buff.py`, `game/buff/manager.py`, `game/card/face/component/buffs.py`) is in place and small. |
| Engine can't take PVP | ✗ **Not yet audited.** No review done of co-op assumptions (single villain, shared encounter deck, targeting). |

### He restated the PVP position after open-sourcing

In GitHub issue #1 (2026-08-05), unprompted:

> this engine still has significant limitations. For example, it is not capable of handling
> features such as PvP properly. We are sharing the project primarily for people who are
> interested in learning how we built the game.

So this is a settled belief on his side, not an off-hand line in a farewell post. Section H of
[`proposed_changes.md`](proposed_changes.md) disputes it on the evidence — `GameArea` isolation
already exists and ships in the Kang scenario — and that disagreement is queued as a respectful
follow-up issue (U2), deliberately framed as information rather than argument.

### One caveat worth carrying forward

The devlog attributes the UNDO problem to "Python … slow at runtime." The code says the dominant
cost is *algorithmic* — replaying the entire session on every undo — which no change of language
fixes. If that holds under profiling, snapshot/rollback state (which is what finishing the Buff
migration enables) is the real fix, and a rewrite in a faster language would be treating the
symptom. This should be settled with a profile before anyone commits to a direction.

**Sources:**

- [Marvel Champions: Digital Edition — The Final Update (devlog, 2026-07-31)](https://irefrixs.itch.io/marvel-lcg/devlog/1610250/marvel-champions-digital-edition-the-final-update)
- [Marvel Champions: Digital Edition on itch.io](https://irefrixs.itch.io/marvel-lcg)
- [Devlog index](https://irefrixs.itch.io/marvel-lcg/devlog)
