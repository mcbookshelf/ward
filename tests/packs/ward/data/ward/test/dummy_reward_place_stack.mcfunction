# @dummy
# Same as dummy_reward_place with two sponges: the reward sees the stack before the consume
setblock ~ ~ ~2 minecraft:stone
item replace entity @s weapon.mainhand with minecraft:sponge 2
data remove storage ward:dummy held
dummy @s use block ~ ~ ~2
assert data storage ward:dummy held{id:"minecraft:sponge",count:2}
assert items entity @s weapon.mainhand minecraft:sponge[count=1]
