# The count renders in a negated failure message
summon minecraft:marker ~ ~1 ~ {Tags:["ward_negated"]}
assert not entity @e[type=minecraft:marker,tag=ward_negated]
