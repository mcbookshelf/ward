setblock ~ ~ ~ minecraft:chest
assert slots block ~ ~ ~ container.*
assert not slots entity @e[tag=ward_missing] container.*
setblock ~ ~ ~ minecraft:air
