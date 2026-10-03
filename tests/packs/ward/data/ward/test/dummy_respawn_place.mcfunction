# @dimension minecraft:the_nether
# @skyaccess
# A dummy respawns in the dimension and with the rotation it was spawned with
execute rotated 90 0 run dummy ward_place spawn
kill ward_place
dummy ward_place respawn
execute at ward_place run assert dimension minecraft:the_nether
assert entity @a[name=ward_place,y_rotation=90,distance=..2]
dummy ward_place leave
