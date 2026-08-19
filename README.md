The open-source of Marvel LCG digital version on [ITCH](https://irefrixs.itch.io/marvel-lcg)

## About this fork

This is [hexate/marvel-lcg](https://github.com/hexate/marvel-lcg), a fork of
[irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg). You are reading `main`, the trunk,
which is the upstream game plus a stabilization pass: crash fixes, a working save, a replay-independent
test suite, and a run script. See [CHANGELOG.md](CHANGELOG.md) for what changed and why.

`master` is left as an exact mirror of upstream and is not where the work lives. The `pr/*` branches
are a record of fixes offered back upstream, each a readable one-commit diff against it; upstream
declared the project sunset and took none of them, so no new ones are cut. Branch layout is in
[docs/proposed_changes.md](docs/proposed_changes.md).

Start the game with `./play.sh`, which is documented in [the install guide](docs/install_guide.md).

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
