# Command-line tooling

The `mcward` CLI installs headless test servers and runs your datapacks
against them. Everything needed to run them — server jar, Fabric loader, the
Ward mod, and even Java itself — is downloaded and cached automatically.

```sh
uv tool install mcward[cli]   # or: pip install mcward[cli]
```

## `mcward test`

```
mcward test [-p <pack>]... [-v <version>]... [selector]
```

Runs datapack tests. This is the default command: `mcward` alone, or
`ward`, runs tests directly.

- **Packs** are discovered from the current directory, its children, and
  `datapacks/*` — any folder or zip with a `pack.mcmeta`. Use `-p` with
  paths or glob patterns to override (quote patterns, e.g.
  `-p "world/datapacks/bs.*"`, so the shell doesn't expand them first).
- **Versions** default to the Minecraft versions compatible with the
  discovered packs' `pack_format` range (newest release of each supported
  line, plus the latest snapshot when supported). Use `-v` to pin one or
  several explicitly. Versions are installed on first use.
- **selector** filters which tests run, using resource selector syntax:
  `*:*` (default), `ward:*`, `mypack:chest/*`, ... Tests in the `minecraft`
  namespace are reserved for vanilla built-ins (like `minecraft:always_pass`)
  and are never selected — define tests in your own pack's namespace.

Each selected version runs the full test suite; results stream into a live
display, and the command exits non-zero if any test fails or anything in a
datapack fails to load.

### Reporters

`--reporter` (also on `beet test`) selects how results are presented:

- **`live`** (default) — the interactive display. Failure positions and
  load diagnostics show the file as a `path:line` relative to the project
  root.
- **`github`** — plain logs plus [GitHub Actions annotations](https://docs.github.com/en/actions/reference/workflow-commands-for-github-actions):
  each failed test becomes an `::error` pointing at the failing line of its
  `.mcfunction` file, datapack load problems annotate the broken file, and
  test failures are merged across versions into a single annotation.
  Files are resolved automatically: `mcward test` annotates the tested pack
  directories themselves, `beet test` maps built tests back to the source
  files they were loaded from (plugin-generated tests have no file to
  annotate and are reported without one).

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

`mcward test` starts servers on demand, but a server started once with
`mcward start` is reused by every subsequent test run, which makes
iteration much faster. Daemons keep running until stopped.

## `beet test`

Installing the `mcward[beet]` extra extends the
[beet](https://github.com/mcbeet/beet) toolchain with a `test` command:

```
beet test [-v <version>]... [selector]
```

It builds the current beet project (the `mcward.beet.plugin` plugin is
required automatically so `test/` folders are picked up), then runs the
built pack exactly like `mcward test`.
