# @timeout 600
# Forceloads must survive batch ends. The chunks are polled rather than checked
# instantly: a freshly forced chunk climbs to entity-ticking asynchronously,
# while a wrongly unforced one unloads for good and times the await out.
forceload add 15000320 15000320
await block 15000320 -64 15000320 minecraft:bedrock
await delay 40
scoreboard players set #during ward.forceload 1
execute if score #kept ward.forceload matches 1 run await run execute if loaded 15000000 0 15000000
execute if score #kept ward.forceload matches 1 run await run execute if loaded 15000640 0 15000640
