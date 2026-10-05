/**
 * Cursed Contraptions — Centralized Configuration
 *
 * Gameplay values live here so every device follows the same, auditable rules.
 */

export const CONFIG = {
  namespace: "cc",

  debug: {
    enabled: false,
    chatDebug: false,
  },

  performance: {
    /** Active devices (capturing/closed/torturing/opening) tick every this many ticks. */
    pollIntervalTicks: 4,
    /** Idle devices (no captive) are scanned for new targets this often. */
    idlePollIntervalTicks: 16,
    /** Redstone power of adjacent blocks is polled this often. */
    redstonePollIntervalTicks: 8,
    /** Minimum ticks between per-player feedback messages to avoid spam. */
    interactionFeedbackCooldownTicks: 25,
    /** Cap on how many devices can be mid-cycle at once (placement is always allowed). */
    maxActiveDevices: 32,
    /** Particle cap per individual spawn event, per particle type. */
    maxParticlesPerEvent: 10,
    /** Grace ticks after a chunk load before we trust recovered state. */
    chunkLoadGracePeriod: 30,
  },

  /**
   * Placement pipeline. The anchor block is converted to the device entity on
   * the next tick; if the chunk is not loaded yet the conversion retries with
   * a growing delay rather than silently losing the device (v0.1.2 bug).
   */
  placement: {
    initialDelayTicks: 1,
    maxAttempts: 6,
    retryBackoffTicks: 4,
    /** Prevent stacking two devices in the same block. */
    duplicateRadius: 0.75,
  },

  /**
   * Containment.
   *
   * v0.1.5 design decision (confirmed by user): captured MOBS retain full
   * normal behavior — they can walk, run, jump, climb, swim, fly, turn,
   * attack, and make noise normally. No Slowness, Weakness, Blindness, or
   * other debuffs are applied. Containment comes purely from physical
   * position correction: when a mob leaves the containment zone it is
   * teleported back to the seat with a rattle/strain animation.
   *
   * Players are still movement-locked via InputPermissions (different
   * mechanism, same containment outcome). Wider drift windows preserve
   * knockback feel (from hits, explosions, water) while still preventing
   * escapes.
   */
  containment: {
    /** Distance past which a captive rattles the frame (blocks). */
    mobDriftLimit: 1.5,
    /** Distance a mob must reach before it is pulled back. */
    mobEscapeLimit: 2.2,
    /** Players may drift with knockback/water before being pulled back. */
    playerDriftLimit: 2.2,
    /** Beyond this distance the captive has genuinely escaped and is freed. */
    leashRadius: 12,
    /** Minimum ticks between corrections for the same captive. */
    correctionCooldownTicks: 20,
    /** How often we check on the seated captive. */
    seatRefreshTicks: 20,
    /**
     * Chance (per second of active struggling) that a mob chips 1 durability
     * off the device while pushing against the boundary — "depends on damage
     * and effort, not strong/weak mobs." Higher when the mob is pressed
     * against the edge, zero when standing calmly in the center.
     */
    mobStruggleChipChance: 0.35,
  },

  /** "The captive is struggling" rattle overlays. */
  struggle: {
    enabled: true,
    minIntervalTicks: 80,
    maxIntervalTicks: 280,
    /** How long a strain/rattle overlay plays, in ticks. */
    strainDurationTicks: 12,
  },

  /**
   * Animation timings (ticks).
   *
   * Per-device open/released/broken values live on each device config entry
   * (``config.openTicks`` etc.) so the server state transitions line up with
   * the exact client-side animation length for that device. v0.1.3 used
   * global constants here which cut off or dead-aired transitions on several
   * devices.
   *
   * The ``releaseAnimationTicks`` / ``brokenAnimationTicks`` keys are kept as
   * legacy fallbacks for the test suite and any external callers; new code
   * should read ``device.config.openTicks`` / ``releasedTicks`` /
   * ``brokenTicks`` directly.
   */
  timings: {
    closedPauseTicks: 10,
    /** Legacy fallback — devices use ``config.openTicks`` instead. */
    get releaseAnimationTicks() { return 30; },
    /** Legacy fallback — devices use ``config.brokenTicks`` instead. */
    get brokenAnimationTicks() { return 30; },
  },

  particles: {
    impactEnabled: true,
    smokeCount: 5,
    sparkCount: 3,
    /** Extra burst when a device closes on a victim. */
    captureBurstCount: 8,
    /** Extra burst when a device breaks. */
    breakBurstCount: 12,
  },

  /** Audio polish using existing vanilla sound events (no custom assets). */
  sounds: {
    enabled: true,
    /** Pitch jitter keeps repeated events from sounding robotic. */
    pitchJitter: 0.12,
    volume: 1.0,
  },

  /**
   * Vignette — the brief blindness flash a captured player sees each cycle.
   * Disabled because v0.1.3's persistent blindness felt like a bug; we still
   * apply weakness as a mechanical debuff.
   */
  vignette: {
    enabled: false,
    fadeInTicks: 6,
  },

  ironMaiden: {
    captureRadius: 1.5,
    captureDelay: 20,
    closeDuration: 30,
    openTicks: 30,
    releasedTicks: 20,
    brokenTicks: 30,
    tortureInterval: 60,
    tortureMinDamage: 10,
    tortureMaxDamage: 18,
    extremeDamageChance: 0.05,
    extremeDamageAmount: 20,
    extremeDamageLethal: true,
    healAmount: 6,
    weaknessAmplifier: 0,
    weaknessDuration: 100,
    baseDurability: 200,
    armorSlots: 4,
    armorDurabilityBonus: 50,
    armorDamageMultiplier: 1.15,
    armorSpeedMultiplier: 0.9,
    redstoneActivationDelay: 10,
    dropOnBreak: true,
    /** Where the captive is seated relative to the device origin, in blocks. */
    seatOffset: { x: 0, y: 0.1, z: 0 },
    /** Sound events for state transitions. */
    sounds: {
      detect: { event: "random.iron_golem", volume: 0.35, pitch: 0.7 },
      close: { event: "random.anvil_land", volume: 0.9, pitch: 0.8 },
      torture: { event: "mob.blaze.hit", volume: 0.45, pitch: 0.5 },
      open: { event: "random.door_open", volume: 0.7, pitch: 0.6 },
      release: { event: "random.explode", volume: 0.25, pitch: 1.4 },
      break: { event: "random.anvil_break", volume: 1.0, pitch: 0.9 },
      hit: { event: "random.anvil_use", volume: 0.4, pitch: 1.2 },
      reinforce: { event: "random.anvil_use", volume: 0.6, pitch: 1.5 },
    },
  },

  cursedStocks: {
    captureRadius: 1.2,
    captureDelay: 15,
    closeDuration: 20,
    openTicks: 22,
    releasedTicks: 16,
    brokenTicks: 28,
    tortureInterval: 80,
    tortureMinDamage: 4,
    tortureMaxDamage: 8,
    extremeDamageChance: 0.03,
    extremeDamageAmount: 20,
    extremeDamageLethal: true,
    healAmount: 3,
    weaknessAmplifier: 1,
    weaknessDuration: 120,
    baseDurability: 150,
    armorSlots: 2,
    armorDurabilityBonus: 30,
    armorDamageMultiplier: 1.1,
    armorSpeedMultiplier: 0.95,
    redstoneActivationDelay: 10,
    dropOnBreak: true,
    seatOffset: { x: 0, y: 0.05, z: 0 },
    sounds: {
      detect: { event: "random.wood_click", volume: 0.5, pitch: 0.9 },
      close: { event: "random.door_close", volume: 0.7, pitch: 0.7 },
      torture: { event: "mob.horse.wood", volume: 0.4, pitch: 0.6 },
      open: { event: "random.door_open", volume: 0.6, pitch: 0.8 },
      release: { event: "random.wood_click", volume: 0.5, pitch: 1.1 },
      break: { event: "random.wood_break", volume: 0.9, pitch: 0.9 },
      hit: { event: "damage.hit", volume: 0.35, pitch: 1.1 },
      reinforce: { event: "random.anvil_use", volume: 0.5, pitch: 1.3 },
    },
  },

  gravebinderCage: {
    captureRadius: 1.8,
    captureDelay: 25,
    closeDuration: 35,
    openTicks: 28,
    releasedTicks: 20,
    brokenTicks: 32,
    tortureInterval: 50,
    tortureMinDamage: 6,
    tortureMaxDamage: 14,
    extremeDamageChance: 0.08,
    extremeDamageAmount: 20,
    extremeDamageLethal: true,
    healAmount: 4,
    weaknessAmplifier: 0,
    weaknessDuration: 80,
    baseDurability: 180,
    armorSlots: 3,
    armorDurabilityBonus: 40,
    armorDamageMultiplier: 1.12,
    armorSpeedMultiplier: 0.92,
    redstoneActivationDelay: 10,
    dropOnBreak: true,
    seatOffset: { x: 0, y: 0.15, z: 0 },
    sounds: {
      detect: { event: "mob.bat.takeoff", volume: 0.4, pitch: 0.5 },
      close: { event: "random.iron_golem", volume: 0.8, pitch: 0.6 },
      torture: { event: "mob.irongolem.hit", volume: 0.5, pitch: 0.7 },
      open: { event: "random.door_open", volume: 0.7, pitch: 0.7 },
      release: { event: "random.explode", volume: 0.3, pitch: 1.3 },
      break: { event: "random.anvil_break", volume: 1.0, pitch: 0.8 },
      hit: { event: "mob.irongolem.hit", volume: 0.35, pitch: 1.0 },
      reinforce: { event: "random.anvil_use", volume: 0.6, pitch: 1.4 },
    },
  },

  regretRack: {
    captureRadius: 1.4,
    captureDelay: 30,
    closeDuration: 40,
    openTicks: 32,
    releasedTicks: 24,
    brokenTicks: 36,
    tortureInterval: 100,
    tortureMinDamage: 8,
    tortureMaxDamage: 16,
    extremeDamageChance: 0.04,
    extremeDamageAmount: 20,
    extremeDamageLethal: true,
    healAmount: 5,
    weaknessAmplifier: 0,
    weaknessDuration: 100,
    baseDurability: 300,
    armorSlots: 4,
    armorDurabilityBonus: 60,
    armorDamageMultiplier: 1.1,
    armorSpeedMultiplier: 0.95,
    redstoneActivationDelay: 15,
    dropOnBreak: true,
    seatOffset: { x: 0, y: 0.4, z: 0 },
    sounds: {
      detect: { event: "random.wood_click", volume: 0.4, pitch: 0.8 },
      close: { event: "mob.horse.leather", volume: 0.7, pitch: 0.6 },
      torture: { event: "damage.hurt", volume: 0.4, pitch: 0.6 },
      open: { event: "random.door_open", volume: 0.6, pitch: 0.7 },
      release: { event: "random.leashknot_place", volume: 0.5, pitch: 1.0 },
      break: { event: "random.wood_break", volume: 1.0, pitch: 0.85 },
      hit: { event: "damage.hit", volume: 0.4, pitch: 1.0 },
      reinforce: { event: "random.anvil_use", volume: 0.55, pitch: 1.35 },
    },
  },

  blackReliquary: {
    captureRadius: 2.0,
    captureDelay: 35,
    closeDuration: 45,
    openTicks: 38,
    releasedTicks: 28,
    brokenTicks: 40,
    tortureInterval: 40,
    tortureMinDamage: 12,
    tortureMaxDamage: 20,
    extremeDamageChance: 0.1,
    extremeDamageAmount: 20,
    extremeDamageLethal: true,
    healAmount: 8,
    weaknessAmplifier: 1,
    weaknessDuration: 60,
    baseDurability: 250,
    armorSlots: 4,
    armorDurabilityBonus: 50,
    armorDamageMultiplier: 1.2,
    armorSpeedMultiplier: 0.85,
    redstoneActivationDelay: 5,
    dropOnBreak: true,
    seatOffset: { x: 0, y: 0.15, z: 0 },
    sounds: {
      detect: { event: "mob.enderdragon.growl", volume: 0.35, pitch: 1.6 },
      close: { event: "mob.wither.spawn", volume: 0.6, pitch: 2.0 },
      torture: { event: "mob.endermen.scream", volume: 0.3, pitch: 2.0 },
      open: { event: "mob.enderdragon.hit", volume: 0.6, pitch: 1.5 },
      release: { event: "random.explode", volume: 0.4, pitch: 1.8 },
      break: { event: "random.explode", volume: 1.0, pitch: 0.9 },
      hit: { event: "mob.endermen.hit", volume: 0.4, pitch: 1.4 },
      reinforce: { event: "fire.fire", volume: 0.5, pitch: 1.8 },
    },
  },
};
