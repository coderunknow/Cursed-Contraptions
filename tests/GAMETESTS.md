# In-engine GameTest checklist

Everything in `tests/gametest/` is **dev-only** tooling. It is not included in
the shipped `Cursed-Contraptions.mcaddon` (the build script only packs
`behavior_pack/` and `resource_pack/`, and the GameTest pack intentionally
depends on beta script modules — GameTest is beta-only).

These tests are not run by `npm test` or the pack-build validator. They require a
Bedrock client/server and must be run in-engine; the automated checks use mocks
and cannot validate real rendering, touchscreen/controller input, Realm pack
propagation, or multiplayer behavior. Run the relevant steps below in a test
world before treating those live behaviors as verified.

## 1. World setup (one time)

1. Copy `tests/gametest/behavior_packs/cursed_contraptions_gametests/` into
   `development_behavior_packs/` of your Bedrock installation (or into the
   `behavior_packs/` folder of a dedicated server).
2. Create a **new flat world** (flat preset) with:
   - **Cheats: ON** (required for `/gametest` and `/scriptevent`).
   - Game mode: Survival (the simulated players bring their own modes).
   - Experiments: **Beta APIs: ON** (needed by the GameTest pack only — the
     shipped packs still use purely stable APIs).
3. In world settings, enable all three packs in this exact order:
   1. *Cursed Contraptions* (resource pack)
   2. *Cursed Contraptions* (behavior pack)
   3. *Cursed Contraptions GameTests (dev-only)*

## 2. Create the test structures (one time)

Each test needs an empty 12×12×12 structure with the same name. Stand in a
flat spot and run these six commands, then save:

```
/gametest create cc:capture_rescue 12 12 12
/gametest save
/gametest create cc:escape_cancels 12 12 12
/gametest save
/gametest create cc:reinforce_consumes 12 12 12
/gametest save
/gametest create cc:break_drop 12 12 12
/gametest save
/gametest create cc:creative_immunity 12 12 12
/gametest save
/gametest create cc:redstone_triggered 12 12 12
/gametest save
```

## 3. Run the suite

Run each test (or `/gametest runall cc:all` to run them in sequence):

```
/gametest run cc:capture_rescue
/gametest run cc:escape_cancels
/gametest run cc:reinforce_consumes
/gametest run cc:break_drop
/gametest run cc:creative_immunity
/gametest run cc:redstone_triggered
```

Expected: every test reports **passed**. Coverage:

| Test | What it proves |
| --- | --- |
| `cc:capture_rescue` | Proximity capture → movement lock → `cc:trapped` tag → teammate rescue restores movement and returns the device to idle. |
| `cc:escape_cancels` | Leaving the capture radius during the capture delay cancels the attempt; no tags are leaked. |
| `cc:reinforce_consumes` | One armor piece is consumed, `cc:armor_count` becomes 1, durability becomes 250 (200 + 50). |
| `cc:break_drop` | Lethal damage breaks the device, drops **exactly one** `cc:item_iron_maiden`, and removes the entity after the broken animation. |
| `cc:creative_immunity` | A creative player standing in range is never captured. |
| `cc:redstone_triggered` | Power on adjacency with an out-of-range target does nothing (negative control), then a fresh rising edge with an in-range target activates the device. |

Known limitations of the checks:

- `redstone_triggered` proves the end-to-end chain (power → activation). The
  activation can also come from the normal idle proximity poll, so strict
  timing attribution to the redstone path alone is observational.
- Simulated players never fully reproduce touch/controller interaction or
  Realm propagation; verify these paths with real Bedrock clients.

## 4. Manual spot-checks not automatable here

1. `/tag @s add cc:admin`, then `/scriptevent cc:give`,
   `/scriptevent cc:devices`, `/scriptevent cc:debug on` and
   `/scriptevent cc:debug off` (these need cheats ON).
2. Place each of the five devices from the creative inventory or by crafting;
   the anchor block must disappear and the animated device entity appear.
3. Inspect every device model and inventory icon in daylight and shade. Check
   that no atlas texture is missing, stretched, cropped, or bleeding across UVs.
4. On a touch client, aim at a device and confirm the localized **Use / Rescue**
   button appears and works. On keyboard/controller, interact with the entity
   using the normal control. Empty-hand use should explain its automatic capture
   and reinforcement behavior; repeated taps should not flood chat.
5. Hold an armor piece, reinforce an unoccupied device, and confirm only one
   item is consumed. Fill its slots and confirm further armor is rejected without
   being consumed. Capture a player and a mob; rescue the player with a second
   player and verify self-rescue receives guidance.
6. Watch the animations cycle (idle → close → torture → open → idle), break a
   device, and verify the captive is released and exactly one device item drops.
7. For the reported target, repeat the interaction/capture checks with two
   Bedrock 26.2 clients in a copied hosted multiplayer/Realm world after the
   owner enables both packs. Confirm a rejoin preserves/reconciles the device.
   Do not treat the mocked suite or a single-player test as Realm verification.

## 5. v0.1.3 spot-checks (reported defects)

These target the three defects reported against v0.1.2. Run them before treating
the v0.1.3 fixes as verified.

