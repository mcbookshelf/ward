# @dummy
# A dummy can be hurt from its first tick, like a player whose client has finished loading
damage @s 4
assert entity @s[nbt={Health:16f}]
assert not run dummy @s respawn
kill @s
dummy @s respawn
# The sender and the connection both follow the dummy to its new instance
assert entity @s[nbt={Health:20f}]
tp @s ~0.2 ~ ~0.2
execute positioned ~0.2 ~ ~0.2 run assert entity @s[distance=..0.05]
damage @s 4
assert entity @s[nbt={Health:16f}]
