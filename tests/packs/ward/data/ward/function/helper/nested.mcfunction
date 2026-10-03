# Awaits on every call and only returns on the third
await delay 2
scoreboard players add #calls ward.nested 1
execute if score #calls ward.nested matches 3.. run return 1