1. **Visible placement.** Place each of the five devices on solid ground and in
   mid-air against a wall, at chunk borders, and after a fresh world load. Every
   placement must leave a visible device: no invisible obstacle, no floating
   anchor cube left behind, and no missing-texture checkerboard on the item icon
   in the hotbar or creative inventory.
2. **Mob containment.** Cage a zombie, a skeleton, a cow, and a villager in turn.
   Each captive should stay inside the frame, occasionally struggle (strain
   animation plus a dust puff), and never judder, teleport in place, or clip
   through the device. Confirm the captive cannot be pushed out by other mobs or
   by flowing water.
3. **Rescue while occupied.** With a device holding a player, aim at the frame
   from outside and confirm the **Use / Rescue** action still appears and frees
   the captive. This was unreachable in the previous build.
4. **Animation coverage.** Watch a full cycle on each device and confirm the
   detect, close, closed-idle, torture, strain, open, released, and broken
   animations all play, and that doors/bars/wheels return to their rest pose
   when the device goes idle.
5. **Feedback.** Hit a device and confirm sparks and (when occupied) a flinch.
   Reinforce one with armor and confirm the burst and message. Break one and
   confirm the release animation, the freed captive, and exactly one item drop.

## 6. v0.1.4 spot-checks (scale, mechanics, polish)

These target the v0.1.4 request ("bigger, more animations and mechanics") and the
reported bug ("mobs get pushed out but still get damage"). Run them before
treating the v0.1.4 feature set as verified.

1. **Scale and readability.** Place all five devices side by side. Each should
   stand 2.2+ blocks tall, read as a distinct contraption from four sides and
   diagonally, and never clip into a two-block ceiling or look like a
   half-width prop. Check the collision box (walk into it) matches what you see.
2. **Containment honesty (the reported bug).** Capture a zombie, then shove it
   with a piston, wash it with a water bucket, and knock it with a sword. It
   must snap back inside the frame and take **no** damage while outside; the
   `/scriptevent cc:devices` durability must only fall while it is visibly
   seated. Repeat with a cow and a villager (they have different AI).
3. **Stuck-release path.** Fill the seat area with blocks so a captive cannot be
   reseated, then confirm the device frees it with "You slipped free of the
   device." instead of damaging an invisible prisoner.
4. **Soul charge.** Stand in a device (or cage a mob) and watch the action-bar
   pips: 0 → 3 uses the normal torture loop, and from 3 the animation turns
   hotter (`torturing_high`). At 4/4 the frame should vent with the `burst`
   overlay, play the surge/soul cues, and increment the soul count.
5. **Soul shards and warding.** Break a device that has vented at least twice and
   confirm soul shards drop. Sneak + use a device while holding a shard: the
   ward message appears, the shard is consumed once, and devices will not claim
   you for five minutes (including after a relog).
6. **Field repair.** Damage a device, then hold its repair material and use the
   device: durability must rise, the material must be consumed once, and the
   wear overlay (cracks/rust) must step back down. At full durability the
   material must not be consumed.
7. **Wear visuals.** Knock a device down through the four wear stages and
   confirm the cracks spread from the panels to the roof and plinth, then
   repair it back to stage 0.
8. **HUD and audio.** As a captive, confirm the action bar shows device, state,
   seconds, and pips, and that it does not flicker or spam. Confirm a strike,
   latch, release, repair, reinforcement, surge, and break each produce a
   distinct vanilla sound from outside the device.
9. **Rescue still wins.** Interact with an occupied device as a teammate: rescue
   must take priority over reinforcement and repair, the captive must be freed,
   moved clear, and given their movement back, and they can be recaptured
   afterwards.
10. Create a fresh copy of the world so old devices load with the new properties
    (`cc:charge`, `cc:souls`) and confirm the wear tags and animations resync.
11. **Death and relog recovery.** Die while trapped, then respawn: you must be
    able to move immediately and no device should still list you as its captive
    (`/scriptevent cc:devices`). Repeat with a disconnect during the closed
    animation and a rejoin.

## 7. v0.1.4 hotfix spot-check (creative-menu registration)

1. Enable both packs in a world and open the creative inventory. The five
   devices (and their five placeholder anchor blocks) must appear under
   **Items → Cursed Contraptions (Devices)**, with icons and names. Searching
   for "Iron Maiden" must also find it.
2. Confirm the Content Log shows no `menu_category`/item-group error on world
   load. If the items are missing, run `/give @s cc:item_iron_maiden`: an
   unknown item means the behavior pack is off, a missing icon means the
   resource pack is off.

## 8. Placement check (v0.1.4 rebuild)

1. Take a device from the creative menu (or craft one) and place it on the
   ground, on a wall, and on a block you are standing on. The device entity must
   appear where you placed it and the item must be consumed in survival.
2. Confirm the same works for all five devices, and that the crafted item (not
   just the creative entry) can be placed.
3. Confirm a freshly placed device looks new: no cracks/rust overlay, and
   `/scriptevent cc:devices` reports full durability (200 for the Iron Maiden,
   150 Stocks, 180 Cage, 300 Rack, 250 Reliquary).
4. Break a device and confirm exactly one device item drops and can be placed
   again.
