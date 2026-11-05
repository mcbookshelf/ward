# @dummy
# A reward triggered by a dummy action runs before the action ends, like for a real player
# placed_block fires before the item is consumed, so the reward still sees the last sponge
setblock ~ ~ ~2 minecraft:stone
item replace entity @s weapon.mainhand with minecraft:sponge
data remove storage ward:dummy held
dummy @s use block ~ ~ ~2
assert block ~ ~1 ~2 minecraft:sponge
assert data storage ward:dummy held{id:"minecraft:sponge"}
assert not items entity @s weapon.mainhand *
