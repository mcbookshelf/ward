setblock ~ ~ ~ minecraft:chest
item replace block ~ ~ ~ container.0 with minecraft:diamond 3
assert items block ~ ~ ~ container.* minecraft:diamond
assert not items block ~ ~ ~ container.* minecraft:iron_ingot
assert not items entity @e[tag=ward_missing] container.* minecraft:diamond
setblock ~ ~ ~ minecraft:air
