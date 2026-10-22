scoreboard objectives add ward.log dummy
scoreboard players set #value ward.log 7
log "plain text"
log {"score":{"name":"#value","objective":"ward.log"}}
# A component that fails to resolve logs the error instead
summon minecraft:marker ~ ~ ~ {Tags:["ward.log"]}
summon minecraft:marker ~ ~ ~ {Tags:["ward.log"]}
log {"score":{"name":"@e[tag=ward.log]","objective":"ward.log"}}
kill @e[tag=ward.log]
await delay 2
log "after await"
