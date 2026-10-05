# Cursed Contraptions — Design Log

Persistent project memory for future agents. The user's current requests
are always authoritative over anything recorded here.

---

## User Intent

### v0.1.3 → v0.1.5 request (2026-10-05)
> Build v0.1.5.
>
> Known real bugs/issues:
> - Some items have jagged/aliased visuals.
> - Most items do not work correctly with mobs.
> - Animations are too limited and do not properly show states such as opening/closing, etc.
> - The overall result is not badass enough. :))
>
> For v0.1.5:
> - Improve performance and runtime efficiency.
> - Expand and improve animations, including clear open/close state transitions and other appropriate item states.
> - Polish visuals and overall presentation.
> - Make item behavior work reliably across all supported items and mob interactions.
> - Keep the implementation clean, efficient, maintainable, and free of technical debt.
> - Fix the actual underlying issues rather than adding superficial workarounds.
> - Avoid unnecessary complexity and duplicated logic.
> - Preserve compatibility with the existing project unless a change is necessary.
>
> - Do NOT merge the PR, do NOT create or tag a release.

### Damage policy (answered by user 2026-10-05)
> Allow devices to kill on critical/durability-out. Keep the normal non-lethal 1 HP
> cap for standard damage, but add a very small random chance for an extreme
> critical hit that deals exactly 20 HP (10 hearts). This rare event may kill the
> captive outright. The critical hit should be uncommon enough that normal torture
> cycles remain non-lethal, while still making the device feel more dangerous and
> unpredictable.

### Sound effects (answered by user 2026-10-05)
> Yes, add appropriate vanilla SFX — trigger existing Minecraft sounds (iron door
> latch, anvil use, mob hurt, ambient cave) for detect/close/torture/open/break
> events per device.

### Containment review (answered 2026-10-05)
User clarified intent after the initial v0.1.5 pass over-restricted mobs:
1. **Mob capability**: captured mobs retain **normal movement and combat behavior** — walk, run,
   jump, climb, swim, fly, turn, attack, make noise normally. Do NOT apply Slowness, Weakness,
   Blindness, Mining Fatigue, Jump Boost, or any other debuff. Containment comes from physical
   position correction, not status effects.
2. **Breakouts**: big hazards (TNT/creeper explosions, Ender Dragon, Wither, other major
   hazards) can break or bypass the device. Mobs chip durability based on their damage/effort
   while pushing against the boundary, not categorically by strong/weak tier.
3. **Knockback**: wider drift window — hits/explosions/water should visibly shove the captive
   around inside the device before a correction pulls them back.
4. **Player vs mob**: same containment outcome (both contained) but different mechanisms —
   players get movement-input lock; mobs get position correction only.

Initial v0.1.5 pass (Slowness 25 + Jump -128 + Mining Fatigue V + Weakness IV + Blindness)
over-restricted mobs into statues. That implementation was revised per above.

---

## Implementation History

### v0.1.3 (pre-agent)
- Stable `@minecraft/server` 1.17.0, `min_engine_version` [1,21,60].
- Five devices: Iron Maiden, Cursed Stocks, Gravebinder Cage, Regret Rack, Black Reliquary.
- Animations: 9 per device (idle, detect, close, closed, torture, strain, open, released, broken) with tag-driven controllers.
- Containment: Slowness amplifier 6 ("Slowness VII") for mobs, InputPermissionCategory.Movement = false for players.
- Mob drift correction threshold: mobDriftLimit=1.25, mobEscapeLimit=2.5, playerDriftLimit=2.0, leashRadius=16. Correction at most once every 20 ticks.
- Release/broken timers used global CONFIG.timings.releaseAnimationTicks=30 / brokenAnimationTicks=30, but per-device client animations had different lengths (cursed stocks open 22 ticks, iron maiden open 30, black reliquary open 38, etc.), causing transitions to cut off or hold dead air.
- Hitbox: two identical component groups `cc:seated` and `cc:empty` swapped by seat/clear events (dead code).
- Captives teleported to device origin (x+0.5, y, z+0.5), which misaligned for regret rack seat height 0.35 and for other devices.

