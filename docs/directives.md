# Test directives

Directives set how a test runs. Write them as comments at the top of the test file:

```mcfunction
# @max_ticks 200
# @dimension minecraft:the_nether
# @environment ward:no_ticks
# @dummy 8 1 8

say running as a dummy in the nether
```

A typo in a directive, or a command that does not parse, fails the whole file
when the pack loads.

## Reference

| Directive | Value | Default | Effect |
| --- | --- | --- | --- |
| `@max_ticks` | ticks | `100` | How long the test may run before it fails. Alias: `@timeout` |
| `@setup_ticks` | ticks | `0` | Ticks the environment runs before the test starts |
| `@optional` | `true`/`false` | `false` | A failure is reported but does not fail the run |
| `@template` | structure id | `minecraft:empty` | Structure placed as the test area. Alias: `@structure` |
| `@environment` | environment id | `minecraft:default` | [Test environment](environments.md) the test runs in |
| `@dimension` | dimension id | `minecraft:overworld` | Dimension the test runs in |
| `@rotation` | `-90`, `0`, `90`, `180` | `0` | Rotation of the test structure |
| `@max_attempts` | count | `1` | How many times a flaky test may run before it fails |
| `@required_successes` | count | `1` | Passing runs needed, together with `@max_attempts` |
| `@padding` | `0` to `128` | `0` | Empty space around the structure, to keep tests apart |
| `@skyaccess` | `true`/`false` | `false` | Keeps the sky above the structure open. Alias: `@sky_access` |
| `@dummy` | position | none | Spawns a [dummy](dummies.md) and runs the test as it |

Boolean directives can be bare: `# @optional` means `true`.
`# @dummy` without a position spawns at `~ ~ ~`.
