# Test environments

A test environment prepares the world before tests run and restores it
afterwards: game rules, weather, time, or arbitrary setup/teardown functions.
Tests declare their environment with the
[`# @environment` directive](directives.md). Tests sharing an environment are
batched together, so the setup runs once per batch, not once per test.

Environments are vanilla registry entries, following the format documented on
the [Minecraft wiki](https://minecraft.wiki/w/Test_environment_definition).
They live in your datapack at:

```
data/<namespace>/test_environment/<name>.json
```

and referenced as `<namespace>:<name>`. The built-in `minecraft:default`
environment (no setup at all) is used when a test declares nothing.

Ward changes one thing: vanilla only loads the `test_environment` registry at
world creation, while Ward reloads it on every `/reload`. Environments
live-update in daemon mode like the tests themselves, and a file that fails
to parse shows up as a diagnostic in the test report.

## Environment types

### `minecraft:function`

Runs functions around the batch. Both fields are optional. Functions run as
the server with gamemaster permissions.

```json
{
  "type": "minecraft:function",
  "setup": "ward:helper/env_setup",
  "teardown": "ward:helper/env_teardown"
}
```

### `minecraft:game_rules`

Sets game rules for the batch and restores the previous values afterwards.

```json
{
  "type": "minecraft:game_rules",
  "rules": {
    "doDaylightCycle": false,
    "randomTickSpeed": 0
  }
}
```

### `minecraft:difficulty`

Sets the world difficulty (`peaceful`, `easy`, `normal` or `hard`) for the
batch and restores the previous value afterwards.

```json
{
  "type": "minecraft:difficulty",
  "difficulty": "hard"
}
```

### `minecraft:weather`

Forces `clear`, `rain` or `thunder`, and restores the previous weather.

```json
{
  "type": "minecraft:weather",
  "weather": "thunder"
}
```

### `minecraft:clock_time`

Sets a world clock to a fixed time (`minecraft:overworld` and
`minecraft:the_end` are the vanilla clocks).

```json
{
  "type": "minecraft:clock_time",
  "clock": "minecraft:overworld",
  "time": 6000
}
```

### `minecraft:timeline_attributes`

Applies environment-attribute timelines to the level for the duration of the
batch.

```json
{
  "type": "minecraft:timeline_attributes",
  "timelines": ["minecraft:overworld"]
}
```

### `minecraft:all_of`

Composes several environments. Entries can reference other environment files
by id, or be inlined. Teardown runs in reverse order.

```json
{
  "type": "minecraft:all_of",
  "definitions": [
    "ward:no_ticks",
    {
      "type": "minecraft:weather",
      "weather": "clear"
    }
  ]
}
```
