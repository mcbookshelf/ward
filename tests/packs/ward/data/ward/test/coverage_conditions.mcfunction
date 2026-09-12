# Condition coverage fixture: gated short-circuits its second term, blocked tests false
assert predicate ward:coverage/gated
assert not predicate ward:coverage/blocked
# Rolling the table reaches both entries, the zero-chance one never runs
loot spawn ~ ~1 ~ loot ward:coverage/drops
