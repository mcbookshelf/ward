# Test commands

The Ward mod adds five commands: `/assert`, `/await`, `/fail`, `/succeed` and
`/dummy`. They need permission level 2. All of them except `/dummy` only work
inside a running test.

A test runs its commands in order. `/await` pauses the test until its
condition holds. The test passes when the last command has run and nothing is
still waiting. You only need `/succeed` to end a test early.

## `/assert` and `/await`

Both commands take the same conditions:

```
assert <condition>          fails now unless the condition holds
assert not <condition>      fails now if the condition holds
await <condition>           waits until the condition holds
await not <condition>       waits until the condition no longer holds
await delay <time>          waits for a duration (10, 2s, 1d)
```

An `await` that never resolves fails the test when it times out.
Set the timeout with the [`@max_ticks` directive](directives.md).

### Conditions

| Condition | Holds when |
| --- | --- |
| `biome <pos> <biome>` | the biome at `pos` matches an id or `#tag` |
| `block <pos> <block>` | the block at `pos` matches (`stone`, `chest[facing=north]`, `#minecraft:logs{...}`) |
| `blocks <start> <end> <destination> all\|masked` | the region matches the blocks at `destination`. `masked` skips air in the source |
| `chat <pattern>` | a chat message matched the regex since the test started |
| `chat <pattern> <players>` | one of `players` received a matching message |
| `data block <pos> <path>` | the NBT path exists in the block entity |
| `data entity <target> <path>` | the NBT path exists on the entity |
| `data storage <id> <path>` | the NBT path exists in command storage |
| `dimension <dimension>` | the test runs in that dimension |
| `entity <selector>` | the selector matches at least one entity |
| `entity <selector> inside` | it matches an entity inside the test area |
| `function <function>` | the function (id or `#tag`) returns a nonzero result |
| `items entity <selector> <slots> <item>` | matching items exist in those entity slots |
| `items block <pos> <slots> <item>` | matching items exist in those container slots |
| `loaded <pos>` | the chunk at `pos` is fully loaded |
| `predicate <predicate>` | the predicate (id or inline) passes |
| `result <range> run <command>` | the command's result is in the range |
| `run <command>` | the command succeeds |
| `score <target> <objective> <op> <source> <objective>` | the comparison holds (`=`, `<`, `<=`, `>`, `>=`) |
| `score <target> <objective> matches <range>` | the score is in the range (`3`, `5..10`, `..0`) |
| `slots entity <selector> <slots>` | those entity slots exist |
| `slots block <pos> <slots>` | those container slots exist |
| `stopwatch <id> <range>` | the stopwatch's elapsed seconds are in the range |

## `/fail` and `/succeed`

```
fail                 fails the test
fail <message>       fails the test with a message (text component)
succeed              passes the test and skips the remaining commands
```

## `/dummy`

Controls fake players. See [dummies](dummies.md).
