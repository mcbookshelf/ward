# Dummies

Dummies are fake players. Use them to test anything that needs a player:
using items, opening containers, taking damage, triggering advancements.
They are inspired by [Carpet](https://github.com/gnembon/fabric-carpet)'s fake players.

A dummy behaves like a real player on the server:

- It spawns in survival mode.
- It has gravity, takes damage, uses items and containers.
- It matches `@a` and `@p`, and receives chat.
- It is never saved with the world.
- When it dies it waits on the death screen. Use `/dummy <name> respawn`,
  or set the `doImmediateRespawn` game rule so dummies respawn on their own.

## Create a dummy

The easiest way is the [`@dummy` directive](directives.md). It spawns a dummy
when the test starts and runs the test as that dummy, so it is `@s`:

```mcfunction
# @dummy 8 1 8

dummy @s mainhand 3
dummy @s use block 8 0 9
assert block 8 0 9 minecraft:torch
```

To pick a name, or to spawn several dummies, use the command:

```mcfunction
dummy alice spawn
dummy alice use block 8 0 9
```

The name must be free: no connected player or dummy with the same name.

## Commands

Each action fails with an error when the dummy cannot do it.

| Command | Action | Fails when |
| --- | --- | --- |
| `dummy <name> spawn` | Spawn a new dummy | name already taken |
| `dummy <name> leave` | Disconnect the dummy | |
| `dummy <name> respawn` | Respawn a dead dummy | |
| `dummy <name> jump` | Jump | not on the ground |
| `dummy <name> swap` | Swap main hand and off hand | |
| `dummy <name> attack <entity>` | Attack an entity in melee | |
| `dummy <name> mine <pos>` | Break the block instantly | block cannot be broken |
| `dummy <name> sneak <true\|false>` | Start or stop sneaking | already in that state |
| `dummy <name> sprint <true\|false>` | Start or stop sprinting | already in that state |
| `dummy <name> mainhand <slot>` | Select hotbar slot `0` to `8` | already selected |
| `dummy <name> drop` | Drop one item from the main hand | |
| `dummy <name> drop all` | Drop the whole main hand stack | |
| `dummy <name> drop from <slot> [all]` | Drop from an inventory slot | |
| `dummy <name> use` | Use the held item (main hand, then off hand) | nothing usable |
| `dummy <name> use block <pos> [<direction>]` | Use the held item on a block face (default `up`) | nothing happened |
| `dummy <name> use entity <entity> [<pos>]` | Interact with an entity, at an exact point if given | nothing happened |
