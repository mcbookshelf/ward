# @cases [ \
  {value: 2, double: 4}, \
  {value: 5, double: 10} \
]
# Each case is a test of its own, with its arguments in the macro lines
scoreboard objectives add ward.cases dummy
$scoreboard players set #$(value) ward.cases $(value)
$scoreboard players operation #$(value) ward.cases += #$(value) ward.cases
$assert score #$(value) ward.cases matches $(double)
