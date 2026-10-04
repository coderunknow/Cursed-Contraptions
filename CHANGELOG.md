# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-10-04

Repair and playability release based on the reported Bedrock 26.2 hosted-multiplayer
scenario. Existing identifiers, pack UUIDs, save keys, recipes, and balance are
preserved. The declared minimum engine/API remain unchanged; the shipped packs
continue to use stable `@minecraft/server` 1.17.0 without Beta APIs.

### Fixed

- **Interaction prompt and feedback.** Custom devices now use a localized
  `Use / Rescue` touch-screen action, explicitly target player interactions,
  and avoid unnecessary swing animations. Empty-hand use explains automatic
  player/mob capture and reinforcement; captives receive clear self-rescue
  feedback. The stable interaction event uses the item snapshot from before
  the interaction and still verifies the selected inventory slot before
  consuming reinforcement.
- **Block texture loading.** All five terrain atlas entries pointed at
  `textures/blocks/cc_...png`, but the tracked images are named
  `textures/blocks/...png`; atlas paths now match the actual files.
- **UV/texture atlas bounds.** Entity box-UV layouts exceeded the declared
  32-texel texture width, and several models declared a texture height that did
  not match the PNG. Entity material textures now have 64-texel-wide atlases
  (64×64, 64×32, 64×48, 64×64, and 64×16); the five block material textures
  and block geometries use consistent 64×64 tiled atlases. Geometry dimensions
  match their images, every legacy box-UV net stays within its atlas, and the
  Black Reliquary door UV was moved up three texels to fit its 64-pixel height.
  This avoids out-of-range UVs being wrapped/clamped into visible texture patches.
- **Inventory icons.** Replaced the five colored-bar placeholders with
  individual transparent pixel-art silhouettes.

### Validation

- Added interaction-event regression coverage for idle guidance/throttling,
  reinforcement item consumption, and teammate rescue; the device unit test
  pins the self-rescue refusal behavior.
- Hardened the build validator to resolve atlas texture files, compare model
  texture dimensions to source PNGs, and verify localized interaction prompts
  and their entity events.
- Automated tests, stable API type check, source-reference validation, and
  `.mcaddon` archive checks are required before packaging. Live Bedrock 26.2
  rendering, touch input, Realm propagation, and multiplayer remain a manual
  test gate; no in-engine pass is claimed here.

## [0.1.1] - 2026-10-03

Bug-fix, audit, and polish patch. Save format, UUIDs, `@minecraft/server` 1.17.0
dependency, `min_engine_version` `[1, 21, 60]`, all identifiers, dynamic-property
keys, entity properties, and tags are unchanged from v0.1.0; worlds created with
v0.1.0 load without migration. No balance values changed.

Items marked *(unverified in-engine)* passed every automated check but were not run
inside Minecraft — see `tests/GAMETESTS.md` for the human verification checklist.

### Fixed

- **F1 — pack-breaking.** Admin commands migrated from the beta-only
  `world.beforeEvents.chatSend` API to stable `system.afterEvents.scriptEventReceive`.
  In v0.1.0 evaluating `world.beforeEvents.chatSend.subscribe(...)` at module top level
  threw an uncaught `TypeError` under the declared stable 1.17.0 dependency (no Beta
  APIs toggle is used), so the script module could never reach the command handlers.
  Commands are now `/scriptevent cc:give`, `/scriptevent cc:devices`, and
  `/scriptevent cc:debug on|off`, still gated by the `cc:admin` tag. Every top-level
  event subscription is additionally wrapped so one failing subscription can never
  abort module evaluation again. *(unverified in-engine)*
- **F6.** `/scriptevent cc:devices` sends one chat message per device entry; the old
  single concatenated string was truncated by the Bedrock client at a few hundred
  characters once several devices were placed. *(unverified in-engine)*
- **F9.** A device that throws inside `tick()` (or during the redstone poll) is now
  contained per device: one broken device can no longer kill the shared gameplay
  interval for every other device.

### Cleaned up

- **F4.** Removed a dead second argument from `_lockVictimMovement(victim, false)`;
  the method takes one argument, so `false` was ignored. No behavior change.
- **F5.** Removed the unreachable tag-scoped fallback scan in `_getVictim()`:
  `world.getEntity` and `Dimension.getEntities` read the same loaded-entity registry,
  and the same dimension/distance rules already ran for the id candidates, so the
  scan could never find anything the direct lookups rejected.
- **F7.** Removed dead `spawn_egg` color config from the five client entity files.
  The colors only style a creative spawn egg, which does not exist while the
  behavior-pack entities are `is_spawnable: false`. No behavior change.
- **T1.** Removed dead no-op loops/checks in `tests/validate_build.py`.
- **T2.** Removed the orphaned `Debug.inspectDevice` helper (zero call sites).

### Docs

- **F1.** “Admin tools” rewritten for the `/scriptevent` syntax (notes that
  `/scriptevent` requires cheats enabled; the `cc:admin` tag gate is unchanged).
- **F3.** The features list no longer claims a total device-count cap; only the
  active-device limit (`maxActiveDevices: 32`) exists.
- **F2.** Audit correction: the v0.1.0 give counters were **not** inverted —
  `Container.addItem` returns `undefined` on success and the leftover stack on
  failure, and the code counts accordingly. Pinned by regression tests so the
  correct logic is not “fixed” into a bug later.
- **F11.** Version references updated to v0.1.1; balance table re-verified against
  `config.js` (unchanged); “Build and tests” documents the new dev-only tooling.

### Internal (tooling)

- **L1.** Added a type-conformance gate: `tsc` with the real
  `@minecraft/server` 1.17.0 typings over `behavior_pack/scripts` (dev-only,
  never shipped in the packs), wired into CI. Baseline census resolved to zero
  errors: 1 real error (F1), 1 dead argument (F4), 14 false positives fixed with
  accurate JSDoc typings — no error suppressed.
- **L2.** Mock harness extended with stable-1.17.0-accurate `world.afterEvents`
  / `system.afterEvents.scriptEventReceive` signals (including namespace
  filtering) and `world.getDimension`; added admin-command and device-manager
  regression tests (suite: 21 → 32 tests).
- **L3.** Added a dev-only GameTest behavior pack in `tests/gametest/` plus
  `tests/GAMETESTS.md` so a human can run the in-engine checklist (~10 minutes).
  It is not part of the shipped `.mcaddon`.

## [0.1.0] - 2026-10-02

Initial release: five animated, placeable trap devices (Iron Maiden, Cursed Stocks,
Gravebinder Cage, The Regret Rack, The Black Reliquary) with proximity capture,
rescue/reinforce interactions, redstone activation, persisted state, durability,
recipes, and an automated validation/build pipeline.
