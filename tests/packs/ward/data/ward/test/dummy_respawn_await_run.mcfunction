# @dummy
# @skyaccess
gamerule immediate_respawn true
kill @s
gamerule immediate_respawn false
# A condition that runs a command follows the dummy to its new instance too
await run execute if entity @s[nbt={Health:20f}]
