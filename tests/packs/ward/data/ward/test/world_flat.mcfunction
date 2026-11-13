# Without a world the run is in the flat one, even right after a run in tests/world
forceload add 8 8
await loaded 8 63 8
assert block 8 -61 8 minecraft:grass_block
assert not block 8 63 8 minecraft:diamond_block
assert not run scoreboard players get #map saved
