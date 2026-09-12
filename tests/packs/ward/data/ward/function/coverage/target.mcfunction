# Coverage fixture: one line per branch shape the collector distinguishes
scoreboard objectives add ward.coverage dummy
scoreboard players set #cov ward.coverage 1
execute if score #cov ward.coverage matches 1 run say covered
execute if score #cov ward.coverage matches 2 run say guarded
execute as @e[type=armor_stand,tag=ward_coverage_missing] run say guarded
execute if function ward:coverage/check run say gated
function ward:coverage/macro {message: "macro"}
return run scoreboard objectives remove ward.coverage
say unreachable
