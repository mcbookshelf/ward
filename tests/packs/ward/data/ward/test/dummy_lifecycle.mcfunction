dummy ward_lifecycle spawn
assert entity @e[type=minecraft:player,name=ward_lifecycle]
kill @e[type=minecraft:player,name=ward_lifecycle]
dummy ward_lifecycle respawn
assert entity @e[type=minecraft:player,name=ward_lifecycle]
dummy ward_lifecycle leave
# Without a type the selector searches the level, where a dummy removed from the player list only would remain
assert not entity @e[name=ward_lifecycle]
