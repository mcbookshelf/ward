# Test environments

An environment prepares the world before a group of tests runs, and cleans up
after. Use one to run a setup function, freeze time, or force the weather.

Define it as a JSON file under `data/<namespace>/test_environment/`, then name
it in your tests:

```mcfunction
# @environment mypack:no_ticks
```

Tests without the directive use the built-in `minecraft:default` environment.
Tests that share an environment run together, in one batch.

These are the vanilla
[test environment definitions](https://minecraft.wiki/w/Test_environment_definition).
The types below cover the common needs.

## Run functions

Runs a function before the batch and another after it. Both are optional.
They run as the server.

```json
{
  "type": "minecraft:function",
  "setup": "mypack:test/setup",
  "teardown": "mypack:test/teardown"
}
```

## Set game rules

Sets game rules for the batch and restores them afterwards.

```json
{
  "type": "minecraft:game_rules",
  "rules": {
    "doDaylightCycle": false,
    "randomTickSpeed": 0
  }
}
```

## Set the difficulty

`peaceful`, `easy`, `normal` or `hard`.

```json
{
  "type": "minecraft:difficulty",
  "difficulty": "hard"
}
```

## Set the weather

`clear`, `rain` or `thunder`.

```json
{
  "type": "minecraft:weather",
  "weather": "thunder"
}
```

## Set the time

Freezes a world clock. `minecraft:overworld` and `minecraft:the_end` are the vanilla clocks.

```json
{
  "type": "minecraft:clock_time",
  "clock": "minecraft:overworld",
  "time": 6000
}
```

## Apply timelines

Applies environment attribute timelines to the level for the batch.

```json
{
  "type": "minecraft:timeline_attributes",
  "timelines": ["minecraft:overworld"]
}
```

## Combine environments

Lists other environments, by id or inline. Setup runs in order, teardown in reverse.

```json
{
  "type": "minecraft:all_of",
  "definitions": [
    "mypack:no_ticks",
    {
      "type": "minecraft:weather",
      "weather": "clear"
    }
  ]
}
```
