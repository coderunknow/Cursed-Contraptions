# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-10-04

Art, containment, and placement release, built from three in-game reports:
*"some items cannot be placed — they are invisible after placement"*,
*"the cage mechanics are rough and make mobs stutter"*, and *"the objects need
more animations and polish"* (clarified in discussion as: something is there,
but nothing renders). Identifiers, pack UUIDs, dynamic-property keys, and
recipes are unchanged, so existing worlds keep their devices, captives, and
reinforcement. The declared minimum engine version and the stable
`@minecraft/server` 1.17.0 dependency are unchanged; no Beta APIs are used.

### Fixed

- **Invisible devices (rendering).** Every shipped texture was a grayscale or
  indexed-colour PNG, and Bedrock silently refuses to bind those to entity
  models — which is exactly the reported symptom of a device that has a hitbox
  but draws nothing. All seventeen textures (5 entity atlases, 5 block faces,
  5 inventory icons, 2 pack icons) are now 8-bit true-colour RGBA, and
  `tests/validate_build.py` rejects any texture that is not colour type 6, so
  the regression cannot return unnoticed.
- **Invisible anchor blocks.** The placeable block pointed at
  `geometry.cc_iron_maiden_block`, a model that was never written into the
  resource pack. A placed device that did not convert into an entity therefore
  left a completely invisible obstacle behind. Anchor blocks are now plain full
  cubes with a painted side texture, and the dangling geometry reference is gone.
- **Silent placement failure.** Placement converted the anchor block exactly
  once, one tick later, and gave up without a trace if the chunk was not loaded
  or the block no longer matched. Conversion now retries with a growing delay,
  accepts whichever contraption anchor is actually present, refuses to stack a
  second device on an occupied block, and restores the anchor block if the
  entity cannot be created.
- **Mismatched item icons.** The item atlas published aliases such as
  `iron_maiden` while the item component requested `cc_item_iron_maiden`, so no
  inventory icon resolved. The atlas now publishes the aliases the items ask
  for, generated from a single table so the two cannot drift apart again.
- **Mob stutter.** Containment teleported a captive back onto its seat every
  five ticks and re-asserted the lock constantly, which read in-game as the mob
  juddering. A captive is now only moved when it genuinely leaves its drift
  window, and never more than once per second.
- **Duplicate block definitions.** Five hand-written
  `behavior_pack/blocks/*.json` files declared the same identifiers as the
  generated `*_block.json` files. Bedrock refuses to load a duplicated
  identifier, so the stale copies are deleted and the generator removes them on
  every rebuild.

### Changed

- **Containment model.** Captured players keep their movement input locked and
  are only pulled back when knocked far away. Captured mobs are held with
  Slowness VII plus Blindness (refreshed every second, particles disabled),
  which works on every vanilla mob with no custom entity definition and leaves
  the captive visibly struggling rather than frozen mid-air. Ordinary drift
  never triggers a correction; only a genuinely escaped captive is unseated.
- **Devices are static fixtures.** Device entities no longer apply gravity and
  no longer collide with blocks, so a device can never sink through a floor
  that unloads for a tick and can never squeeze a captive out of its own seat.
  Devices remain targetable, breakable, and unpushable.
- **Complete animation set.** Nine animations per device (`idle`, `detect`,
  `close`, `closed`, `torture`, `strain`, `open`, `released`, `broken`) with
  controllers in which every state can reach every other state, including the
  previously unreachable `detecting` and `released` states on four devices.
  Animation lengths are aligned with the gameplay timings for capture delay,
  closing, the closed pause, and the torture interval.
- **Hand-painted art.** The five entity atlases, the five block textures, and
  the five inventory icons are painted pixel art with per-device palettes: iron
  plating and rivets, oak grain and rope, black iron bars over a bone skull,
  blood-stained timber with a tension wheel, and an obsidian reliquary with
  gold bands and a soul gem.
- **Feedback.** Hitting a device throws sparks; hitting an occupied device makes
  the captive flinch; capture, close, release, and reinforcement spawn
  particles; reinforcements and captives receive clear localized messages.
- **Release timing.** Hatching open now takes its full 1.5-second animation
  before the released state begins, instead of cutting the animation off.

### Validation

- `npm test` (33 tests: 9 unit, 24 in-scope lifecycle/integration) covers placement conversion, capture, containment,
  rescue, reinforcement, durability, break-and-drop, recovery, admin commands,
  and the full place → capture → torture → break → drop → unregister flow.
- `npm run typecheck` passes against the stable 1.17.0 API surface.
- `tests/validate_build.py` now fails on non-RGBA textures and on duplicated
  block identifiers, and the pack validates with 0 errors both before and after
  packaging.
- Automated checks cannot render assets or simulate a real client input path.
  In-engine rendering, touch controls, and Realm propagation still need a manual
  pass; see `tests/GAMETESTS.md`.

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
