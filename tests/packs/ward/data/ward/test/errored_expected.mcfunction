# Unresolvable arguments must fail the assert with the command error, never skip it silently
# The engine swallows exceptions thrown by command bodies, so the assert has to catch them
assert score #t ward.missing matches 1..
