# @dimension minecraft:the_nether
assert dimension minecraft:the_nether
assert not dimension minecraft:overworld
assert predicate ward:in_nether
assert not predicate ward:in_overworld
# The test world is flat in every vanilla dimension, so the biome and the floor never change
assert biome ~ ~ ~ minecraft:basalt_deltas
assert block ~ 3 ~ minecraft:basalt
