# In-engine GameTest checklist

Everything in `tests/gametest/` is **dev-only** tooling. It is not included in
the shipped `Cursed-Contraptions.mcaddon` (the build script only packs
`behavior_pack/` and `resource_pack/`, and the GameTest pack intentionally
depends on beta script modules — GameTest is beta-only).

These tests could not be executed from the automated v0.1.1 audit environment
(`minecraft.net` was unreachable, so no Bedrock Dedicated Server). Run them
once by hand before merging; the whole flow takes about 10 minutes.

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
- Simulated players never fully reproduce touch-control interaction; verify
  one rescue on a real second device/console once.

## 4. Manual spot-checks not automatable here

1. `/tag @s add cc:admin`, then `/scriptevent cc:give`,
   `/scriptevent cc:devices`, `/scriptevent cc:debug on` and
   `/scriptevent cc:debug off` (these need cheats ON).
2. Place each of the five devices from the creative inventory or by crafting;
   the anchor block must disappear and the animated device entity appear.
3. Watch the animations cycle (idle → close → torture → open → idle) and the
   broken animation on break.
