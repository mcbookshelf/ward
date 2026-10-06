# @dummy
# Player chat reaches the players form, and a broadcast still counts once
scoreboard objectives add ward.chat_players dummy
say ward said
assert chat "ward said" @s
execute store result score #said ward.chat_players run assert chat "ward said"
assert score #said ward.chat_players matches 1
msg @s ward whispered
assert chat "ward whispered" @s
assert chat "ward whispered"
