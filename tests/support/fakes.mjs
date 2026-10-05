/**
 * Cursed Contraptions — shared device test fixtures
 *
 * FakeEntity/FakeDimension implement just enough of the stable @minecraft/server
 * surface for gameplay tests, and record the calls the scripts make so tests can
 * assert on them (damage, effects, sounds, action-bar lines, anchoring).
 */

import assert from "node:assert/strict";
import { CONFIG } from "../../behavior_pack/scripts/config.js";
import { TortureDevice } from "../../behavior_pack/scripts/devices/device-base.js";
import { advanceTicks, resetSystem, world } from "../mocks/minecraft-server.mjs";

export class FakeDimension {
  id = "minecraft:overworld";
  entities = [];
  droppedItems = [];
  particles = [];
  sounds = [];

  getEntities(options = {}) {
    return this.entities.filter((entity) => {
      if (!entity.isValid() || entity.dimension !== this) return false;
      if (options.type && entity.typeId !== options.type) return false;
      if (options.excludeTypes?.includes(entity.typeId)) return false;
      if (options.families && !options.families.every((family) => entity.families.has(family))) return false;
      if (options.tags && !options.tags.every((tag) => entity.hasTag(tag))) return false;
      if (options.location && Number.isFinite(options.maxDistance)) {
        const dx = entity.location.x - options.location.x;
        const dy = entity.location.y - options.location.y;
        const dz = entity.location.z - options.location.z;
        if (dx * dx + dy * dy + dz * dz > options.maxDistance * options.maxDistance) return false;
      }
      return true;
    });
  }

  getBlock() { return { isAir: true, isLiquid: false }; }
  spawnItem(item, location) { this.droppedItems.push({ item, location }); }
  spawnParticle(id, location) { this.particles.push({ id, location }); }
  playSound(id, location, options) { this.sounds.push({ id, location, options }); }

  add(entity) {
    this.entities.push(entity);
    world.registerEntity(entity);
    return entity;
  }
}

export class FakeContainer {
  constructor(size = 9) { this.slots = new Array(size); }
  getItem(slot) { return this.slots[slot]; }
  setItem(slot, item) { this.slots[slot] = item; }
  addItem(item) {
    const slot = this.slots.findIndex((current) => !current);
    if (slot < 0) return item;
    this.slots[slot] = item;
    return undefined;
  }
}

export let nextEntityId = 1;
export class FakeEntity {
  constructor(typeId, dimension, location, options = {}) {
    this.id = options.id || `entity-${nextEntityId++}`;
    this.typeId = typeId;
    this.dimension = dimension;
    this.location = { ...location };
    this.valid = true;
    this.tags = new Set(options.tags || []);
    this.families = new Set(options.families || (
      typeId === "minecraft:player" ? ["player"]
        : typeId.startsWith("minecraft:") ? ["mob"]
          : ["cc_device"]
    ));
    this.dynamicProperties = new Map();
    this.properties = new Map([
      ["cc:state", "idle"],
      ["cc:durability", options.durability || 200],
      ["cc:armor_count", 0],
    ]);
    this._health = options.health || 20;
    this._maxHealth = options.maxHealth || 20;
    this.healthComponent = {
      get currentValue() { return this.owner._health; },
      get effectiveMax() { return this.owner._maxHealth; },
      setCurrentValue: (value) => {
        this._health = Math.min(this._maxHealth, Math.max(0, value));
        return true;
      },
      owner: this,
    };
    this.gameMode = options.gameMode || "survival";
    this.isSneaking = options.isSneaking ?? false;
    this.messages = [];
    this.actionBars = [];
    this.onScreenDisplay = {
      setActionBar: (message) => { this.actionBars.push(String(message)); },
    };
    this.effects = new Map();
    this.velocity = { ...(options.velocity || { x: 0, y: 0, z: 0 }) };
    this.impulses = [];
    this.velocityClears = 0;
    this.teleports = [];
    this.teleportFails = Boolean(options.teleportFails);
    this.inputPermissions = {
      movement: options.movementEnabled ?? true,
      isPermissionCategoryEnabled: () => this.inputPermissions.movement,
      setPermissionCategory: (_, enabled) => { this.inputPermissions.movement = enabled; },
    };
    this.inventory = options.inventory || new FakeContainer();
    this.selectedSlotIndex = options.selectedSlotIndex ?? 0;
    this.damageTaken = [];
  }

  isValid() { return this.valid; }
  getComponent(typeId) {
    if (typeId === "minecraft:health" || typeId === "health") return this.healthComponent;
    if (typeId === "minecraft:inventory" || typeId === "inventory") return { container: this.inventory };
    return undefined;
  }
  getGameMode() { return this.gameMode; }
  getDynamicProperty(id) { return this.dynamicProperties.get(id); }
  setDynamicProperty(id, value) {
    if (value === undefined) this.dynamicProperties.delete(id);
    else this.dynamicProperties.set(id, value);
  }
  getProperty(id) { return this.properties.get(id); }
  setProperty(id, value) { this.properties.set(id, value); }
  addTag(tag) { this.tags.add(tag); }
  removeTag(tag) { this.tags.delete(tag); }
  hasTag(tag) { return this.tags.has(tag); }
  addEffect(id, duration, options) { this.effects.set(id, { duration, ...options }); }
  removeEffect(id) { this.effects.delete(id); }
  teleport(location, options = {}) {
    if (this.teleportFails) return false;
    this.location = { ...location };
    this.teleports.push({ location: { ...location }, options });
    if (options.dimension) this.dimension = options.dimension;
    return true;
  }
  getVelocity() { return { ...this.velocity }; }
  clearVelocity() { this.velocity = { x: 0, y: 0, z: 0 }; this.velocityClears++; }
  applyImpulse(vector) { this.impulses.push({ ...vector }); }
  applyDamage(amount, options) {
    this.damageTaken.push({ amount, options });
    this._health = Math.max(0, this._health - amount);
    return true;
  }
  sendMessage(message) { this.messages.push(message); }
  kill() { this.valid = false; }
  remove() { this.valid = false; }
}

export function setup() {
  resetSystem();
  nextEntityId = 1;
  const dimension = new FakeDimension();
  const deviceEntity = dimension.add(new FakeEntity("cc:iron_maiden", dimension, {
    x: 0.5, y: 64, z: 0.5,
  }, { health: 1000, maxHealth: 1000 }));
  const device = new TortureDevice("cc:iron_maiden", CONFIG.ironMaiden, deviceEntity);
  return { dimension, device, deviceEntity };
}

export function captureForTorture(dimension, device, options = {}, typeId = "minecraft:player") {
  const victim = dimension.add(new FakeEntity(typeId, dimension, {
    x: 0.5, y: 64, z: 0.5,
  }, options));
  device.tick(true);
  advanceTicks(CONFIG.ironMaiden.captureDelay
    + CONFIG.ironMaiden.closeDuration
    + CONFIG.timings.closedPauseTicks);
  assert.equal(device.stateMachine.state, "torturing");
  return victim;
}

export function withRandomSequence(values, callback) {
  const originalRandom = Math.random;
  let index = 0;
  Math.random = () => values[index++] ?? 0.5;
  try {
    return callback();
  } finally {
    Math.random = originalRandom;
  }
}
