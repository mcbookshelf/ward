# Test directives

Directives configure how a test runs. They are comments of the form
`# @directive value` inside the test's `.mcfunction` file — conventionally at
the top, though any comment line in the file is scanned:

```mcfunction
# @timeout 200
# @environment ward:nether
# @dummy 8 1 8

say running as a dummy in the nether
```

Test files are parsed strictly when the pack loads: an unknown directive, an
invalid value, or an unparseable command makes the whole file fail to load,
and the test is reported as a load error instead of silently running without
it.

## Reference

| Directive | Value | Default | Effect |
| --- | --- | --- | --- |
| `@timeout` | positive int (ticks) | `100` | Maximum test duration; the test fails when it is reached |
| `@optional` | `true`/`false` (bare = `true`) | `false` | A failure is reported but does not fail the test run |
| `@template` | structure id | `minecraft:empty` | Structure template placed as the test area |
| `@environment` | test environment id | `minecraft:default` | [Test environment](environments.md) the test runs in |
| `@skyaccess` | `true`/`false` (bare = `true`) | `false` | Keeps the space above the structure clear of the test barrier ceiling |
| `@dummy` | position (bare = `~ ~ ~`) | none | Spawns a [dummy](dummies.md) and makes it the test's executor |

Notes:

- **`@timeout`** counts in game ticks (20 per second). A pending `/await`
  fails with its descriptive message on the last tick before the timeout.
- **`@template`** — with the default empty template the test area is a plain
  platform; point it to a structure to run the test inside a prebuilt scene.
  Coordinates in test commands are relative to the structure origin.
- **`@dummy`** — the spawned dummy becomes `@s` for every command in the test,
  so `assert data entity @s ...`, `dummy @s jump`, etc. work directly. The
  position is relative to the structure origin.
