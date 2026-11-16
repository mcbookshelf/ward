# @environment ward:lively
# A test that needs mobs or weather turns them back on in its environment
assert result 1 run gamerule spawn_mobs
assert result 1 run gamerule advance_weather
