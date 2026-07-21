<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/banner-light.png">
    <img src="docs/assets/banner-dark.png" alt="Ward" width="400">
  </picture>
</h1>

<div align="center">
  <a href="https://github.com/mcbookshelf/ward/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/mcbookshelf/ward/ci.yml?style=for-the-badge&label=ci&colorA=363a4f&colorB=926bd1&logo=githubactions&logoColor=cad3f5" alt="CI"></a>
  &nbsp;
  <a href="https://modrinth.com/mod/ward"><img src="https://img.shields.io/modrinth/v/ward?style=for-the-badge&label=modrinth&colorA=363a4f&colorB=a6da95&logo=modrinth&logoColor=cad3f5" alt="Modrinth"></a>
  &nbsp;
  <a href="https://pypi.org/project/mcward/"><img src="https://img.shields.io/pypi/v/mcward?style=for-the-badge&label=pypi&colorA=363a4f&colorB=91d7e3&logo=python&logoColor=cad3f5" alt="PyPI"></a>
  &nbsp;
  <a href="https://discord.gg/MkXytNjmBt"><img src="https://img.shields.io/discord/1247513995376726116?style=for-the-badge&color=%237289DA&labelColor=363a4f&logo=discord&logoColor=cad3f5" alt="Discord"></a>
</div>

<br/>

Ward lets you write automated tests for your datapacks as plain `.mcfunction`
files in a `test/` folder.

![demo](./docs/assets/demo.gif)

<p align="center"><i>A test run with <code>mcward test</code>: results stream in live.</i></p>

Ward comes in two parts:

<table>
  <tr>
    <td align="center" nowrap>🧩 <b>Mod</b> (<a href="https://modrinth.com/mod/ward">Modrinth</a>)</td>
    <td>Adds the test commands (<code>/assert</code>, <code>/await</code>, <code>/fail</code>, <code>/succeed</code>, <code>/dummy</code>) and a headless test server that streams results live.</td>
  </tr>
  <tr>
    <td align="center" nowrap>🐍 <b>CLI</b> (<a href="https://pypi.org/project/mcward/">PyPI</a>)</td>
    <td>Installs test servers (Java and the mod are fetched for you) and runs your packs on one or several Minecraft versions. Also ships a <a href="https://github.com/mcbeet/beet">beet</a> plugin that adds <code>beet test</code>.</td>
  </tr>
</table>

## Quickstart

```sh
uv tool install mcward[cli]   # or: pip install mcward[cli]
ward                          # discovers datapacks, picks compatible versions, runs
```

`ward list --remote` shows the Minecraft versions Ward currently supports.

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
ward test [-v <version>]... [-p <pack>]... [selector]   # run tests (default command)
ward install [version]                                  # install a test server
ward start / stop / status                              # manage the test daemon
ward list [--remote]                                    # installed / available versions
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
