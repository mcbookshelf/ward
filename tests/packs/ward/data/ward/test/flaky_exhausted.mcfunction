# @max_attempts 2
# Never succeeds, so it is reported failed once every attempt is exhausted
# The failure carries the message of the final attempt, not a generic "out of attempts" one
fail "flaky ran out of attempts"
