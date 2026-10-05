import assert from "node:assert/strict";
import test from "node:test";
import { CONFIG } from "../behavior_pack/scripts/config.js";
import { deviceManager } from "../behavior_pack/scripts/devices/device-manager.js";
import {
  advanceTicks,
  resetSystem,
  world,
} from "./mocks/minecraft-server.mjs";

// Drives the REAL entry point's subscribed handlers (placement, tick loop,
// entityHurt, entityDie) instead of calling device internals directly.
import "../behavior_pack/scripts/main.js";

class FakeDimension {
  id = "minecraft:overworld";
  entities = [];
  droppedItems = [];
  blocks = new Map();

  static key(location) {
    return `${Math.floor(location.x)},${Math.floor(location.y)},${Math.floor(location.z)}`;
  }
  getBlock(location) {
    const typeId = this.blocks.get(FakeDimension.key(location));
    return typeId ? { typeId, isAir: typeId === "minecraft:air", getRedstonePower: () => 0 } : undefined;
  }
  setBlockType(location, typeId) {
    this.blocks.set(FakeDimension.key(location), typeId);
  }
  spawnEntity(typeId, location) {
    return this.add(new FakeEntity(typeId, this, location));
  }
  add(entity) {
    this.entities.push(entity);
    world.registerEntity(entity);
    return entity;
  }
  spawnItem(item, location) { this.droppedItems.push({ item, location }); }
  spawnParticle() {}
  playSound() {}
  getEntities(options = {}) {
    return this.entities.filter((entity) => {
      if (!entity.isValid() || entity.dimension !== this) return false;
      if (options.type && entity.typeId !== options.type) return false;
      if (options.families && !options.families.every((family) => entity.families.has(family))) return false;
      if (options.excludeFamilies && options.excludeFamilies.some((family) => entity.families.has(family))) return false;
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
}

let nextId = 1;
class FakeEntity {
  constructor(typeId, dimension, location, options = {}) {
    this.id = options.id || `entity-${nextId++}`;
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
    this.gameMode = options.gameMode || "survival";
    this.messages = [];
    this.healthComponent = {
      get currentValue() { return this.owner._health; },
      get effectiveMax() { return this.owner._maxHealth; },
      setCurrentValue: (value) => {
        this._health = Math.min(this._maxHealth, Math.max(0, value));
        return true;
      },
      owner: this,
    };
    this.inputPermissions = {
      movement: true,
      isPermissionCategoryEnabled: () => this.inputPermissions.movement,
      setPermissionCategory: (_, enabled) => { this.inputPermissions.movement = enabled; },
    };
    this.selectedSlotIndex = 0;
  }
  isValid() { return this.valid; }
  getComponent(typeId) {
    if (typeId === "minecraft:health") return this.healthComponent;
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
  addEffect() {}
  teleport(location, options = {}) {
    this.location = { ...location };
    if (options.dimension) this.dimension = options.dimension;
  }
  applyDamage(amount) { this._health = Math.max(0, this._health - amount); return true; }
  sendMessage(message) { this.messages.push(message); }
  triggerEvent() {}
  playSound() {}
  kill() { this.valid = false; }
  remove() { this.valid = false; }
}

test.beforeEach(() => {
  resetSystem();
  nextId = 1;
});

test.after(() => {
  deviceManager.devices.clear();
});

test("full in-world flow through the real entry point: place → capture → torture → break → drop → unregister", () => {
  // The entry point's deferred init task was cleared by beforeEach; reproduce
  // its effect (starting the manager loop) the way world load would.
  deviceManager.start();

  const dimension = new FakeDimension();
  world.registerDimension(dimension);
  const blockLocation = { x: 0, y: 64, z: 0 };
  dimension.setBlockType(blockLocation, "cc:iron_maiden_block");
  const placer = dimension.add(new FakeEntity("minecraft:player", dimension, { x: 2.5, y: 64, z: 2.5 }));

  // Placement event → deferred spawn → registration, anchor block removed.
  world.afterEvents.playerPlaceBlock.fire({
    player: placer,
    block: { typeId: "cc:iron_maiden_block", location: blockLocation, dimension },
  });
  advanceTicks(2);
  assert.equal(dimension.getBlock(blockLocation)?.typeId, "minecraft:air");
  assert.equal(deviceManager.totalCount, 1);
  const deviceEntity = [...dimension.entities].find((entity) => entity.typeId === "cc:iron_maiden");
  assert.ok(deviceEntity);

  // Idle polling detects and captures the nearby survival player.
  const victim = dimension.add(new FakeEntity("minecraft:player", dimension, { x: 0.5, y: 64, z: 0.5 }));
  advanceTicks(CONFIG.performance.idlePollIntervalTicks + CONFIG.ironMaiden.tortureInterval);
  const [device] = deviceManager.devices.values();
  assert.equal(device.stateMachine.state, "torturing");
  assert.equal(victim.hasTag("cc:trapped"), true);
  assert.equal(victim.inputPermissions.movement, false);

  // Lethal damage through the entityHurt event breaks the device, frees the
  // victim, and drops exactly one item.
  world.afterEvents.entityHurt.fire({ hurtEntity: deviceEntity, damage: 9999, damageSource: {} });
  assert.equal(device.stateMachine.state, "broken");
  assert.equal(victim.hasTag("cc:trapped"), false);
  assert.equal(victim.inputPermissions.movement, true);
  assert.equal(dimension.droppedItems.length, 1);
  assert.equal(dimension.droppedItems[0].item.typeId, "cc:item_iron_maiden");

  // The broken entity is removed after its animation, then entityDie
  // unregisters it without a second drop.
  advanceTicks(CONFIG.timings.brokenAnimationTicks + 2);
  assert.equal(deviceEntity.isValid(), false);
  world.afterEvents.entityDie.fire({ deadEntity: deviceEntity });
  assert.equal(deviceManager.totalCount, 0);
  assert.equal(dimension.droppedItems.length, 1);

  // The interval loop keeps running cleanly afterwards.
  advanceTicks(200);
  assert.equal(deviceManager.totalCount, 0);
});
