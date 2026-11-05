# @dummy
# item_durability_changed fires before a broken tool is removed, so the reward still sees it
setblock ~ ~ ~2 minecraft:stone
item replace entity @s weapon.mainhand with minecraft:wooden_pickaxe[damage=58]
data remove storage ward:dummy held
dummy @s mine ~ ~ ~2
assert block ~ ~ ~2 minecraft:air
assert data storage ward:dummy held{id:"minecraft:wooden_pickaxe"}
assert not items entity @s weapon.mainhand *
