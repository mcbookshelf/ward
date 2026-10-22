# @max_attempts 3
# Fails until its third attempt: only the logs of that attempt are reported
scoreboard players add #log_retry ward.flaky 1
log {"score":{"name":"#log_retry","objective":"ward.flaky"}}
assert score #log_retry ward.flaky matches 3..
