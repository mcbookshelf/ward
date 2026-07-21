# @dummy
# @timeout 200

execute positioned ~.5 ~ ~.5 run assert entity @s[distance=..0.1]

dummy @s jump
dummy @s sneak true
dummy @s sneak false
dummy @s sprint true
dummy @s sprint false

setblock ~-2 ~ ~ minecraft:stone
dummy @s mine ~-2 ~ ~
assert block ~-2 ~ ~ minecraft:air

setblock ~ ~ ~2 minecraft:stone
setblock ~ ~1 ~2 minecraft:lever[face=floor]
dummy @s use block ~ ~1 ~2
assert block ~ ~1 ~2 minecraft:lever[powered=true]
setblock ~ ~1 ~2 minecraft:air
setblock ~ ~ ~2 minecraft:air

item replace entity @s weapon.mainhand with minecraft:snowball 16
dummy @s use
assert entity @e[type=minecraft:snowball] inside

summon minecraft:armor_stand ~2 ~ ~ {Tags:["ward_target"]}
dummy @s attack @e[type=minecraft:armor_stand,tag=ward_target,limit=1]
await delay 5
dummy @s attack @e[type=minecraft:armor_stand,tag=ward_target,limit=1]
await not entity @e[tag=ward_target]
