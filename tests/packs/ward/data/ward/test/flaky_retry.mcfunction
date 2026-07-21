# @max_attempts 3
# Fails until its third attempt: proves failed runs are retried and the test is
# reported passed only when it finally succeeds, not on the first failure. The
# counter persists across reruns, so it reaches 3 on the third attempt.
scoreboard players add #flaky_retry ward.flaky 1
assert score #flaky_retry ward.flaky matches 3..
