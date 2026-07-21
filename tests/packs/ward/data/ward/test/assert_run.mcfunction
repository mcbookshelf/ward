assert run function ward:helper/pass
assert not run function ward:helper/fail

assert result 42 run function ward:helper/pass
assert not result 1.. run function ward:helper/fail

scoreboard objectives add ward.run dummy
scoreboard players set #run ward.run 7
assert run scoreboard players get #run ward.run
assert result 7 run scoreboard players get #run ward.run
assert not result 8.. run scoreboard players get #run ward.run
scoreboard objectives remove ward.run

assert function ward:helper/pass
assert not function ward:helper/fail
assert not function ward:helper/quiet
