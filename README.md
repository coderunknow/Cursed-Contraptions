# Cursed Contraptions

**Five animated, placeable trap devices for Minecraft Bedrock multiplayer.**

Release **v0.1.5** · Declared minimum engine version **1.21.60**; prepared for the reported **Bedrock 26.2 multiplayer test**. Uses stable `@minecraft/server` 1.17.0; no Beta APIs toggle is required. Worlds created with v0.1.0–v0.1.4 keep their devices, captives, durability, and reinforcements.

## Features

- Five craftable devices, each **2.2–2.7 blocks tall** with its own silhouette, palette, capture
  range, damage, cycle speed, and durability. Hand-painted RGBA art for every entity atlas, block
  face, and inventory icon.
- **Fifteen animations per device**, including a hot `torturing_high` loop, a surge `burst`, a
  struggle `strain`, and four durability `wear` stages that show cracks and rust as the frame takes
  damage.
- **Soul-charge escalation:** every strike a captive survives winds the device up — shorter cycles,
  heavier hits — until the meter vents for a soul and one extra surge strike.
- **Containment you can trust:** a captive that is shoved, knocked or washed out of its device is
  pulled back and **takes no damage until it is inside again**; a captive that cannot be reseated is
  released instead of being left stuck.
- **Field repair:** hold iron, planks, bone, or obsidian (per device) to repair a damaged frame.
  Armor pieces reinforce an unoccupied device; interacting with an occupied device rescues first.
- **Soul shards and warding:** vented souls drop as soul shards when a frame breaks. Sneak + use any
  device while holding one to buy five minutes of immunity from capture.
- **Polish:** vanilla sound cues for every action, an action-bar status HUD for captives, wear
  textures, impact particles positioned between the frame and its prisoner.
- Redstone activation, persisted state, breakable durability, exactly one item drop on break, and a
  deterministic test suite; active-device limits, local entity queries, and bounded timers keep work
  predictable.

## Install

1. Download and import `Cursed-Contraptions.mcaddon` into Bedrock Edition.
2. Enable **both** packs in world settings — the behavior pack **and** the
   resource pack. Enabling only one of them is the most common reason an add-on
   looks empty.
3. Find the devices in the creative inventory under **Items → Cursed
   Contraptions (Devices)** (or search for *Iron Maiden*). In survival, craft
   them from the recipes below, or use `/give @s cc:item_iron_maiden` (replace
   the item ID for another device).
4. For a Realm, the owner should enable both packs on a copy of the world first; the shipped add-on uses stable APIs and does not require Beta APIs.

For a dedicated server, extract the `.mcaddon` and install each contained `.mcpack` in the matching `behavior_packs/` and `resource_packs/` directories. Add both packs to the world pack lists and restart.

## Play

### Place and capture

Place a device item on a solid surface. It becomes an animated device entity; the temporary anchor block is removed. Nearby eligible players and mobs are detected automatically. During the capture delay, leaving the configured radius cancels the attempt. Creative and spectator players are immune. On touch controls, aim at the device and use the localized **Use / Rescue** action; on keyboard/controller, use the normal entity-interact control. An empty-hand interaction explains what the device does and how to reinforce it.

### Rescue and reinforce

- **Rescue:** Interact with an occupied device. A teammate opens it and releases the captive, who is teleported clear and gets their movement back. A captive cannot free themselves.
- **Reinforce:** While the device is unoccupied, interact while holding a vanilla armor piece or elytra. The item is consumed; each piece raises durability and damage output while shortening the torture interval. Slots are limited per device.
- **Repair:** Interact while holding the device's repair material — iron (ingot, bars, chain, or block) for the Iron Maiden and Gravebinder Cage, planks or sticks for the Cursed Stocks and Regret Rack, bone for the bone frames, and obsidian for the Black Reliquary. Each item restores a fixed fraction of maximum durability; a full device refuses the item instead of eating it.
- **Ward:** Sneak + use any device while holding a soul shard to consume it for 5 minutes of immunity. Devices will not even start a capture on a warded player.
- **Break:** Attack the device. It has its own durability counter; breaking it releases the captive, drops exactly one device item, and drops one soul shard per two harvested souls.
- **Redstone:** Power an adjacent block to request an activation after the device's configured delay. Proximity capture remains enabled without redstone.

