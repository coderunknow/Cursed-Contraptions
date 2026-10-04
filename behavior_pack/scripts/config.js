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
    pollIntervalTicks: 5,
    idlePollIntervalTicks: 20,
    redstonePollIntervalTicks: 10,
    interactionFeedbackCooldownTicks: 30,
    maxActiveDevices: 32,
    maxParticlesPerEvent: 8,
    chunkLoadGracePeriod: 40,
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
   * Containment. Players are held by locked movement input; mobs are frozen
   * with Slowness VII (movement multiplier reaches zero), which works on every
   * vanilla mob and needs no custom entity definition. Teleporting the victim
   * every tick is what made v0.1.2 look like the captive was stuttering, so
   * position corrections now only happen on a real escape.
   */
  containment: {
    /** Distance past which a captive rattles the frame (blocks). */
    mobDriftLimit: 1.25,
    /** Distance a mob must reach before it is pulled back. */
    mobEscapeLimit: 2.5,
    /** Players may drift a little (knockback, water) before being pulled back. */
    playerDriftLimit: 2.0,
    /** Beyond this distance the captive has genuinely escaped and is freed. */
    leashRadius: 16,
    /** Amplifier 6 = Slowness VII, which pins movement at zero. */
    mobFreezeAmplifier: 6,
    /** Effect duration; refreshed every seatRefreshTicks. */
    mobFreezeDurationTicks: 80,
    /** Minimum ticks between corrections for the same captive. */
    correctionCooldownTicks: 20,
    /** How often the hold on the captive is re-asserted. */
    seatRefreshTicks: 20,
  },

  /** "The captive is struggling" rattle overlays. */
  struggle: {
    enabled: true,
    minIntervalTicks: 120,
    maxIntervalTicks: 320,
    /** How long a strain/rattle overlay plays, in ticks. */
    strainDurationTicks: 12,
  },

  timings: {
    closedPauseTicks: 10,
    releaseAnimationTicks: 30,
    brokenAnimationTicks: 30,
  },

  particles: {
    impactEnabled: true,
    smokeCount: 4,
    sparkEnabled: true,
    sparkCount: 2,
    /** Extra burst when a device closes on a victim. */
    captureBurstCount: 6,
  },

  vignette: {
    enabled: true,
    fadeInTicks: 10,
  },

  ironMaiden: {
    captureRadius: 1.5,
    captureDelay: 20,
    closeDuration: 30,
    tortureInterval: 60,
    tortureMinDamage: 10,
    tortureMaxDamage: 18,
    extremeDamageChance: 0.05,
    extremeDamageAmount: 20,
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
  },

  cursedStocks: {
    captureRadius: 1.2,
    captureDelay: 15,
    closeDuration: 20,
    tortureInterval: 80,
    tortureMinDamage: 4,
    tortureMaxDamage: 8,
    extremeDamageChance: 0.03,
    extremeDamageAmount: 12,
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
  },

  gravebinderCage: {
    captureRadius: 1.8,
    captureDelay: 25,
    closeDuration: 35,
    tortureInterval: 50,
    tortureMinDamage: 6,
    tortureMaxDamage: 14,
    extremeDamageChance: 0.08,
    extremeDamageAmount: 16,
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
  },

  regretRack: {
    captureRadius: 1.4,
    captureDelay: 30,
    closeDuration: 40,
    tortureInterval: 100,
    tortureMinDamage: 8,
    tortureMaxDamage: 16,
    extremeDamageChance: 0.04,
    extremeDamageAmount: 18,
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
  },

  blackReliquary: {
    captureRadius: 2.0,
    captureDelay: 35,
    closeDuration: 45,
    tortureInterval: 40,
    tortureMinDamage: 12,
    tortureMaxDamage: 20,
    extremeDamageChance: 0.1,
    extremeDamageAmount: 24,
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
  },
};
