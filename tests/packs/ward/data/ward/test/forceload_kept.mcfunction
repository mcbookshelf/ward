# @environment ward:scored
# @timeout 600
# The mirror of ward:forceload_during, running in the other batch; see there
forceload add 15000640 15000640
await block 15000640 -64 15000640 minecraft:bedrock
await delay 40
scoreboard players set #kept ward.forceload 1
execute if score #during ward.forceload matches 1 run await run execute if loaded 15000000 0 15000000
execute if score #during ward.forceload matches 1 run await run execute if loaded 15000320 0 15000320
