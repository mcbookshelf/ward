# The flat world spawns no mob and keeps its weather unless a test asks
assert result 0 run gamerule spawn_mobs
assert result 0 run gamerule advance_weather
