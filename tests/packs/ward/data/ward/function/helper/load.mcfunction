# Simulates a datapack keeping a machine chunk alive, far outside the test area
# The ward:forceload_* tests check that it survives
forceload add 15000000 15000000

# The forceload test flags persist with the world; each run starts clean
scoreboard objectives remove ward.forceload
scoreboard objectives add ward.forceload dummy

# The flaky fixtures count their attempts across reruns here; start clean too
scoreboard objectives remove ward.flaky
scoreboard objectives add ward.flaky dummy
