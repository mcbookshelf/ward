<div>
  <img src="./docs/assets/logo.png" alt="Ward logo" height="44" align="left">
  <h1>Ward</h1>
</div>

Ward lets you write automated tests for your datapacks as plain `.mcfunction`
files in a `test/` folder.

![demo](./docs/assets/demo.gif)

Ward is two pieces that work together:

- 🧩 **The Mod** (on [Modrinth](https://modrinth.com/mod/ward)) — a Fabric mod
  adding the test commands (`/assert`, `/await`, `/fail`, `/succeed`,
  `/dummy`) and a headless test server that streams results live.
- 🐍 **The Tooling** (on [PyPI](https://pypi.org/project/mcward/)) — the `mcward`
  CLI that installs test servers (fetching Java and the mod for you), runs your packs against one or several
  Minecraft versions with a live display, plus a [beet](https://github.com/mcbeet/beet)
  plugin adding `beet test`.

## Quickstart

```sh
uv tool install mcward[cli]   # or: pip install mcward[cli]
mcward test                   # discovers datapacks, picks compatible versions, runs
```

Write tests in your datapack under `data/<namespace>/test/`:

```mcfunction
# @timeout 100
summon minecraft:armor_stand ~ ~ ~ {Tags: ["target"]}
assert entity @e[tag=target]
await not entity @e[tag=target]
```

Test files support directives (`# @timeout`, `# @optional`, `# @dummy`,
`# @template`, `# @environment`, `# @skyaccess`) and the full command set:

| Command | Purpose |
| --- | --- |
| `assert [not] block/entity/data/score/chat/biome/predicate/items ...` | Assert immediately |
| `await [not] ...` | Retry every tick until true or timeout |
| `await delay <time>` | Pause the test |
| `fail [message]` / `succeed` | End the test explicitly |
| `dummy <player> spawn/leave/jump/use/attack/mine/...` | Control fake players |

## Documentation

- [CLI](docs/cli.md) — the `mcward` CLI and `beet test`
- [Dummies](docs/dummies.md) — fake players and the `/dummy` command
- [Directives](docs/directives.md) — `# @timeout`, `# @environment`, ...
- [Test commands](docs/commands.md) — `/assert`, `/await`, `/fail`, `/succeed`
- [Test environments](docs/environments.md) — world setup/teardown around tests

## Commands

```sh
mcward test [-v <version>]... [-p <pack>]... [selector]   # run tests (default command)
mcward install [version]                                  # install a test server
mcward start / stop / status                              # manage the test daemon
mcward list [--remote]                                    # installed / available versions
beet test                                                 # build the beet project and test it
```

## Acknowledgements

Ward is heavily inspired by [packtest](https://github.com/misode/packtest) by
[misode](https://github.com/misode).

Ward implements packtest's full command set, so **existing packtest tests run
unmodified under Ward**. On top of that, Ward adds a few extra commands, a CLI
with multi-version runs and a live test display, and a `beet test` plugin.

## Development

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for the guidelines and workflow.

## License

[MPL-2.0](LICENSE)
