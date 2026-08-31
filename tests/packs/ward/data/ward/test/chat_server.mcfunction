# Broadcasts are observable without any dummy online
# The server copy of the message is recorded even with no player recipient
say ward server broadcast
assert chat "ward server broadcast"
assert not chat "never said anywhere"
