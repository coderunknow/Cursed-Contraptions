import assert from "node:assert/strict";
import test from "node:test";
import { CONFIG } from "../behavior_pack/scripts/config.js";
import { TortureDevice } from "../behavior_pack/scripts/devices/device-base.js";
import { advanceTicks, resetSystem } from "./mocks/minecraft-server.mjs";
import {
  FakeContainer,
  FakeDimension,
  FakeEntity,
  captureForTorture,
  setup,
  withRandomSequence,
} from "./support/fakes.mjs";

test("capture reserves one target, disables movement, and rescue restores it", () => {
  const { dimension, device } = setup();
  const victim = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 0.5, y: 64, z: 0.5,
  }));

  device.tick(true);
  assert.equal(device.stateMachine.state, "detecting");
  assert.equal(victim.hasTag("cc:capture_reserved"), true);

  advanceTicks(CONFIG.ironMaiden.captureDelay);
  assert.equal(device.stateMachine.state, "capturing");
  assert.equal(device.victimId, victim.id);
  assert.equal(victim.hasTag("cc:trapped"), true);
  assert.equal(victim.inputPermissions.movement, false);
  assert.equal(victim.getDynamicProperty("cc:movement_was_enabled"), true);
  assert.equal(device.onInteract(victim, null), false);
  assert.match(victim.messages.at(-1), /cannot free yourself/);
  assert.equal(device.stateMachine.state, "capturing");

  assert.equal(device.release(), true);
  assert.equal(device.stateMachine.state, "opening");
  advanceTicks(CONFIG.timings.releaseAnimationTicks);
  assert.equal(device.stateMachine.state, "released");
  assert.equal(victim.hasTag("cc:trapped"), false);
  assert.equal(victim.inputPermissions.movement, true);
  assert.equal(victim.getDynamicProperty("cc:movement_was_enabled"), undefined);
  assert.notDeepEqual(victim.location, { x: 0.5, y: 64, z: 0.5 });

  advanceTicks(CONFIG.timings.releaseAnimationTicks);
  assert.equal(device.stateMachine.state, "idle");
  assert.equal(dimension.droppedItems.length, 0);
});

test("mob-family entities can be captured with an independent family query", () => {
  const { dimension, device } = setup();
  const mob = dimension.add(new FakeEntity("minecraft:zombie", dimension, {
    x: 0.5, y: 64, z: 0.5,
  }));

  device.tick(true);
  assert.equal(device.stateMachine.state, "detecting");
  advanceTicks(CONFIG.ironMaiden.captureDelay);
  assert.equal(device.victimId, mob.id);
  assert.equal(mob.hasTag("cc:trapped"), true);
  assert.equal(device.stateMachine.state, "capturing");
});

test("an escaped or cross-dimension captive is unlocked without being dragged back", () => {
  const { dimension, device } = setup();
  const victim = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 0.5, y: 64, z: 0.5,
  }));
  device.tick(true);
  advanceTicks(CONFIG.ironMaiden.captureDelay);
  assert.equal(victim.inputPermissions.movement, false);

  const otherDimension = new FakeDimension();
  otherDimension.id = "minecraft:nether";
  const escapedLocation = { x: 100, y: 72, z: 3 };
  victim.dimension = otherDimension;
  victim.location = { ...escapedLocation };
  device.tick(true);
  assert.equal(device.stateMachine.state, "opening");
  advanceTicks(CONFIG.timings.releaseAnimationTicks);
  assert.equal(victim.inputPermissions.movement, true);
  assert.equal(victim.hasTag("cc:trapped"), false);
  assert.deepEqual(victim.location, escapedLocation);
  assert.equal(victim.dimension.id, "minecraft:nether");
});

test("release clearance permits water but never selects lava", () => {
  const { device } = setup();
  assert.equal(device._isPassable({ isAir: true, isLiquid: false, typeId: "minecraft:air" }), true);
  assert.equal(device._isPassable({ isAir: false, isLiquid: true, typeId: "minecraft:water" }), true);
  assert.equal(device._isPassable({ isAir: false, isLiquid: true, typeId: "minecraft:lava" }), false);
});

test("simultaneous devices cannot reserve the same victim; moving away cancels capture", () => {
  const { dimension, device: first } = setup();
  const secondEntity = dimension.add(new FakeEntity("cc:iron_maiden", dimension, {
    x: 0.5, y: 64, z: 0.5,
  }, { health: 1000, maxHealth: 1000 }));
  const second = new TortureDevice("cc:iron_maiden", CONFIG.ironMaiden, secondEntity);
  const victim = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 0.5, y: 64, z: 0.5,
  }));

  first.tick(true);
  second.tick(true);
  assert.equal(first.stateMachine.state, "detecting");
  assert.equal(second.stateMachine.state, "idle");

  victim.location.x = 3;
  first.tick(true);
  assert.equal(first.stateMachine.state, "idle");
  assert.equal(victim.hasTag("cc:capture_reserved"), false);
  assert.equal(victim.hasTag("cc:trapped"), false);
});

test("a torture cycle heals before damage and never kills a low-health captive", () => {
  const { dimension, device } = setup();
  const victim = captureForTorture(dimension, device, { health: 2, maxHealth: 20 });

  advanceTicks(CONFIG.ironMaiden.tortureInterval);
  assert.equal(victim.damageTaken.length, 1);
  assert.equal(victim.damageTaken[0].amount, 7);
  assert.equal(victim.healthComponent.currentValue, 1);
  assert.equal(device.durability, CONFIG.ironMaiden.baseDurability - 1);
});

