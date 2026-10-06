# @dummy
# @skyaccess
# Sneaking and sprinting are keys that a predicate can read
dummy @s sneak true
assert predicate {"type":"minecraft:entity_properties","entity":"this","predicate":{"minecraft:type_specific/player":{"input":{"sneak":true,"sprint":false}}}}
dummy @s sprint true
assert predicate {"type":"minecraft:entity_properties","entity":"this","predicate":{"minecraft:type_specific/player":{"input":{"sneak":true,"sprint":true}}}}
dummy @s sneak false
assert predicate {"type":"minecraft:entity_properties","entity":"this","predicate":{"minecraft:type_specific/player":{"input":{"sneak":false,"sprint":true}}}}
