<div>
  <img src="./docs/assets/logo.png" alt="Ward logo" height="42" align="left">
  <h1>Ward</h1>
</div>

A testing framework for Minecraft datapacks using mcfunction.

Ward lets you write automated tests for your datapacks as plain `.mcfunction`
files in a `test/` folder.

![demo](./docs/assets/demo.gif)

Ward is two pieces that work together:

- **The mod** ([Modrinth](https://modrinth.com/mod/ward)) — a Fabric mod
  adding the test commands (`/assert`, `/await`, `/fail`, `/succeed`,
  `/dummy`) and a headless test server that streams results live.
- **The tooling** ([PyPI](https://pypi.org/project/mcward/)) — the `mcward`
  CLI that installs test servers, runs your packs against one or several
  Minecraft versions with a live display, plus a [beet](https://github.com/mcbeet/beet)
  plugin adding `beet test`.

## Quick start

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

## Development

Requires [uv](https://docs.astral.sh/uv/), [just](https://just.systems), a JDK,
and Gradle (wrapper included).

```sh
uv sync --all-extras          # set up the workspace
just check                    # lint + types + unit tests
just verify                   # build the mod and run the full integration suite
```

Layout: the Fabric mod lives in `src/`, the Python packages in `packages/`
(`mcward-core`, `mcward-cli`, `mcward-beet`), tooling in `tools/`, and the
integration fixture datapacks in `tests/packs/`. Releases are automated from
the versions committed to the tree — see
[CONTRIBUTING.md](.github/CONTRIBUTING.md) for the guidelines and workflow.

## License

[MPL-2.0](LICENSE)
