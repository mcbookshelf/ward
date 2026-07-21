# @max_attempts 5
# @required_successes 3
# Always succeeds; required_successes forces three winning attempts before the
# test is reported passed. The extra reruns are invisible in the result, which
# must still settle as a single passed test (never double-counted).
scoreboard players add #flaky_successes ward.flaky 1
