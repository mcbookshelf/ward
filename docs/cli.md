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

It picks Minecraft versions from the `pack_format` range of your packs. Each
version is installed on first use, then runs the full suite. When the range
spans several major versions, Ward asks which ones to use.

### Options

```
mcward test [-p <pack>]... [-v <version>]... [--world <path>] [selector]
```

- `-p <pack>`: choose packs yourself, by path or glob (`-p "path/to/datapacks/*"`).
- `-v <version>`: pin one or more versions (`-v 26.1.2 -v 26.2`).
- `--world <path>`: run in a copy of a world save. See [saved world](#saved-world).
- `selector`: run a subset of tests. `mypack:*` runs a namespace,
  `mypack:chest/*` a folder. The default `*:*` runs everything. Tests in the
  `minecraft` namespace never run, so keep tests in your own namespace.

### Coverage

`--coverage` shows which parts of your packs the tests run.
`--coverage-report html` writes the detail to a file.
`--coverage-min 80` fails the run when coverage is below 80%. See [coverage](coverage.md).

### Result files

`--junit-xml results.xml` writes the results as JUnit XML, one `<testsuite>`
per version. Most CI services can display this file.

### Saved world

Tests run in a flat, empty world. `--world <path>` runs them in a copy of a
world save instead, such as the map your pack is made for:

```sh
mcward test --world world
```

You can also set it in a `ward.toml` file, in the folder you run the tests
from. The path is relative to that file, and `--world` wins over it.

```toml
world = "world"
```

Ward never writes to your world. Each server keeps its own copy and makes it
again when a file of the world changes. 

The `datapacks` folder of the world is left out: only the packs under test
load. See [the test world](directives.md#saved-world) for what a test finds in
the copy.

### Watch mode

`--watch` (or `-w`) runs the tests, then again each time a pack file changes.
A change in the [saved world](#saved-world) counts too.
The server keeps running between runs, so each one takes about a second.

While it waits, these keys work:

- `a` or `Enter`: run every selected test again.
- `p`: type a selector and press `Enter` to run only those tests, such as
  `mypack:chest/*`. `Escape` cancels, and `a` goes back to every test.
- `q`: quit. The servers keep running for the next time.

`--watch` does not work with `--reporter github`.

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

```
mcward install [version] [--force]   install a test server (--force reinstalls)
mcward clean [version]               remove an installed one
mcward list [--remote]               installed versions, or all available ones
```

Without a version, these commands ask you to pick one.

## Keep servers running

`mcward test` starts servers when it needs them and leaves them running, so
the next run starts faster. You can also manage them yourself:

```
mcward start [version]      start a server in the background
mcward stop [version|-a]    stop one, or all of them with --all
mcward status               show running servers
```

## beet

The `mcward[beet]` extra adds a `test` command to
[beet](https://github.com/mcbeet/beet):

```sh
beet test [-v <version>]... [selector]
```

It builds your project, then tests the built pack. Every `mcward test` option works.
With `--watch`, it builds and tests again when a project file changes. Hidden
files and beet's cache do not count as changes.
