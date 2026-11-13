# Entities load after their chunk
forceload add 8 8
await entity @e[type=minecraft:armor_stand,tag=saved]
kill @e[type=minecraft:armor_stand,tag=saved]
