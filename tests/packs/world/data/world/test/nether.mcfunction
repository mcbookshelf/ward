# @dimension minecraft:the_nether
# The Nether is the one of the save, with its terrain
forceload add 8 8
await loaded 8 64 8
assert block 8 64 8 minecraft:gold_block
