# Dummies

Dummies are fake players for testing player-specific mechanics: interactions,
inventories, advancements, chat, damage — anything that needs a real
`ServerPlayer` on the server. They are inspired by
[Carpet](https://github.com/gnembon/fabric-carpet)'s fake players.

A dummy is a full server-side player attached to a no-op network connection:

- it spawns in **survival mode** on the bottom center of the block containing
  the position of the command that created it — placement is block-aligned
  and deterministic however the position was derived,
- it ticks like a real player (gravity, damage, item use, container logic),
  counts for `@a`/`@p` selectors, and receives chat like anyone else,
- it is never saved with the world,
- when it dies it stays on the death screen like a real player — respawn it
  with `/dummy <name> respawn`, or enable the `doImmediateRespawn` game rule
  to make dummies respawn automatically,

## Creating dummies

Two ways:

- **`/dummy <name> spawn`** — spawns a dummy with that exact name at the
  command source's position. The name must not collide with a connected
  player (or another dummy).
- **[`# @dummy` directive](directives.md)** — spawns a dummy with a generated
  name (`dummy-<number>`) when the test starts and makes it the executor of
  every command in the test, so it is simply `@s`:

```mcfunction
# @dummy 8 1 8

dummy @s mainhand 3
dummy @s use block 8 0 9
assert block 8 0 9 minecraft:torch
```

## Subcommands

All actions hard-fail with a descriptive error when they cannot be performed —
a dummy that is already sneaking cannot `sneak true`, a mid-air dummy cannot
`jump`. This is intentional: a test action that does nothing is a bug in the
test.

| Command | Action | Fails when |
| --- | --- | --- |
| `dummy <name> spawn` | Spawn a new dummy | name already taken |
| `dummy <name> leave` | Disconnect the dummy | |
| `dummy <name> respawn` | Respawn a dead dummy | |
| `dummy <name> jump` | Jump | not on the ground |
| `dummy <name> swap` | Swap main hand and off hand | |
| `dummy <name> attack <entity>` | Melee-attack an entity | |
| `dummy <name> mine <pos>` | Break the block (instantly, respecting protection) | block cannot be broken |
| `dummy <name> sneak <true\|false>` | Start/stop sneaking | already in that state |
| `dummy <name> sprint <true\|false>` | Start/stop sprinting | already in that state |
| `dummy <name> mainhand <slot>` | Select hotbar slot `0`-`8` | already selected |
| `dummy <name> drop` | Drop one item from the main hand | |
| `dummy <name> drop all` | Drop the whole main-hand stack | |
| `dummy <name> drop from <slot> [all]` | Drop from a specific inventory slot | |
| `dummy <name> use` | Use the held item (main hand, then off hand) | nothing usable |
| `dummy <name> use block <pos> [<direction>]` | Use the held item on a block face (default `up`) | interaction not consumed |
| `dummy <name> use entity <entity> [<pos>]` | Interact with an entity, optionally at a precise point | interaction not consumed |

`<name>` accepts a player name or a selector resolving to a dummy (`@s` inside
a `@dummy` test); targeting a real player is an error. `drop` and
`drop from` return the number of items dropped, the `use` variants try the
main hand first and fall back to the off hand.
