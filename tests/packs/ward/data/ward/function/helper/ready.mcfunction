# Runs a plain command on every call and only returns once the flag is set
scoreboard players add #polls ward.fn 1
execute if score #done ward.fn matches 1 run return 1
