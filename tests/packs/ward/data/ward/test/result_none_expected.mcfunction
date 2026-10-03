# The failure says that nothing ran, it does not report a result of 0
assert result 1 run execute if entity @e[tag=ward_nobody] run scoreboard players get #t ward.missing
