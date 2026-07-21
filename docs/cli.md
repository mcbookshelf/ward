# Command-line tooling

The `mcward` CLI installs headless test servers and runs your datapacks
against them. It downloads and caches everything it needs: the server jar,
the Fabric loader, the Ward mod, and Java itself.

```sh
uv tool install mcward[cli]   # or: pip install mcward[cli]
```

## `mcward test`

```
mcward test [-p <pack>]... [-v <version>]... [selector]
```

Runs datapack tests. This is the default command: `mcward` alone, or
`ward`, runs tests directly.

- **Packs** are discovered automatically: any folder or zip with a
  `pack.mcmeta` in the current directory, its children, or `datapacks/*`.
  Use `-p` with a path or glob pattern to pick packs yourself. Quote the
  patterns (e.g. `-p "world/datapacks/bs.*"`) so the shell does not expand
  them first.
- **Versions** are picked from the packs' `pack_format` range: the newest
  release of each supported line, plus the latest snapshot when supported.
  Use `-v` to pin one or several versions. Versions are installed on first
  use.
- **selector** filters which tests run, using resource selector syntax:
  `*:*` (default), `ward:*`, `mypack:chest/*`, ... The `minecraft` namespace
  is reserved for vanilla built-ins (like `minecraft:always_pass`) and is
  never selected, so define tests in your own pack's namespace.

Each selected version runs the full test suite. Results stream into a live
display, and the command exits non-zero when a test fails or a datapack
fails to load.

### Reporters

`--reporter` (also on `beet test`) selects how results are presented:

- **`live`** (default) — the interactive display. Failures and load
  diagnostics point at the file as `path:line`, relative to the project
  root.
- **`github`** — plain logs plus [GitHub Actions annotations](https://docs.github.com/en/actions/reference/workflow-commands-for-github-actions).
  Each failed test becomes an `::error` pointing at the failing line of its
  `.mcfunction` file, and datapack load problems annotate the broken file.
  Failures are merged across versions into a single annotation.
  `mcward test` annotates the tested pack directories, while `beet test`
  maps built tests back to their source files. Plugin-generated tests have
  no file and are reported without one.

```yaml
- name: run datapack tests
  run: uvx "mcward[cli]" test -v 26.1.2 -v 26.2 --reporter github
```

## Managing versions

```
mcward install [version] [--force]   install a test server (--force reinstalls)
mcward clean [version]               remove an installed version
mcward list [--remote]               installed versions, or available ones with --remote
```

Run without a version argument, these prompt interactively.

## The daemon

```
mcward start [version]      start a test server in the background
mcward stop [version|-a]    stop it (or all of them with --all)
mcward status               show running daemons and whether they respond
```

`mcward test` starts servers on demand. A server started with `mcward start`
keeps running and is reused by every test run, which makes iteration much
faster.

## `beet test`

Installing the `mcward[beet]` extra extends the
[beet](https://github.com/mcbeet/beet) toolchain with a `test` command:

```
beet test [-v <version>]... [selector]
```

It builds the current beet project, then runs the built pack exactly like
`mcward test`. The `mcward.beet.plugin` plugin is required automatically so
`test/` folders are picked up.
