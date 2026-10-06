# @template ward:empty/3x3x3
# @dummy ~1 ~ ~1

# The first example of docs/dummies.md
setblock ~1 ~ ~2 minecraft:stone
item replace entity @s weapon.mainhand with minecraft:torch
dummy @s use block ~1 ~ ~2
assert block ~1 ~1 ~2 minecraft:torch
