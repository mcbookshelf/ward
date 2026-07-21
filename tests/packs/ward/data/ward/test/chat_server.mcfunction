# Broadcasts are observable without any dummy online: the server copy of the
# message is recorded even when there is no player recipient
say ward server broadcast
assert chat "ward server broadcast"
assert not chat "never said anywhere"
