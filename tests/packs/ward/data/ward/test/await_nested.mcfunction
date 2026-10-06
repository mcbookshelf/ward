# @timeout 20
# An await inside an awaited function is one more await the test waits for
scoreboard objectives add ward.nested dummy
await function ward:helper/nested
assert score #calls ward.nested matches 3
scoreboard objectives remove ward.nested
