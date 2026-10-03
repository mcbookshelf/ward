# An error means "not yet": the objective does not exist when the await starts
schedule function ward:helper/late 3t
await score #late ward.late matches 1
scoreboard objectives remove ward.late
