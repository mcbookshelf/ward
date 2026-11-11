# The save has this block. The test replaces it, and the next run has to find it again
forceload add 8 8
await loaded 8 63 8
assert block 8 63 8 minecraft:diamond_block
setblock 8 63 8 minecraft:dirt
