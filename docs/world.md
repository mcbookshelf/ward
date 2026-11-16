# Test world

Each run starts in a new world, and nothing is saved. No experiment is
enabled: villager trades and loot are the ones of a default world.

The three vanilla dimensions are flat: grass in the overworld (plains), basalt
in the Nether (basalt deltas), and end stone in the End. No mob spawns and the
weather does not change: turn them back on in a
[test environment](environments.md) with the `spawn_mobs` and
`advance_weather` game rules.

## Test areas

Each test gets its own area, a few blocks above the floor. The default
template, `minecraft:empty`, is a single block of air. Minecraft closes the
area with barriers: a floor, four walls, and a ceiling unless `@skyaccess` is
set.

Test areas sit in rows of 8, a few blocks apart, and the tests of a batch all
run at the same time. So a test that builds outside its own area can reach
the area of another test.

Ward comes with larger empty templates for tests that need room:
`ward:empty/3x3x3`, `ward:empty/5x5x5`, and `ward:empty/9x9x9`.

```mcfunction
# @template ward:empty/5x5x5

fill ~1 ~ ~1 ~3 ~ ~3 minecraft:stone
assert block ~2 ~ ~2 minecraft:stone
```

`~ ~ ~` is the north-west bottom corner of the template, not its center.
The center of a `3x3x3` template is `~1 ~ ~1`.

### Position

Test areas are placed from a random spot, up to millions of blocks from the
center of the world. When a run fails, Ward prints where it placed them. To
place them there again, or always at the same spot, set `origin` in
[`ward.toml`](cli.md#wardtoml) to the x and z of that spot:

```toml
origin = [120, -4500]
```

## Saved world

Tests can run in a copy of a saved world instead, such as the map your pack is
made for:

```sh
mcward test --world world
```

You can also set `world` in [`ward.toml`](cli.md#wardtoml). `--world` wins
over it.

Ward never writes to your world. Each server keeps its own copy, and makes it
again when a file of the world changes. What a test changes is gone on the
next run. The tests of one run share the copy, so what one test changes
outside its area, another one can see.

- Blocks, entities, scores, command storage, game rules, time, and the spawn
  point are the ones of the save.
- The dimensions are the ones of the save too: its Nether, its End, and the
  ones your packs add. `@dimension` works the same.
- Only the packs under test load. The `datapacks` folder of the save is left
  out, and so are its list of enabled packs and its experiments.
- Test areas sit far from the save, a few blocks above the bottom of the
  world. In a void world they hang in the void. In a world with terrain, that
  terrain is generated around them, which is slower, and the areas are
  underground. Set [`origin`](#position) to choose the spot.
- A world border saved with the world does not move, so the test areas are
  outside of it and living entities take border damage there.

A test starts once its own area is loaded. The chunks of the save are not
loaded for it: load the ones you use and wait for them. Chunks read from disk
take a few ticks longer than flat ones.

```mcfunction
forceload add 100 200
await loaded 100 64 200
assert block 100 64 200 minecraft:barrel
```
