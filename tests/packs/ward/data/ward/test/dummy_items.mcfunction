# @timeout 200
dummy ward_items spawn
item replace entity ward_items weapon.mainhand with minecraft:diamond 2
item replace entity ward_items weapon.offhand with minecraft:stick
assert items entity ward_items weapon.mainhand minecraft:diamond
assert not items entity ward_items weapon.mainhand minecraft:stick

dummy ward_items swap
assert items entity ward_items weapon.mainhand minecraft:stick
assert items entity ward_items weapon.offhand minecraft:diamond

item replace entity ward_items hotbar.3 with minecraft:emerald
dummy ward_items mainhand 3
assert items entity ward_items weapon.mainhand minecraft:emerald

dummy ward_items drop all
assert not items entity ward_items weapon.mainhand minecraft:emerald
assert entity @e[type=minecraft:item] inside

dummy ward_items drop from weapon.offhand all
assert not items entity ward_items weapon.offhand minecraft:diamond
# An item dropped from a slot is thrown by the dummy, like the one dropped from the hand
assert entity @e[type=minecraft:item,nbt={Item:{id:"minecraft:diamond"}}] inside
assert data entity @e[type=minecraft:item,nbt={Item:{id:"minecraft:diamond"}},limit=1] Thrower

dummy ward_items leave
