forceload add 8 8
await loaded 8 64 8
assert items block 8 64 8 container.0 minecraft:emerald
item replace block 8 64 8 container.0 with minecraft:stone
