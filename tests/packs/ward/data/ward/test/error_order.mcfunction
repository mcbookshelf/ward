# The first failing command must be the reported failure, not the last one of the tick
setblock ~ ~5 ~ minecraft:stone
await delay 2
execute if block ~ ~5 ~ minecraft:stone run fail "first failure"
execute if block ~ ~5 ~ minecraft:stone run fail "second failure"
