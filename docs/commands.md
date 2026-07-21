# Test commands

The Ward mod registers five commands: `/assert`, `/await`, `/fail`, `/succeed`
and `/dummy`. They require permission level 2 (gamemasters). All of them
except `/dummy` only work while a test is running.

Commands in a test file run in order, on the test's command source. An
`/await` pauses the test until its condition holds. When the last command has
run and no awaits are pending, the test succeeds on its own; `/succeed` is
only needed to end a test early.

## `/assert` and `/await`

Both commands share the same condition syntax:

```
assert <condition>          fails the test immediately unless the condition holds
assert not <condition>      fails the test immediately if the condition holds
await <condition>           retries every tick until the condition holds
await not <condition>       retries every tick until the condition no longer holds
await delay <time>          pauses the test for a duration (e.g. 10, 2s, 1d)
```

An `/await` that never succeeds fails the test right before the timeout (see
the [`@max_ticks` directive](directives.md)), with the same message an
`/assert` would produce.

Conditions are counting checks: they hold when at least one match is found,
and failure messages report what was found instead. A check that cannot be
evaluated at all (unloaded position, unknown objective, missing entity) counts
as *errored*. An errored check fails both `assert` and `assert not`, and
keeps an `await` polling.

### Conditions

| Condition | Holds when |
| --- | --- |
| `biome <pos> <biome>` | the biome at `pos` matches a biome id or `#tag` |
| `block <pos> <block>` | the block at `pos` matches a block predicate (`stone`, `chest[facing=north]`, `#minecraft:logs{...}`) |
| `chat <pattern>` | a chat message matching the regex was received |
| `chat <pattern> <players>` | a matching message was received by one of `players` |
| `data block <pos> <path>` | the NBT path exists in the block entity |
| `data entity <target> <path>` | the NBT path exists on the entity |
| `data storage <id> <path>` | the NBT path exists in command storage |
| `entity <selector>` | the selector matches at least one entity |
| `entity <selector> inside` | it matches at least one entity inside the test structure bounds |
| `function <function>` | the function (id or `#tag`) returns a nonzero result, like `execute if function` |
| `items entity <selector> <slots> <item>` | matching items exist in the given entity slots |
| `items block <pos> <slots> <item>` | matching items exist in the given container slots |
| `predicate <predicate>` | the loot predicate (id or inline) passes at the source position |
| `result <range> run <command>` | the command's result value is within the range |
| `run <command>` | the command succeeds |
| `score <target> <objective> <op> <source> <objective>` | the score comparison holds (`=`, `<`, `<=`, `>`, `>=`) |
| `score <target> <objective> matches <range>` | the score is within the range (e.g. `3`, `5..10`, `..0`) |

## `/fail` and `/succeed`

```
fail                 fails the test with a generic message
fail <message>       fails the test with a text component message
succeed              ends the test successfully, skipping remaining commands
```

`<message>` is a text component: a plain string (`fail "chest not filled"`)
or a structured component (`fail {"text":"...","color":"red"}`). Components
resolve against the executing source.

## `/dummy`

Controls fake players. See [dummies](dummies.md) for how dummies behave and
the full subcommand reference:

```
dummy <name> spawn|leave|respawn|jump|swap
dummy <name> attack <entity>
dummy <name> mine <pos>
dummy <name> sneak|sprint <true|false>
dummy <name> mainhand <slot>
dummy <name> drop [all] | drop from <slot> [all]
dummy <name> use [block <pos> [<direction>]] [entity <entity> [<pos>]]
```
