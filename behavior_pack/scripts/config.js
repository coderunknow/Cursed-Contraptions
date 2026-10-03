/**
 * Cursed Contraptions — Centralized Configuration
 * 
 * All tunable values for the mod live here. Device-specific configs
 * extend these defaults. Never hard-code magic numbers in device logic.
 */

export const CONFIG = {
  // ── Namespace ──
  namespace: "cc",

  // ── Debug ──
  debug: {
    enabled: false,          // Set to true for development logging
    logLevel: "info",        // "info" | "warn" | "error"
    chatDebug: false,        // Broadcast debug info to chat (dev only)
  },

  // ── Performance ──
  performance: {
    pollIntervalTicks: 20,   // How often active devices tick (1 second)
    idlePollIntervalTicks: 100, // How often idle devices check for activity (5 seconds)
    maxActiveDevices: 32,    // Max devices processing simultaneously
    entityScanRadius: 8,     // Max radius for entity detection around a device
    maxParticlesPerEvent: 8, // Cap particles per damage event
    failsafeMaxTimers: 64,   // Max concurrent runTimeout/runInterval handles
    chunkLoadGracePeriod: 40, // Ticks to wait after chunk load before processing
  },

  // ── Iron Maiden ──
  ironMaiden: {
    captureRadius: 1.5,        // Blocks within which a player is detected
    captureDelay: 20,          // Ticks before capture animation completes
    closeDuration: 30,         // Ticks for door-close animation
    tortureInterval: 60,      // Ticks between damage cycles (3 seconds)
    tortureMinDamage: 10,      // Min hearts × 2 = 10 damage points (5 hearts)
    tortureMaxDamage: 18,      // Max hearts × 2 = 18 damage points (9 hearts)
    extremeDamageChance: 0.05, // 5% chance
    extremeDamageAmount: 20,   // 10 hearts
    healAmount: 6,             // Regen per cycle to sustain long torture
    healDuration: 60,          // Ticks the regen effect lasts
    healAmplifier: 1,          // Regen level
    weaknessAmplifier: 0,      // Weakness level applied to victim
    weaknessDuration: 100,     // Ticks
    baseDurability: 200,       // Total durability points
    armorSlots: 4,             // Number of armor reinforcement slots
    armorDurabilityBonus: 50,  // +durability per armor piece
    armorDamageMultiplier: 1.15, // +15% damage per armor piece
    armorSpeedMultiplier: 0.90,  // -10% cycle time per armor piece
    redstoneActivationDelay: 10, // Ticks delay after redstone signal
    dropOnBreak: true,         // Whether broken device drops the item
    naturalSpawnDurability: 80, // Lower durability for naturally spawned
  },

  // ── Cursed Stocks ──
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
    healDuration: 60,
    healAmplifier: 0,
    weaknessAmplifier: 1,
    weaknessDuration: 120,
    baseDurability: 150,
    armorSlots: 2,
    armorDurabilityBonus: 30,
    armorDamageMultiplier: 1.10,
    armorSpeedMultiplier: 0.95,
    redstoneActivationDelay: 10,
    dropOnBreak: true,
    naturalSpawnDurability: 60,
  },

  // ── Gravebinder Cage ──
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
    healDuration: 80,
    healAmplifier: 1,
    weaknessAmplifier: 0,
    weaknessDuration: 80,
    baseDurability: 180,
    armorSlots: 3,
    armorDurabilityBonus: 40,
    armorDamageMultiplier: 1.12,
    armorSpeedMultiplier: 0.92,
    redstoneActivationDelay: 10,
    dropOnBreak: true,
    naturalSpawnDurability: 70,
  },

  // ── The Regret Rack ──
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
    healDuration: 100,
    healAmplifier: 1,
    weaknessAmplifier: 0,
    weaknessDuration: 100,
    baseDurability: 300,
    armorSlots: 4,
    armorDurabilityBonus: 60,
    armorDamageMultiplier: 1.10,
    armorSpeedMultiplier: 0.95,
    redstoneActivationDelay: 15,
    dropOnBreak: true,
    naturalSpawnDurability: 120,
  },

  // ── The Black Reliquary ──
  blackReliquary: {
    captureRadius: 2.0,
    captureDelay: 35,
    closeDuration: 45,
    tortureInterval: 40,
    tortureMinDamage: 12,
    tortureMaxDamage: 20,
    extremeDamageChance: 0.10,
    extremeDamageAmount: 24,
    healAmount: 8,
    healDuration: 60,
    healAmplifier: 2,
    weaknessAmplifier: 1,
    weaknessDuration: 60,
    baseDurability: 250,
    armorSlots: 4,
    armorDurabilityBonus: 50,
    armorDamageMultiplier: 1.20,
    armorSpeedMultiplier: 0.85,
    redstoneActivationDelay: 5,
    dropOnBreak: true,
    naturalSpawnDurability: 100,
  },

  // ── Natural Generation ──
  worldgen: {
    enabled: true,
    structureRarity: 0.002,   // Very rare — per-chunk chance
    minDepth: 10,             // Minimum Y depth for underground spawns
    maxDepth: 50,             // Maximum Y depth
  },

  // ── Vignette / Visual Effects ──
  vignette: {
    enabled: true,
    intensity: 0.6,           // Darkness overlay strength
    fadeInTicks: 10,
    fadeOutTicks: 20,
  },

  // ── Particles ──
  particles: {
    bloodEnabled: true,
    bloodCount: 4,             // Per damage event
    sparkEnabled: true,
    sparkCount: 2,
    ambientEnabled: true,
    ambientInterval: 40,       // Ticks between ambient particles
  },
};
