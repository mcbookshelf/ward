# @dummy
# Dummy entity interactions must fire the player_interacted_with_entity trigger
# Vanilla fires it from the network handler, which dummies bypass
summon minecraft:cow ~2 ~ ~ {NoAI:1b,Tags:["ward_cow"]}
item replace entity @s weapon.mainhand with minecraft:wheat
dummy @s use entity @e[type=minecraft:cow,tag=ward_cow,limit=1]
assert entity @s[advancements={ward:feed_cow=true}]
kill @e[type=minecraft:cow,tag=ward_cow]
