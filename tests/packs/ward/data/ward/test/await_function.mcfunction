# @timeout 100
# A retried await function reads the function's return value, not the result of the commands it runs
scoreboard objectives add ward.fn dummy
scoreboard players set #done ward.fn 0
schedule function ward:helper/finish 5t
await function ward:helper/ready
assert score #done ward.fn matches 1

# A tag keeps going past a function that runs commands without returning
scoreboard players set #done ward.fn 0
schedule function ward:helper/finish 5t
await function #ward:quiet_then_ready
assert score #done ward.fn matches 1
scoreboard objectives remove ward.fn
