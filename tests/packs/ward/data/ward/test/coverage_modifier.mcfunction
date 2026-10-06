# @dummy
# @skyaccess
# An item modifier counts as run when it is applied
item replace entity @s weapon.mainhand with minecraft:stone
item modify entity @s weapon.mainhand ward:coverage/double
assert items entity @s weapon.mainhand minecraft:stone[count=2]
