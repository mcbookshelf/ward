# @max_attempts 2
# Never succeeds: after exhausting every attempt it is reported failed, carrying
# the message of its final attempt rather than a generic "out of attempts" one.
fail "flaky ran out of attempts"