test("torture damage includes both configured range endpoints", () => {
  for (const [damageRoll, expectedDamage] of [
    [0, CONFIG.ironMaiden.tortureMinDamage],
    [1, CONFIG.ironMaiden.tortureMaxDamage],
  ]) {
    const { dimension, device } = setup();
    const victim = captureForTorture(dimension, device, { health: 100, maxHealth: 100 });

    withRandomSequence([0.5, damageRoll], () => {
      advanceTicks(CONFIG.ironMaiden.tortureInterval);
    });
    assert.equal(victim.damageTaken.length, 1);
    assert.equal(victim.damageTaken[0].amount, expectedDamage);
  }
});

test("armor is consumed once and its configured durability bonus is applied", () => {
  const { dimension, device } = setup();
  const inventory = new FakeContainer();
  inventory.setItem(0, { typeId: "minecraft:iron_helmet", amount: 1, setAmount() {} });
  const player = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 8, y: 64, z: 8,
  }, { inventory }));

  assert.equal(device.onInteract(player, inventory.getItem(0)), true);
  assert.equal(inventory.getItem(0), undefined);
  assert.equal(device.armorCount, 1);
  assert.equal(device.maxDurability, CONFIG.ironMaiden.baseDurability + CONFIG.ironMaiden.armorDurabilityBonus);
  assert.equal(device.durability, device.maxDurability);
});

test("breaking is idempotent and drops exactly one device item", () => {
  const { dimension, device, deviceEntity } = setup();
  assert.equal(device.takeDamage(device.durability), true);
  assert.equal(device.stateMachine.state, "broken");
  assert.equal(dimension.droppedItems.length, 1);
  assert.equal(dimension.droppedItems[0].item.typeId, "cc:item_iron_maiden");
  assert.equal(device.break(), false);
  assert.equal(device.takeDamage(100), false);
  assert.equal(dimension.droppedItems.length, 1);

  advanceTicks(CONFIG.timings.brokenAnimationTicks);
  assert.equal(deviceEntity.isValid(), false);
  assert.equal(dimension.droppedItems.length, 1);
});

test("an interrupted capture rolls back its reservation, captive lock, and animation", () => {
  const { dimension, deviceEntity } = setup();
  const victim = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 0.5, y: 64, z: 0.5,
  }));
  victim.addTag("cc:capture_reserved");
  victim.addTag("cc:trapped");
  victim.inputPermissions.movement = false;
  victim.setDynamicProperty("cc:movement_was_enabled", true);
  deviceEntity.addTag("cc:anim_detecting");
  deviceEntity.setDynamicProperty("cc:device_state", "detecting");
  deviceEntity.setDynamicProperty("cc:device_pending_victim_id", victim.id);
  deviceEntity.setDynamicProperty("cc:device_victim_id", victim.id);

  const restored = new TortureDevice("cc:iron_maiden", CONFIG.ironMaiden, deviceEntity);
  assert.equal(restored.stateMachine.state, "idle");
  assert.equal(victim.hasTag("cc:capture_reserved"), false);
  assert.equal(victim.hasTag("cc:trapped"), false);
  assert.equal(victim.inputPermissions.movement, true);
  assert.equal(victim.getDynamicProperty("cc:movement_was_enabled"), undefined);
  assert.equal(deviceEntity.getDynamicProperty("cc:device_victim_id"), undefined);
  assert.equal(deviceEntity.hasTag("cc:anim_detecting"), false);
  assert.equal(deviceEntity.hasTag("cc:anim_idle"), true);
});

test("recovery clears a saved captive link when the target is no longer trapped", () => {
  const { dimension, deviceEntity } = setup();
  const victim = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 0.5, y: 64, z: 0.5,
  }));
  victim.inputPermissions.movement = false;
  victim.setDynamicProperty("cc:movement_was_enabled", true);
  deviceEntity.setDynamicProperty("cc:device_state", "torturing");
  deviceEntity.setDynamicProperty("cc:device_victim_id", victim.id);

  const restored = new TortureDevice("cc:iron_maiden", CONFIG.ironMaiden, deviceEntity);
  assert.equal(restored.stateMachine.state, "idle");
  assert.equal(restored.victimId, null);
  assert.equal(victim.inputPermissions.movement, true);
  assert.equal(victim.getDynamicProperty("cc:movement_was_enabled"), undefined);
  assert.equal(deviceEntity.getDynamicProperty("cc:device_victim_id"), undefined);
});

test("an occupied device restores its saved state without scanning the whole world", () => {
  const { dimension, deviceEntity } = setup();
  const victim = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 0.5, y: 64, z: 0.5,
  }, { id: "persistent-player", movementEnabled: true }));
  victim.addTag("cc:trapped");
  victim.setDynamicProperty("cc:movement_was_enabled", true);
  deviceEntity.setDynamicProperty("cc:device_state", "torturing");
  deviceEntity.setDynamicProperty("cc:device_victim_id", victim.id);
  deviceEntity.setDynamicProperty("cc:device_durability", 100);

  const restored = new TortureDevice("cc:iron_maiden", CONFIG.ironMaiden, deviceEntity);
  assert.equal(restored.stateMachine.state, "torturing");
  assert.equal(restored.victimId, victim.id);
  assert.equal(victim.inputPermissions.movement, false);
  assert.equal(restored.durability, 100);
});
