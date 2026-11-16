<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/banner-light.png">
    <img src="docs/assets/banner-dark.png" alt="Ward" width="400">
  </picture>
</h1>

<div align="center">
  <a href="https://github.com/mcbookshelf/ward/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/mcbookshelf/ward/ci.yml?style=for-the-badge&label=ci&colorA=363a4f&colorB=926bd1&logo=githubactions&logoColor=cad3f5" alt="CI"></a>
  &nbsp;
  <a href="https://modrinth.com/mod/ward"><img src="https://img.shields.io/modrinth/v/ward?style=for-the-badge&label=modrinth&colorA=363a4f&colorB=2eb86a&logo=modrinth&logoColor=cad3f5" alt="Modrinth"></a>
  &nbsp;
  <a href="https://pypi.org/project/mcward/"><img src="https://img.shields.io/pypi/v/mcward?style=for-the-badge&label=pypi&colorA=363a4f&colorB=3775A9&logo=python&logoColor=cad3f5" alt="PyPI"></a>
  &nbsp;
  <a href="https://discord.gg/MkXytNjmBt"><img src="https://img.shields.io/discord/1247513995376726116?style=for-the-badge&color=%237289DA&labelColor=363a4f&logo=discord&logoColor=cad3f5" alt="Discord"></a>
</div>

<br/>

<p align="center">Ward runs automated tests for Minecraft datapacks. Tests are plain <code>.mcfunction</code> files in a <code>test/</code> folder.</p>

<p align="center"><img src="./docs/assets/demo.gif" alt="demo"></p>
<p align="center"><i>A test run with <code>mcward</code>. Results stream in live.</i></p>

Ward comes in two parts:

<table>
  <tr>
    <td align="center" nowrap>🧩 <b>Mod</b> - <a href="https://modrinth.com/mod/ward">Modrinth</a></td>
    <td>Adds the test commands (<code>/assert</code>, <code>/await</code>, <code>/fail</code>, <code>/succeed</code>, <code>/log</code>, <code>/dummy</code>) and a headless test server that streams results live.</td>
  </tr>
  <tr>
    <td align="center" nowrap>🐍 <b>CLI</b> - <a href="https://pypi.org/project/mcward/">PyPI</a></td>
    <td>Installs test servers and runs your packs on one or more Minecraft versions. It downloads Java and the mod for you. The <code>beet</code> extra adds <code>beet test</code> to <a href="https://github.com/mcbeet/beet">beet</a>.</td>
  </tr>
</table>

## Quickstart

Install the CLI (requires Python 3.14 or newer):

```sh
uv tool install mcward[cli]   # or: pip install mcward[cli]
```

Write a test in your datapack under `data/<namespace>/test/`:

```mcfunction
# @max_ticks 20
summon minecraft:zombie ~ ~ ~ {Tags: ["target"]}
kill @e[tag=target]
await not entity @e[tag=target]
```

Ward finds your packs, picks matching versions, and runs the tests:

```sh
mcward test
```

Comments starting with `@` are [directives](docs/directives.md). They configure the test.
`/await` and `/assert` are [test commands](docs/commands.md).

## Documentation

- [Test commands](docs/commands.md): `/assert`, `/await`, `/fail`, `/succeed`, `/log`
- [Test directives](docs/directives.md): settings of a test, such as `@max_ticks` and `@environment`
- [Test environments](docs/environments.md): set up the world before tests, and clean up after
- [Test world](docs/world.md): the world tests run in, test areas, and saved worlds
- [Dummies](docs/dummies.md): fake players and the `/dummy` command
- [Test coverage](docs/coverage.md): which parts of your packs the tests run
- [Benchmarks](docs/bench.md): time commands and compare them
- [Command-line tooling](docs/cli.md): the `mcward` command and `beet test`

## Acknowledgements

Ward is heavily inspired by [packtest](https://github.com/misode/packtest) by
[misode](https://github.com/misode), and implements its full command set.
Dummies are inspired by the fake players of
[Carpet](https://github.com/gnembon/fabric-carpet).
