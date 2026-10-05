# Cursed Contraptions

**Five animated, placeable trap devices for Minecraft Bedrock multiplayer.**

Release **v0.1.5** · Declared minimum engine version **1.21.60**. Uses stable `@minecraft/server` 1.17.0; no Beta APIs toggle is required.

## Features

- Five craftable devices with distinct capture ranges, damage, cycle speeds, and durability;
  hand-painted RGBA art for every entity atlas, block face, and inventory icon.
- Automatic proximity capture, a short escape window, and synchronized closing animations.
- Captured players have movement disabled until rescued or released; mobs are held in place
  with Slowness VII and Blindness and visibly struggle, without the tick-by-tick teleport
  corrections that used to make them stutter.
- Nearby teammates can open an occupied device. Captured players cannot rescue themselves; the interaction prompt and feedback make available actions clearer.
- Armor pieces reinforce an unoccupied device; interacting with an occupied device rescues first.
- Redstone activation, persisted device state, breakable durability, and a single item drop on break.
- Active-device limits, local entity queries, and bounded timers to keep work predictable.

## Install

1. Download and import `Cursed-Contraptions.mcaddon` into Bedrock Edition.
2. Enable both **Cursed Contraptions** packs in world settings.
3. Cheats are optional; use the recipes below for survival, or `/give @s cc:item_iron_maiden` (replace the item ID for another device).
4. For a Realm, the owner should enable both packs on a copy of the world first; the shipped add-on uses stable APIs and does not require Beta APIs.

For a dedicated server, extract the `.mcaddon` and install each contained `.mcpack` in the matching `behavior_packs/` and `resource_packs/` directories. Add both packs to the world pack lists and restart.

## Play

### Place and capture

Place a device item on a solid surface. It becomes an animated device entity; the temporary anchor block is removed. Nearby eligible players and mobs are detected automatically. During the capture delay, leaving the configured radius cancels the attempt. Creative and spectator players are immune. On touch controls, aim at the device and use the localized **Use / Rescue** action; on keyboard/controller, use the normal entity-interact control. An empty-hand interaction explains what the device does and how to reinforce it.

### Rescue and reinforce

- **Rescue:** Interact with an occupied device. A teammate opens it and releases the captive.
- **Reinforce:** While the device is unoccupied, interact while holding a vanilla armor piece or elytra. The item is consumed; each piece raises durability and damage output while shortening the torture interval. Slots are limited per device.
- **Break:** Attack the device. It has its own durability counter; breaking it releases the captive and drops exactly one device item.
- **Redstone:** Power an adjacent block to request an activation after the device's configured delay. Proximity capture remains enabled without redstone.

Torture cycles heal the captive first, then apply damage capped to leave at least one health point — so a normal cycle cannot kill. A rare extreme critical hit (per-device chance, roughly 3–10%) deals a flat 20 HP (10 hearts) spike that may finish a low-health captive outright, keeping the device unpredictable. Other hazards and player actions are still dangerous; death releases the device.

## Devices and default balance

Damage values are Minecraft health points (two points per heart). Armor bonuses apply per installed armor piece.

| Device | Capture radius | Cycle | Normal damage | Critical chance | Durability | Armor slots |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Iron Maiden | 1.5 | 3 s | 10–18 | 5% | 200 | 4 |
| Cursed Stocks | 1.2 | 4 s | 4–8 | 3% | 150 | 2 |
| Gravebinder Cage | 1.8 | 2.5 s | 6–14 | 8% | 180 | 3 |
| The Regret Rack | 1.4 | 5 s | 8–16 | 4% | 300 | 4 |
| The Black Reliquary | 2.0 | 2 s | 12–20 | 10% | 250 | 4 |

Critical damage and healing are device-specific; exact values are in `behavior_pack/scripts/config.js`.

## Crafting

Recipes use a crafting table. Empty spaces are shown as spaces.

**Iron Maiden**
```
IBI
ISI
IRI
I = Iron Ingot   B = Iron Bars   S = Iron Sword   R = Redstone
```

**Cursed Stocks**
```
P P
PCP
P P
P = Oak Planks   C = Chain
```

**Gravebinder Cage**
```
BBB
BSB
BIB
B = Iron Bars   S = Soul Sand   I = Iron Ingot
```

**The Regret Rack**
```
C C
PPP
IRI
C = Chain   P = Oak Planks   I = Iron Ingot   R = Redstone
```

**The Black Reliquary**
```
ONO
NEN
ORO
O = Obsidian   N = Netherite Ingot   E = End Crystal   R = Redstone Block
```

## Admin tools

Admin commands run through `/scriptevent`, so they only need the stable API — but `/scriptevent` requires **cheats enabled** in the world. Commands are restricted to players tagged `cc:admin`; an operator can grant the tag with `/tag <player> add cc:admin`.

- `/scriptevent cc:give` — Add all five devices to your inventory.
- `/scriptevent cc:devices` — List registered devices and their state/durability.
- `/scriptevent cc:debug on` / `/scriptevent cc:debug off` — Toggle server and chat debug logging.

## Build and tests

Requirements: Python 3, Node.js 22+, and Info-ZIP (`zip`). The packs themselves have no runtime dependencies; `npm install` fetches dev-only type-checking tooling (`typescript`, `@minecraft/server` typings) that never ships inside the packs.

```bash
npm install        # Dev-only tooling for the type-check gate
npm test           # Unit, manager, admin-command, and device-lifecycle tests
npm run typecheck  # Type-check behavior-pack scripts against the stable 1.17.0 API surface
./build.sh         # Validate pack references and package the .mcaddon
```

The automated suite checks JavaScript syntax, type conformance against the stable `@minecraft/server` 1.17.0 typings, state transitions, persistence helpers, gameplay lifecycle behavior, admin command handling, pack references, manifest compatibility, and the final archive layout. Actual rendering, redstone behavior, and multiplayer play still require an in-game Bedrock test; they are not claimed as verified by the automated suite. See `tests/GAMETESTS.md` for a human-runnable in-engine checklist.

## Development notes

- Behavior pack logic is in `behavior_pack/scripts/`; each device uses the shared `TortureDevice` lifecycle.
- Entity and block art, geometry, animations, and animation controllers are generated by the
  dev-only pixel-art pipeline in `tools/texturegen/` (`python3 tools/texturegen/build_assets.py`;
  QA renders with `tools/texturegen/preview.py`). The pipeline is never packaged into the `.mcaddon`.
- Entity dynamic properties persist server-side state; client-sync entity properties mirror state,
  durability, and reinforcement count, and drive the client animation controllers through
  `cc:anim_*` tags.
- Devices are static fixtures: no gravity and no block collision, so they cannot sink through an
  unloaded floor or shove a captive out of its seat.
- Device detection is local, idle checks are throttled, and the active-device ceiling is enforced.
- Natural structure/world generation and structure loot are not implemented in v0.1.3.

## License

See [`LICENSE`](LICENSE) for code and asset license terms.
