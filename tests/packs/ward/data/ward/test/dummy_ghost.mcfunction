# @max_attempts 2
# First attempt: the dummy dies on the last tick of the test, which removes it before its respawn task runs
# Second attempt: runs in a later batch and fails if that task brought the dummy back
scoreboard players add #ghost_attempt ward.flaky 1
execute if score #ghost_attempt ward.flaky matches 2 run assert not entity @e[name=ward_ghost]
execute if score #ghost_attempt ward.flaky matches 2 run succeed
dummy ward_ghost spawn
gamerule immediate_respawn true
kill @a[name=ward_ghost]
gamerule immediate_respawn false
fail "ends on the death tick"
