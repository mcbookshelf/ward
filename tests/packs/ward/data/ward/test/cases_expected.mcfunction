# @cases [{n: 1}, {n: 2}]
# A case that fails does so alone, under its own arguments
scoreboard objectives add ward.cases dummy
$scoreboard players set #expected_$(n) ward.cases $(n)
$assert score #expected_$(n) ward.cases matches 1
