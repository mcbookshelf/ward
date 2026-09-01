# The chat window spans awaits: a message from a scheduled function arriving on an
# earlier tick than the assert must still be visible
schedule function ward:helper/announce 1t
await delay 3
assert chat "ward delayed announce"
