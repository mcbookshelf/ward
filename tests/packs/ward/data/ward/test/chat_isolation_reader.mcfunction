# @environment ward:chat
# A test does not see the chat of the other tests of its batch
await delay 3
assert not chat "ward isolation"