### v0.1.5 first pass (committed 2026-10-05 as 0c8605a) — NEEDS DESIGN REVIEW
- Bumped all manifests/package/build banner to 0.1.5.
- **Per-device timing keys added to config.js**: `openTicks`, `releasedTicks`, `brokenTicks`, `seatOffset`, `sounds`.
- **Containment change (NEEDS REVIEW)**: Replaced single Slowness 6 with a 5-effect stack:
  - Slowness amplifier 25 ("fully halt movement")
  - Jump Boost amplifier 128 ("prevent jumping/spider climbs")
  - Mining Fatigue amplifier 4 ("stop attacks/breaking")
  - Weakness amplifier 3 (stacked with device-specific weakness)
  - Blindness amplifier 0 ("stop target tracking")
  - This may be over-restricting mobs beyond intended gameplay.
- Tightened mob drift/escape: mobDriftLimit 1.25→0.9, mobEscapeLimit 2.5→1.6, playerDriftLimit 2.0→1.6, leashRadius 16→12, seatRefreshTicks 20 unchanged.
- Detection: single getEntities query with excludeFamilies (inanimate + cc_device); two-query fallback.
- Tick intervals: active 5→4 ticks, idle 20→16, redstone 10→8.
- Added `dimension.playSound()` calls at detect/close/torture/open/release/break/hit/reinforce with per-device config + pitch jitter.
- Extreme damage: 20 HP un-capped, can kill. Standard damage still capped at 1 HP.
- Removed duplicate component groups; added capturing-state rescue prompt.
- Added per-device seatOffset used when teleporting captives.
- Updated tests/mocks with playSound, excludeFamilies, triggerEvent, getRedstonePower stubs.
- All 42 tests pass; typecheck passes; build validates; PR #8 opened.

### v0.1.5 revision after containment design review (committed as follow-up to 0c8605a)
- Removed ALL mob debuff effects (Slowness, Jump, Mining Fatigue, Weakness, Blindness stacks).
  `_applyMobEffects` and `_clearMobEffects` are now intentional no-ops; `_seatVictim` and
  `_unseatVictim` skip effect application/removal for mobs; `_applyDebuff` only applies to
  players (per-config weakness, cosmetic only since movement is already locked).
- Widened drift thresholds: mobDriftLimit 0.9→1.5, mobEscapeLimit 1.6→2.2, playerDriftLimit
  1.6→2.2 (wider knockback feel).
- Added `_applyStruggleChip(distance)`: mobs pushing against the boundary chip durability
  proportional to effort (chance scales with distance past the drift band).
- Mobs retain full movement/combat capability (walk, run, jump, climb, fly, attack, sound);
  containment is purely position-correction based with the same once-per-20-tick correction
  cooldown to prevent judder stutter.
- Updated README and CHANGELOG to reflect the corrected containment design.
- Added DESIGN_LOG.md per user request.

---

## Decisions & Lessons

- **Bedrock Slowness amplifier values**: amplifier 6 is Slowness VII which only reduces speed by ~85% — this was the root cause of "mobs don't work right" (mob could still claw out). Amplifier ≥20 is reported to fully halt movement. However, the gameplay question of whether mobs *should* be fully frozen (vs. held in place but able to attack) is a design call, not an implementation one. See pending questions above.
- **Component groups**: identical seated/empty hitboxes were dead code. Kept the events as no-op stubs so existing triggerEvent callsites don't error.
- **Animation timings**: matching server timers to client animation lengths is required for smooth transitions; global constants don't work across devices with different animation durations.
- **Backward compatibility**: pack UUIDs, dynamic property keys, entity properties, tags, recipes, and the stable 1.17.0 API are preserved across versions so existing worlds keep working.
- **In-engine verification is manual**: the automated suite cannot render assets, simulate client input, or test multiplayer on a real Bedrock host. tests/GAMETESTS.md is the human in-engine checklist.
