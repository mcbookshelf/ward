# Condition coverage fixture: gated short-circuits its second term, blocked tests false
assert predicate ward:coverage/gated
assert not predicate ward:coverage/blocked
# Rolling the table evaluates the conditional number provider behind its rolls
loot spawn ~ ~1 ~ loot ward:coverage/drops
# Referencing the slot source from an assertion evaluates it
setblock ~ ~ ~ minecraft:chest
assert slots block ~ ~ ~ ward:coverage/chest_slots
setblock ~ ~ ~ minecraft:air
