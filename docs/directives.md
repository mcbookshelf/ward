# Test directives

Directives configure how a test runs. They are comments of the form
`# @directive value` in the test's `.mcfunction` file, conventionally at the
top (any comment line in the file is scanned):

```mcfunction
# @max_ticks 200
# @dimension minecraft:the_nether
# @environment ward:no_ticks
# @dummy 8 1 8

say running as a dummy in the nether
```

Test files are parsed strictly when the pack loads. An unknown directive, a
bad value, or a command that does not parse makes the whole file fail to
load. The test is then reported as a load error instead of running without
it.

## Reference

| Directive | Value | Default | Effect |
| --- | --- | --- | --- |
| `@max_ticks` / `@timeout` | positive int (ticks) | `100` | Maximum test duration; the test fails when it is reached |
| `@setup_ticks` | non-negative int (ticks) | `0` | Ticks the environment runs before the test starts |
| `@optional` | `true`/`false` (bare = `true`) | `false` | A failure is reported but does not fail the test run |
| `@template` / `@structure` | structure id | `minecraft:empty` | Structure template placed as the test area |
| `@environment` | test environment id | `minecraft:default` | [Test environment](environments.md) the test runs in |
| `@dimension` | dimension id | `minecraft:overworld` | Dimension the test runs in |
| `@rotation` | degrees: `-90` / `0` / `90` / `180` | `0` | Rotation applied to the test structure |
| `@max_attempts` | positive int | `1` | Number of times the test may run before it is reported as failed |
| `@required_successes` | positive int | `1` | Successful runs needed to pass (for flaky tests, with `@max_attempts`) |
| `@padding` | int `0`–`128` | `0` | Empty space kept around the structure to isolate neighbouring tests |
| `@skyaccess` / `@sky_access` | `true`/`false` (bare = `true`) | `false` | Keeps the space above the structure clear of the test barrier ceiling |
| `@dummy` | position (bare = `~ ~ ~`) | none | Spawns a [dummy](dummies.md) and makes it the test's executor |

Directives map onto the vanilla
[test instance](https://minecraft.wiki/w/Test_instance) fields, and keep the
vanilla spelling as an alias where the names differ.
