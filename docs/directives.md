# Test directives

Directives set how a test runs. Write them as comments at the top of the test
file, before the first command:

```mcfunction
# @max_ticks 200
# @dimension minecraft:the_nether
# @environment ward:no_ticks
# @dummy ~ ~ ~

say running as a dummy in the nether
```

A typo in a directive, or a command that does not parse, fails the whole file
when the pack loads. After the first command, a comment is never read as a
directive, whatever it starts with.

## Reference

| Directive | Value | Default | Effect |
| --- | --- | --- | --- |
| `@max_ticks` | ticks | `100` | How long the test may run before it fails. Alias: `@timeout` |
| `@setup_ticks` | ticks | `0` | Ticks the environment runs before the test starts |
| `@optional` | `true`/`false` | `false` | A failure is reported but does not fail the run |
| `@template` | structure id | `minecraft:empty` | Template placed as the [test area](world.md#test-areas). Alias: `@structure` |
| `@environment` | environment id | `minecraft:default` | [Test environment](environments.md) the test runs in |
| `@dimension` | dimension id | `minecraft:overworld` | Dimension the test runs in |
| `@rotation` | `-90`, `0`, `90`, `180` | `0` | Rotation of the test area |
| `@max_attempts` | count | `1` | How many times a flaky test may run before it fails |
| `@required_successes` | count | `1` | Passing runs needed, together with `@max_attempts` |
| `@padding` | `0` to `128` | `0` | Empty space around the test area |
| `@skyaccess` | `true`/`false` | `false` | Keeps the sky above the test area open. Alias: `@sky_access` |
| `@dummy` | position | none | Spawns a [dummy](dummies.md) and runs the test as it |
| `@cases` | list of compounds | none | Runs the test once for each [case](#cases) |

Boolean directives can be bare: `# @optional` means `true`.
`# @dummy` without a position spawns at `~ ~ ~`.
Names ignore case, and a directive written twice keeps its last value.

## Cases

`@cases` runs the test once for each compound of arguments. Use the arguments
in macro lines, as in a function:

```mcfunction
# @cases [{value: 2, double: 4}, {value: 5, double: 10}]

$scoreboard players set #n mypack.math $(value)
function mypack:double
$assert score #n mypack.math matches $(double)
```

Each case is a test of its own, named after its arguments:

```text
mypack:double {double:4,value:2}
mypack:double {double:10,value:5}
```

The cases share the other directives of the file. `mcward test mypack:double`
runs all of them, and `mcward test mypack:double/2` only the second. A long
list can go over several lines, with a `\` at the end of each:

```mcfunction
# @cases [ \
  {value: 2, double: 4}, \
  {value: 5, double: 10} \
]
```
