# @dummy
# No client confirms the teleport, and vanilla keeps a player invulnerable until its dimension change is confirmed
execute in ward:custom run tp @s ~ ~ ~
damage @s 4
assert entity @s[nbt={Health:16f}]
