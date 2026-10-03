# A function tag stops at its first return, like execute if function
scoreboard objectives add ward.tag dummy
scoreboard players set #second ward.tag 0
assert function #ward:first_returns
assert score #second ward.tag matches 0
