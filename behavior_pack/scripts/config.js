/**
 * Cursed Contraptions — Centralized Configuration
 *
 * Gameplay values live here so every device follows the same, auditable rules.
 * Timings are in ticks (20 ticks = 1 second).
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
   * Containment. A captive is held *inside* its device:
   *
   * - players keep their movement input locked and are nudged back with an
   *   impulse (knockback, water and pistons can still move them a little),
   * - mobs have their velocity cleared and are nudged back to the seat every
   *   tick, so vanilla AI cannot shove them out (v0.1.3 only reacted once the
   *   mob was 2.5 blocks away, which is the reported "pushed out but still
   *   taking damage" bug),
   * - damage is gated on real containment, so a captive can never be hurt
   *   while it is outside its device.
   */
  containment: {
    /** Effects are refreshed this often; latency-tolerant, not every tick. */
    seatRefreshTicks: 20,
    /** Distance a wobbling captive still counts as seated (per device). */
    defaultRadius: 1.6,
    /** Distance to the seat before a correction teleport is allowed. */
    snapDistance: 1.9,
    /** Minimum ticks between correction teleports for the same captive. */
    correctionCooldownTicks: 10,
    /** Speed cap applied by the anchoring impulse, in blocks per tick. */
    maxAnchorSpeed: 0.24,
    /** Beyond this distance the captive has genuinely escaped and is freed. */
    leashRadius: 18,
    /** Failed reseats before the captive is released instead of stuck. */
    maxFailedReseatCycles: 3,
    /** Amplifier 6 = Slowness VII, which pins mob movement at zero. */
    mobFreezeAmplifier: 6,
    mobFreezeDurationTicks: 80,
  },

  /** "The captive is struggling" rattle overlays. */
  struggle: {
    enabled: true,
    minIntervalTicks: 120,
    maxIntervalTicks: 320,
    strainDurationTicks: 12,
  },

  /**
   * Soul charge. Every strike a contained captive survives winds the device up
   * one step: the work interval shortens, the damage grows, and a full meter
   * vents as a surge that harvests a soul. The client-synced ``cc:charge``
   * property switches the animation controller to the hotter torture loop.
   */
  charge: {
    enabled: true,
    max: 4,
    /** Extra damage per charge step (0.3 = +30% at full charge). */
    damageBonusPerStep: 0.3,
    /** Faster cycles per charge step (0.1 = 10% shorter at full charge). */
    speedBonusPerStep: 0.1,
    /** The venting surge hits this much harder than a normal cycle. */
    surgeMultiplier: 1.5,
    /** Charge decays this fast (in ticks per step) while the device is empty. */
    decayIntervalTicks: 100,
  },

  /** Souls harvested by a device become soul shards when it is destroyed. */
  souls: {
    itemId: "cc:soul_shard",
    perShard: 2,
    maxShards: 8,
    /** Immunity granted by spending a soul shard (5 minutes). */
    immunityTicks: 6000,
  },

  /**
   * Field repair: any device that is not full repairs by holding a matching
   * material. The value is a fraction of the device's maximum durability.
   */
  repair: {
    enabled: true,
    materials: {
      metal: {
        "minecraft:iron_ingot": 0.2,
        "minecraft:iron_bars": 0.15,
        "minecraft:chain": 0.15,
        "minecraft:iron_block": 0.6,
      },
      timber: {
        "minecraft:stick": 0.08,
        "minecraft:oak_planks": 0.2,
        "minecraft:birch_planks": 0.2,
        "minecraft:spruce_planks": 0.2,
        "minecraft:jungle_planks": 0.2,
        "minecraft:acacia_planks": 0.2,
        "minecraft:dark_oak_planks": 0.2,
        "minecraft:mangrove_planks": 0.2,
        "minecraft:cherry_planks": 0.2,
        "minecraft:bamboo_planks": 0.2,
      },
      bone: {
        "minecraft:bone": 0.15,
        "minecraft:bone_block": 0.5,
      },
      soul: {
        "minecraft:obsidian": 0.3,
        "minecraft:crying_obsidian": 0.4,
        "minecraft:netherite_scrap": 0.5,
      },
    },
  },

  /** Vanilla sound cues. Profiles differ per device material. */
  sounds: {
    enabled: true,
    profiles: {
      metal: { hit: "random.anvil_use", slam: "random.anvil_land", pitch: 1.0 },
      timber: { hit: "dig.wood", slam: "dig.wood", pitch: 1.0 },
      damp: { hit: "dig.wood", slam: "random.anvil_land", pitch: 0.85 },
      soul: { hit: "random.fizz", slam: "random.anvil_land", pitch: 0.8 },
    },
    latch: "random.click",
    release: "random.pop",
    reinforce: "random.anvil_use",
    repair: "random.anvil_use",
    soul: "random.orb",
    surge: "random.fizz",
    break: "random.anvil_land",
    capture: "random.orb",
  },

  /** Action-bar status for captives and (once) for rescuers. */
  hud: {
    enabled: true,
    intervalTicks: 60,
  },

  timings: {
    closedPauseTicks: 10,
    releaseAnimationTicks: 30,
    brokenAnimationTicks: 30,
    burstAnimationTicks: 9,
  },

  particles: {
    impactEnabled: true,
    smokeCount: 4,
    sparkEnabled: true,
    sparkCount: 2,
    /** Extra burst when a device closes on a victim. */
    captureBurstCount: 6,
    /** Self-damage feedback when the frame is struck. */
    hitBounceCount: 3,
  },

  vignette: {
    enabled: true,
    fadeInTicks: 10,
  },

  /**
   * Per-device balance. ``containmentRadius`` gates both the seat and the
   * damage cycle, so it is the single number that defines "inside the device".
   */
  ironMaiden: {
    captureRadius: 1.5,
    containmentRadius: 1.55,
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
    repairMaterial: "metal",
    soundProfile: "metal",
    soundPitch: 1.0,
    dropOnBreak: true,
  },

  cursedStocks: {
    captureRadius: 1.2,
    containmentRadius: 1.35,
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
    repairMaterial: "timber",
    soundProfile: "timber",
    soundPitch: 1.1,
    dropOnBreak: true,
  },

  gravebinderCage: {
    captureRadius: 1.8,
    containmentRadius: 1.7,
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
    repairMaterial: "metal",
    soundProfile: "metal",
    soundPitch: 1.15,
    dropOnBreak: true,
  },

  regretRack: {
    captureRadius: 1.4,
    containmentRadius: 1.5,
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
    repairMaterial: "timber",
    soundProfile: "damp",
    soundPitch: 0.9,
    dropOnBreak: true,
  },

  blackReliquary: {
    captureRadius: 2.0,
    containmentRadius: 1.85,
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
    repairMaterial: "soul",
    soundProfile: "soul",
    soundPitch: 0.7,
    dropOnBreak: true,
  },
};
