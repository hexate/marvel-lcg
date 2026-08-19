The open-source of Marvel LCG digital version on [ITCH](https://irefrixs.itch.io/marvel-lcg)

## About this project

This is [hexate/marvel-lcg](https://github.com/hexate/marvel-lcg), where the digital Marvel LCG
carries on. The game was originally developed by the Irefrixs Team and open-sourced in July 2026.
[irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg) declared the project sunset on
2026-08-10 and is no longer taking changes, so continued work happens here.

You are reading `main`, the trunk: the original game plus a stabilization pass and the work since.
Crash fixes, a working save, a replay-independent test suite, a rebuilt board layout, a one-command
build. See [CHANGELOG.md](CHANGELOG.md) for what changed and why.

### Upstream

Read it, do not send to it. Across five issues the original maintainer answered in detail, conceded
the technical point most times, and acted on none of them, including one he called "an actual bug in
the open-source version". Three replies end with a variant of "feel free to change it in your fork".
He remains the best source on why the code is the way it is, and that is worth a great deal: the
history behind the RNG, the save format and the test method all came from asking him.

`master` is a pinned mirror of upstream and is never committed to, because the
`compare/master...pr/x` links in those issues read against it. The `pr/*` branches are the record of
what was offered and declined. No new ones are cut. Branch layout is in
[docs/proposed_changes.md](docs/proposed_changes.md).

### One caveat before you build on this

There is no `LICENSE` file, here or upstream, so the default is all rights reserved. The original
maintainer said in writing that community builds are welcome and approved crediting the work as
*"originally developed by the Irefrixs Team"*, but a comment on an issue is not a licence grant with
terms. That is fine for private play and is the open question in front of anything wider. Tracked as
U5 in [docs/proposed_changes.md](docs/proposed_changes.md).

Build it with `./build.sh` and start it with `./play.sh`. The first creates the virtualenv,
installs both halves' dependencies and compiles the client; the second runs the game and will
call the first if anything is missing. Both are documented in
[the install guide](docs/install_guide.md).

| Tracker | Contents |
| --- | --- |
| [Proposed changes](docs/proposed_changes.md) | Defects found in the existing code, with the reasoning and what was decided |
| [Proposed features](docs/proposed_features.md) | New features and improvements for the fork |

## Documentation

| Guide                                                          | Description                       |
| -------------------------------------------------------------- | --------------------------------- |
| [Install Guide](docs/install_guide.md)                         | How to install and run the game   |
| [How to Play](https://itch.io/t/3763917/how-to-play-this-game) | Game rules and controls           |
| [Card Scripting Guide](docs/card_scripting_guide.md)           | How to write card ability scripts |
| [Engine Architecture](docs/engine_architecture.md)             | Engine internals for developers   |
| [Debug Guide](docs/debug_guide.md)                             | How to debug the game             |
| [Editor Guide](docs/editor_guide.md)                           | How to use the card editor        |

## Security Warning

This game runs Python card scripts, which is not safe.  
Do not install or run any third-party card scripts unless you trust them.

这个游戏会运行用 Python 编写的卡牌脚本，这不安全。  
除非你完全信任，否则不要安装或运行任何第三方的卡牌脚本。

## Snapshot

![](/docs/assets/image-1.jpg)
![](/docs/assets/image-2.jpg)
