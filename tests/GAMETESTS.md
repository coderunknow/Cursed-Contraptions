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
