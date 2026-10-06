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
Names ignore case, and a directive written twice keeps its last value.

## Test world

Each run starts in a new world, and nothing is saved. No experiment is
enabled: villager trades and loot are the ones of a default world.

The three vanilla dimensions are flat: grass in the overworld (plains), basalt
in the Nether (basalt deltas) and end stone in the End. The test area sits a
few blocks above that floor.

## Empty templates

The default template, `minecraft:empty`, is a single block of air. Minecraft
closes the test area with barriers: a floor, four walls, and a ceiling unless
`@skyaccess` is set.

Test areas sit in rows of 8, a few blocks apart, and the tests of a batch all
run at the same time. So a test that builds outside its own area can reach
the area of another test.

Ward comes with larger empty templates for tests that need room:
`ward:empty/3x3x3`, `ward:empty/5x5x5` and `ward:empty/9x9x9`.

```mcfunction
# @template ward:empty/5x5x5

fill ~1 ~ ~1 ~3 ~ ~3 minecraft:stone
assert block ~2 ~ ~2 minecraft:stone
```

`~ ~ ~` is the north-west bottom corner of the template, not its center.
The center of a `3x3x3` template is `~1 ~ ~1`.
