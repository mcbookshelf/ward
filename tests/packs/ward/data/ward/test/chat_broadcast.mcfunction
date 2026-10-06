# A broadcast counts once, however many players receive it
scoreboard objectives add ward.chat dummy
dummy ward_listener spawn
execute store result score #count ward.chat run assert chat "ward_listener joined the game"
assert score #count ward.chat matches 1
dummy ward_listener leave
