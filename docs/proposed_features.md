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

Nothing else is tracked yet. This document was created on 2026-08-13, when `stable` became the
fork's trunk, and is waiting for the first features to be written into it.

## Decision log

| Date | Change |
| --- | --- |
| 2026-08-13 | Created, alongside `stable` becoming the fork's trunk. Seeded with N1, which is not a new idea but the deferred half of F6c: that row was closed as a decision not to fail closed, on the explicit grounds that the real fix is a feature, so it belongs here rather than sitting as a permanently open defect. |
