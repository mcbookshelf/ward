<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/banner-light.png">
    <img src="docs/assets/banner-dark.png" alt="Ward" width="400">
  </picture>
</h1>

<p align="center">
  <a href="https://github.com/mcbookshelf/ward/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/mcbookshelf/ward/ci.yml?style=for-the-badge&label=ci" alt="CI"></a>
  <a href="https://modrinth.com/mod/ward"><img src="https://img.shields.io/modrinth/v/ward?style=for-the-badge&logo=modrinth&label=modrinth" alt="Modrinth"></a>
  <a href="https://pypi.org/project/mcward/"><img src="https://img.shields.io/pypi/v/mcward?style=for-the-badge&logo=python&logoColor=white&label=pypi" alt="PyPI"></a>
</p>

Ward lets you write automated tests for your datapacks as plain `.mcfunction`
files in a `test/` folder.

![demo](./docs/assets/demo.gif)

<p align="center"><i>A test run with <code>mcward test</code>: results stream in live.</i></p>

Ward comes in two parts:

- 🧩 **Mod** ([Modrinth](https://modrinth.com/mod/ward)) — adds the test
  commands (`/assert`, `/await`, `/fail`, `/succeed`, `/dummy`) and a headless
  test server that streams results live.
- 🐍 **CLI** ([PyPI](https://pypi.org/project/mcward/)) — installs test
  servers (Java and the mod are fetched for you) and runs your packs on one or
  several Minecraft versions. Also ships a
  [beet](https://github.com/mcbeet/beet) plugin that adds `beet test`.

Ward is compatible with [packtest](https://github.com/misode/packtest):
existing packtest tests run unmodified.

## Quickstart

```sh
uv tool install mcward[cli]   # or: pip install mcward[cli]
mcward test                   # discovers datapacks, picks compatible versions, runs
```

`mcward list --remote` shows the Minecraft versions Ward currently supports.

Write tests in your datapack under `data/<namespace>/test/`:

```mcfunction
# @max_ticks 100
summon minecraft:armor_stand ~ ~ ~ {Tags: ["target"]}
assert entity @e[tag=target]
await not entity @e[tag=target]
```

Comment lines like `# @max_ticks` are [directives](docs/directives.md) that
configure the test. Inside the test, these commands are available:

| Command | Purpose |
| --- | --- |
| `assert [not] block/entity/data/score/chat/biome/predicate/items ...` | Assert immediately |
| `await [not] ...` | Retry every tick until true or timeout |
| `await delay <time>` | Pause the test |
| `fail [message]` / `succeed` | End the test explicitly |
| `dummy <player> spawn/leave/jump/use/attack/mine/...` | Control fake players |

## CLI

```sh
mcward test [-v <version>]... [-p <pack>]... [selector]   # run tests (default command)
mcward install [version]                                  # install a test server
mcward start / stop / status                              # manage the test daemon
mcward list [--remote]                                    # installed / available versions
beet test                                                 # build the beet project and test it
```

## Documentation

- [CLI](docs/cli.md) — the `mcward` CLI and `beet test`
- [Dummies](docs/dummies.md) — fake players and the `/dummy` command
- [Directives](docs/directives.md) — `# @max_ticks`, `# @environment`, ...
- [Test commands](docs/commands.md) — `/assert`, `/await`, `/fail`, `/succeed`
- [Test environments](docs/environments.md) — world setup/teardown around tests

## Acknowledgements

Ward is heavily inspired by [packtest](https://github.com/misode/packtest) by
[misode](https://github.com/misode), and implements its full command set.
