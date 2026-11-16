# @environment ward:leftover/first
# @dummy
# Leaves a score and a team under the name that the dummy of dummy_leftover_second gets
scoreboard objectives add ward.leftover dummy
scoreboard players set @s ward.leftover 5
team add ward.leftover
team join ward.leftover @s
assert score @s ward.leftover matches 5
assert entity @s[team=ward.leftover]
