# A delay spanning the whole timeout still fits
# The executor runs through the timeout tick, which the framework only fails strictly after
await delay 100
