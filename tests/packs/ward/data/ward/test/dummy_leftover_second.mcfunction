# @environment ward:leftover/second
# @dummy
# Its batch runs after the one of dummy_leftover_first: same name, none of its score or team
scoreboard objectives add ward.leftover dummy
assert entity @s[name=dummy-1]
assert not score @s ward.leftover matches 5
assert not entity @s[team=ward.leftover]
