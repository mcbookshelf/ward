setblock ~ ~ ~ minecraft:stone
setblock ~ ~2 ~ minecraft:stone
assert blocks ~ ~ ~ ~ ~ ~ ~ ~2 ~ all
setblock ~ ~2 ~ minecraft:dirt
assert not blocks ~ ~ ~ ~ ~ ~ ~ ~2 ~ all
setblock ~ ~ ~ minecraft:air
assert blocks ~ ~ ~ ~ ~ ~ ~ ~2 ~ masked
setblock ~ ~2 ~ minecraft:air
