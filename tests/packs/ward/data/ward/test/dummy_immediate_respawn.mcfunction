# @dummy
# @skyaccess
gamerule immediate_respawn true
kill @s
gamerule immediate_respawn false
# The respawn runs after the tick, like a client answering the death screen
# The await starts on the dead dummy and follows it to its new instance
await entity @s[nbt={Health:20f}]
