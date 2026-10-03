# @environment ward:frozen
# @max_attempts 2
# Its own environment keeps the freeze out of the other tests' batch
# First attempt: freezes the game and fails after an await, so tests must keep ticking while the game is frozen
# Second attempt: runs in a later batch and only passes if the game was unfrozen when the first batch ended
scoreboard players add #freeze_attempt ward.flaky 1
execute if score #freeze_attempt ward.flaky matches 1 run tick freeze
execute store result score #freeze_before ward.flaky run time query gametime
await delay 5
execute store result score #freeze_after ward.flaky run time query gametime
execute if score #freeze_attempt ward.flaky matches 1 run fail "frozen on the first attempt"
assert score #freeze_after ward.flaky > #freeze_before ward.flaky
