# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.5] - 2026-10-05

Hotfix for *"I don't see any item in the game though I activate the add-on."*

### Fixed

- **Nothing appeared in the creative inventory.** Every item and anchor block
  declared `"group": "itemGroup.name.miscellaneous"`. Since Bedrock 26.x the
  creative group must be namespaced (`<namespace>:<name>`), so the game rejected
  the whole `menu_category` and dropped all ten entries from the creative menu —
  the add-on looked like it shipped no content at all. The devices now live in a
  real, namespaced group, `cc:itemGroup.name.devices`, defined by a new
  `behavior_pack/item_catalog/crafting_item_catalog.json` (icon: the Iron Maiden)
  and labelled *Cursed Contraptions (Devices)* in `en_US.lang`. `/give` and the
  crafting recipes were never affected; they are unchanged.
- **`tests/validate_build.py` now rejects this class of defect**: every item and
  block must declare a visible `menu_category` (`construction`, `equipment`,
  `items`, or `nature`), any `group` must be namespaced, and every group must be
  defined in the item catalog, list the declaring identifier, use a known icon,
  and have a localization key. A deliberately re-broken item fails the build
  (verified), so the defect cannot ship silently again.

Nothing else changed: identifiers, UUIDs, recipes, and balance are untouched, so
worlds from v0.1.4 keep their devices and captives. The pack version is bumped so
a world that already has v0.1.4 installed accepts the update.

## [0.1.4] - 2026-10-05

Scale, animation, mechanics, and polish release, built from the request
*"the objects should be bigger, have more animations and more mechanics"* and
the bug report *"the mobs when stuck, it still can be pushed out but still get
damage"*. Identifiers, pack UUIDs, dynamic-property keys, recipes, and the
declared `min_engine_version [1, 21, 60]` / `@minecraft/server` 1.17.0
dependency are unchanged; the new entity properties (`cc:charge`, `cc:souls`)
and tags are additive, so existing worlds keep their devices, captives,
durability, and reinforcements. No Beta APIs are used.

### Fixed

- **Damage outside the device (reported bug).** A captive was damaged on a
  timer with no containment check, and containment only reacted once a shoved
  mob had drifted 2.5 blocks — so a mob pushed out of the frame kept taking
  damage while it was visibly outside. The hold is now an anchoring loop
  (`utils/containment.js`): mob velocity is cleared every device tick, a capped
  impulse pulls the captive back to its seat, and a rate-limited teleport
  correction lands when it is genuinely out of the seat window. Damage,
  healing, and soul-charge growth are all gated behind a verified containment
  check, so a captive that is outside is pulled back instead of being hurt. A
  captive that cannot be reseated `maxFailedReseatCycles` times is released
  with a message rather than left in limbo.
- **Stale capture locks.** A player who relogged between capture and release
  could keep the `cc:trapped` tag, the movement lock, and the hidden
  `cc:movement_was_enabled` save. Recovery now clears all three from one shared
  code path (`TortureDevice.clearStaleCapture`).
- **Double-strike race.** A venting surge rescheduled the torture timer while
  the previous cycle was still pending, which could deliver two strikes for one
  cycle. `_scheduleNextDamage()` always retires the pending timer first.
- **Vestigial hit tests.** The seated and empty component groups were byte-for-byte
  identical. The seated hitbox is now slightly larger, so a rescuer's arrows and
  swings land on the closed frame instead of the prisoner inside it.

### Added

- **Soul-charge escalation.** Every strike a contained captive survives winds
  the device one step (`cc:charge`, 0–4): cycles shorten by 10 % per step and
  damage grows by 30 % per step. At 4/4 the meter vents — a soul is harvested
  and one surge strike lands at 1.5× the charged damage. Charge decays while
  the device is empty, and the client-synced property switches the animation
  controller to the hotter `torturing_high` loop with no extra round trip.
- **Field repair.** Interact with a damaged device while holding its configured
  material — iron (`ingot`/`bars`/`chain`, or an iron block), planks/sticks for
  the timber frames, bone, or obsidian — to restore a fraction of maximum
  durability. A full device refuses the material instead of consuming it.
- **Soul shards and immunity.** Vented souls drop as `cc:soul_shard` items when
  the frame is destroyed. Sneak + use any device while holding a shard to spend
  it for 5 minutes of immunity; a warded player is never detected, and the
  shard is consumed only when the ward binds. `/scriptevent cc:souls` grants a
  stack to admins for testing.
- **Action-bar HUD.** A captured player sees the device, state, seconds held,
  charge pips, and how to get out. It refreshes on every meaningful change and
  on a slow timer, and is cooldown-limited so it never spams.
- **Sound cues.** Profile-driven vanilla sounds for strike, slam, latch,
  release, reinforcement, repair, soul harvest, surge, and break. No new
  assets, and playback is wrapped so a missing id cannot break gameplay.
- **Wear animations.** A second animation controller per device adds
  `wear_0`…`wear_3`: cracks and rust spread from the panels to the roof/door and
  finally the plinth as durability falls, so a damaged device looks damaged.
- **Burst overlay.** The `burst` animation plays for the venting surge.

### Changed

- **All five devices are bigger.** Collision boxes and visible bounds are now
  derived from the finished geometry (world units): iron maiden 1.2 × 2.6,
  cursed stocks 2.25 × 1.59, gravebinder cage 2.27 × 2.62, regret rack
  1.78 × 2.25, black reliquary 1.79 × 2.68 — against v0.1.3 heights of
  1.81 / 1.12 / 1.50 / 0.88 / 2.06. Bounds can no longer ship stale, because a
  resized model regenerates them.
- **Fifteen animations per device** (`idle`, `detect`, `close`, `closed`,
  `torture`, `torture_high`, `strain`, `burst`, `open`, `released`, `broken`,
  `wear_0`…`wear_3`), with anchored bones and axis-correct mechanism wheels.
- **Atlas quality.** Broad patches were split into aspect-specific keys so no
  shared patch is stretched across a thin post or edge, and the painters got
  per-device palettes, rivets, grain, rust and glow passes.
- **Containment tuning.** Seat refresh is once per second, corrections are rate
  limited to one per 10 ticks, the leash is 18 blocks, and particle work per
  event is capped by `performance.maxParticlesPerEvent`.

### Validation

- `npm test` is now **38 tests** (9 unit, 12 device lifecycle, 2 manager, 9
  admin-command, 13 mechanics, 2 integration): the new `tests/mechanics.test.js`
  pins the shove → reseat → no-damage contract, the release path when reseating
  fails, the escalation sequence `[14, 18, 22, 26, 46]`, soul-shard drops, field
  repair, the immunity ward, the HUD, rescue, the single-drop guarantee, and the
  death/respawn movement recovery (both directly and through the real entry
  point). Shared fixtures moved to `tests/support/fakes.mjs`.
- `npm run typecheck` passes against the stable 1.17.0 API surface.
- `tests/validate_build.py` now resolves both controller files per device
  (state + wear), validates `cc:charge`/`cc:souls` on every entity, and checks
  client-entity controller aliases against the controller definitions.
- `tools/texturegen/build_assets.py` verifies required animations, bone
  references, atlas bounds, hitbox walkability on all four sides, and
  controller reachability before writing a single file.
- Automated checks cannot render assets or drive a real client input path.
  In-engine rendering, the knockback/shove feel, the HUD, sound mix,
  multiplayer rescue, and Realm persistence still need a manual pass; see
  `tests/GAMETESTS.md` and `V0.1.4_PLAN.md`.

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
