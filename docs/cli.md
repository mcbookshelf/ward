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

Ward finds your packs on its own. It looks for a `pack.mcmeta` in the current
folder, its children, and `datapacks/*`.

It picks Minecraft versions from the `pack_format` range of your packs. Each
version is installed on first use, then runs the full suite. When the range
spans several major versions, Ward asks which ones to use.

### Options

```
mcward test [-p <pack>]... [-v <version>]... [selector]
```

- `-p <pack>`: choose packs yourself, by path or glob (`-p "path/to/datapacks/*"`).
- `-v <version>`: pin one or more versions (`-v 26.1.2 -v 26.2`).
- `selector`: run a subset of tests. `mypack:*` runs a namespace,
  `mypack:chest/*` a folder. The default `*:*` runs everything. Tests in the
  `minecraft` namespace never run, so keep tests in your own namespace.

### Coverage

`--coverage` shows which parts of your packs the tests run.
`--coverage-report html` writes the detail to a file. See [coverage](coverage.md).

### Result files

`--junit-xml results.xml` writes the results as JUnit XML, one `<testsuite>`
per version. Most CI services can display this file.

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
