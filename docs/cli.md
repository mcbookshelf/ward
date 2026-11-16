# Command-line tooling

The `mcward` command runs your datapack tests. It downloads everything it
needs: Java, the Minecraft server, and the Ward mod.

```sh
uv tool install mcward[cli]   # or: pip install mcward[cli]
```

## Run tests

```sh
mcward test
```

`mcward` alone, or `ward`, does the same thing.

Ward finds your packs on its own. It looks at the current folder, its children,
and `datapacks/*`.

It picks Minecraft versions from the `pack_format` range of your packs. Ward
installs each version on first use, then runs the full suite on it. When the
range spans several major versions, Ward asks which ones to use. Without a
terminal, it uses all of them.

### Options

```text
mcward test [-p <pack>]... [-v <version>]... [<selector>]
```

- `-p <pack>`: choose packs yourself, by path or glob (`-p "path/to/datapacks/*"`).
- `-v <version>`: pin one or more versions (`-v 26.1.2 -v 26.2`).
- `<selector>`: run a subset of tests. `mypack:*` runs a namespace,
  `mypack:chest/*` a folder. The default `*:*` runs everything. Tests in the
  `minecraft` namespace never run, so keep tests in your own namespace.
- `--world <path>`: run in a copy of a [saved world](world.md#saved-world).
- `--coverage`: show which parts of your packs the tests run. See
  [coverage](coverage.md) for this option and the ones that go with it.
- `--junit-xml <file>`: write the results as JUnit XML, one `<testsuite>` per
  version. Most CI services can display this file.
- `--reporter github`: print for GitHub Actions. See [run in CI](#run-in-ci).
- `--verbose`: list every test and every coverage row, not a summary.
- `--watch`: run again when a file changes. See [watch mode](#watch-mode).

### Watch mode

`--watch` (or `-w`) runs the tests, then again each time a pack file changes.
A change in the [saved world](world.md#saved-world) counts too.
The report files a run writes, such as `coverage.html`, do not count.
The server keeps running between runs, so each one takes about a second.

While it waits, these keys work:

- `a` or `Enter`: run every selected test again.
- `p`: type a selector and press `Enter` to run only those tests, such as
  `mypack:chest/*`. `Escape` cancels, and `a` goes back to every test.
- `q`: quit. The servers keep running for the next time.

`--watch` does not work with `--reporter github`.

## ward.toml

Settings that stay with your project go in a `ward.toml` file, in the folder
you run the tests from.

| Key | Value | Effect |
| --- | --- | --- |
| `world` | path, relative to the file | The [saved world](world.md#saved-world) tests run in |
| `origin` | `[x, z]` | Where [test areas](world.md#position) are placed |
| `coverage.minimum` | percentage | The [coverage a run has to reach](coverage.md#require-a-minimum) |
| `coverage.ignore` | list of rules | What [coverage leaves out](coverage.md#ignore-code) |

```toml
world = "world"

[coverage]
minimum = 80
```

## Time commands

```sh
mcward bench "function mypack:a" "function mypack:b"
```

See [benchmarks](bench.md).

## Run in CI

Use the `github` reporter. It prints plain logs, and each failed test becomes
an annotation on the failing line of your `.mcfunction` file. Broken datapack
files get annotated too.

```yaml
- name: run datapack tests
  run: uvx "mcward[cli]" test -v 26.1.2 -v 26.2 --reporter github
```

## Manage servers

```text
mcward install [<version>] [--force]   install a test server (--force reinstalls)
mcward clean [<version>]               remove an installed one
mcward list [--remote]                 installed versions, or all available ones
```

Without a version, these commands ask you to pick one.

When Modrinth has a newer Ward mod for an installed version, the next start
updates it first, so a local run uses the same mod as a fresh install on CI.

## Keep servers running

`mcward test` starts servers when it needs them and leaves them running, so
the next run starts faster. A server that runs nothing for an hour stops by itself.
A server serves one `mcward` at a time: a second run on the same version waits
for the first one to end.
You can also manage them yourself:

```text
mcward start [<version>]         start a server in the background
mcward stop [<version>|--all]    stop one, or all of them
mcward status                    show running servers
```

## beet

The `mcward[beet]` extra adds a `test` command to
[beet](https://github.com/mcbeet/beet):

```sh
beet test [-v <version>]... [<selector>]
```

It builds your project, then tests the built pack. Every `mcward test` option works.
With `--watch`, it builds and tests again when a project file or the saved world changes.
It skips the files that `beet watch` skips.

### mecha

The `mcward[mecha]` extra adds a [mecha](https://github.com/mcbeet/mecha)
plugin that parses test files with Ward's commands. Require it in your beet
config:

```json
{
  "require": ["mcward.mecha"]
}
```

It uses the commands of the newest Ward. To match an older mod, name its
version:

```json
{
  "meta": { "ward": { "version": "1.2" } }
}
```