Torture cycles heal the captive first, then apply damage capped to leave at least one health point. This keeps a normal cycle from instantly killing a full-health captive. Other hazards and player actions can still be dangerous; death releases the device.

### Soul charge

While a captive is contained, every strike it survives adds one charge step (a captured player sees
the meter in the action bar):

| Charge | Effect | Animation |
| --- | --- | --- |
| 0 | configured damage and cycle | `torture` |
| 1 | +30 % damage, 10 % faster cycles | `torture` |
| 2 | +60 % damage, 20 % faster cycles | `torture` |
| 3 | +90 % damage, 30 % faster cycles | `torturing_high` |
| 4 | vents: one soul harvested and a surge strike at 1.5× the charged damage | `burst` |

Charge decays while the device is empty, so a fresh victim always starts at step 0.

## Troubleshooting

**No devices in the creative inventory.** Check, in order:

1. Both packs are enabled for the world (behavior *and* resource).
2. The world was reloaded after enabling them; a world keeps its pack list, so
   re-importing an add-on requires re-enabling the pack.
3. Run `/give @s cc:item_iron_maiden` (cheats on). If the command reports an
   unknown item, the **behavior pack** is not active; if the item arrives but
   has no icon, the **resource pack** is not active.
4. The devices are a creative group, not loose items: look under **Items →
   Cursed Contraptions (Devices)**, or use the search box.
5. Open **Settings → Creator → Content Log** and reload; a rejected content file
   is reported there. `tests/validate_build.py` rejects an invalid creative group
   in CI, and v0.1.5 fixed the one that shipped in v0.1.4.

## Devices and default balance

Damage values are Minecraft health points (two points per heart). Armor bonuses apply per installed armor piece.

| Device | Capture radius | Cycle | Normal damage | Critical chance | Durability | Armor slots |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Iron Maiden | 1.5 | 3 s | 10–18 | 5% | 200 | 4 |
| Cursed Stocks | 1.2 | 4 s | 4–8 | 3% | 150 | 2 |
| Gravebinder Cage | 1.8 | 2.5 s | 6–14 | 8% | 180 | 3 |
| The Regret Rack | 1.4 | 5 s | 8–16 | 4% | 300 | 4 |
| The Black Reliquary | 2.0 | 2 s | 12–20 | 10% | 250 | 4 |

Critical damage and healing are device-specific, and the cycle column is the base interval before
armor and soul-charge speed-ups; exact values are in `behavior_pack/scripts/config.js`.

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
- `/scriptevent cc:souls` — Add a stack of soul shards (for testing the ward).
- `/scriptevent cc:devices` — List registered devices and their state/durability/armor/souls.
- `/scriptevent cc:debug on` / `/scriptevent cc:debug off` — Toggle server and chat debug logging.

## Build and tests

Requirements: Python 3, Node.js 22+, and Info-ZIP (`zip`). The packs themselves have no runtime dependencies; `npm install` fetches dev-only type-checking tooling (`typescript`, `@minecraft/server` typings) that never ships inside the packs.

```bash
npm install        # Dev-only tooling for the type-check gate
npm test           # 38 tests: unit, manager, admin-command, lifecycle, mechanics, integration
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
  durability, reinforcement count, soul charge (`cc:charge`), and souls (`cc:souls`). The animation
  controllers read `cc:anim_*` state tags, `cc:anim_wear_*` durability tags, and the `cc:charge`
  property, so the client picks the right loop with no extra server round trip.
- Captive anchoring lives in `utils/containment.js`, the ward in `utils/immunity.js`, and sound/HUD
  feedback in `utils/feedback.js`; `device-base.js` owns the lifecycle and gates every damaging
  action behind a containment check.
- Devices are static fixtures: no gravity and no block collision, so they cannot sink through an
  unloaded floor or shove a captive out of its seat.
- Device detection is local, idle checks are throttled, and the active-device ceiling is enforced.
- Natural structure/world generation and structure loot are not implemented in v0.1.5.
- Creative-menu placement is declared once, in `behavior_pack/item_catalog/crafting_item_catalog.json`,
  and every item/block points at the group it defines; the pack validator keeps the two in sync.

## License

See [`LICENSE`](LICENSE) for code and asset license terms.
