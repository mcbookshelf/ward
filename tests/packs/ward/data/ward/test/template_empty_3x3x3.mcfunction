# @template ward:empty/3x3x3
# @dummy ~1 ~ ~1

assert block ~2 ~2 ~2 minecraft:air
assert block ~2 ~3 ~2 minecraft:barrier
# The default template is one block high and its ceiling suffocates a dummy
await delay 12
assert entity @s[nbt={Health:20f}]
