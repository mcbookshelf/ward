# @timeout 20
# A failure on the timeout tick keeps its message and line
await delay 20
fail "at the deadline"
