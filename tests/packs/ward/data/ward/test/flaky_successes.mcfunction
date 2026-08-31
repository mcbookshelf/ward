# @max_attempts 5
# @required_successes 3
# Always succeeds, but required_successes forces three winning attempts before it passes
# The extra reruns stay invisible in the result, which settles as a single passed test
scoreboard players add #flaky_successes ward.flaky 1
