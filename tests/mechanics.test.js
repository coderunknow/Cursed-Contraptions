/**
 * Cursed Contraptions — v0.1.4 mechanic tests
 *
 * Covers the containment contract (a captive outside its device is never
 * damaged), soul-charge escalation, field repair, soul shards, immunity
 * warding, rescue, and the polish layer (sounds + action-bar HUD).
 */

import assert from "node:assert/strict";
import test from "node:test";
import { CONFIG } from "../behavior_pack/scripts/config.js";
import { TortureDevice } from "../behavior_pack/scripts/devices/device-base.js";
import { advanceTicks, resetSystem } from "./mocks/minecraft-server.mjs";
import {
  FakeContainer,
  FakeEntity,
  captureForTorture,
  setup,
  withRandomSequence,
} from "./support/fakes.mjs";

const TORTURE_INTERVAL = CONFIG.ironMaiden.tortureInterval;
/** Advance from a fresh torture cycle to the tick a damage cycle lands on. */
const toNextDamage = () => advanceTicks(TORTURE_INTERVAL);

test("a shoved captive is pulled back inside and is never damaged while outside", () => {
  const { dimension, device, deviceEntity } = setup();
  const mob = captureForTorture(dimension, device, { health: 200, maxHealth: 200 }, "minecraft:zombie");
  assert.equal(mob.getComponent("minecraft:health").currentValue, 200);

  // Simulate a shove: the mob ends up 11.5 blocks away with knockback velocity.
  mob.velocity = { x: 0.9, y: 0.4, z: 0 };
  mob.location = { x: 12, y: 64, z: 0.5 };

  device.tick(true);

  // The hold clears mob velocity and teleports the captive back inside.
  assert.ok(mob.velocityClears >= 1, "the anchor loop clears accumulated velocity");
  assert.ok(mob.teleports.length >= 1, "the captive is snapped back to the seat");
  const offset = Math.hypot(mob.location.x - 0.5, mob.location.z - 0.5);
  assert.ok(
    offset <= CONFIG.ironMaiden.containmentRadius,
    `captive is inside the device again (offset ${offset.toFixed(2)})`,
  );

  // Damage that lands after the reseat is applied, because the captive is back.
  advanceTicks(TORTURE_INTERVAL);
  assert.equal(mob.damageTaken.length, 1);
  assert.equal(device.stateMachine.state, "torturing");
  assert.equal(deviceEntity.hasTag("cc:anim_torturing"), true);
});

test("a captive that cannot be reseated is freed instead of being damaged outside", () => {
  const { dimension, device } = setup();
  const mob = captureForTorture(dimension, device, { health: 200, maxHealth: 200 }, "minecraft:zombie");
  mob.teleportFails = true;
  mob.location = { x: 12, y: 64, z: 0.5 };

  // Every containment attempt fails, so no damage may ever be dealt.
  for (let i = 0; i < CONFIG.containment.maxFailedReseatCycles + 1; i++) device.tick(true);

  assert.equal(mob.damageTaken.length, 0);
  assert.equal(device.stateMachine.state, "opening");

  // The release animation completes the hand-off: tags and effects are cleared.
  advanceTicks(CONFIG.timings.releaseAnimationTicks * 2);
  assert.equal(mob.hasTag("cc:trapped"), false);
});

test("mobs are frozen with slowness while held and thawed on release", () => {
  const { dimension, device } = setup();
  const mob = captureForTorture(dimension, device, { health: 40, maxHealth: 40 }, "minecraft:zombie");

  const freeze = mob.effects.get("slowness");
  assert.ok(freeze, "captured mobs receive the freeze effect");
  assert.equal(freeze.amplifier, CONFIG.containment.mobFreezeAmplifier);
  assert.equal(mob.effects.has("blindness"), true);

  device.release();
  advanceTicks(CONFIG.timings.releaseAnimationTicks * 2);
  assert.equal(mob.effects.has("slowness"), false);
  assert.equal(mob.effects.has("blindness"), false);
});

test("soul charge builds after the first strike, escalates damage, then discharges a soul", () => {
  const { dimension, device } = setup();
  const mob = captureForTorture(dimension, device, { health: 1000, maxHealth: 1000 }, "minecraft:zombie");
  assert.equal(device.charge, 0);

  withRandomSequence([0.5], () => {
    // 0.5 is above the extreme-damage chance and rolls 14 within [10, 18].
    // Four charge steps and five strikes fit inside four base intervals.
    advanceTicks(TORTURE_INTERVAL * 4);
  });

  // Base 14 at charge 0, then +30% per charge step, then a 1.5x surge discharge.
  assert.deepEqual(
    mob.damageTaken.map((entry) => entry.amount),
    [14, 18, 22, 26, 46],
    "damage escalates with the soul charge and peaks on the discharge",
  );
  assert.equal(device.durability, CONFIG.ironMaiden.baseDurability - 5);
  assert.equal(device.charge, 0, "a discharge resets the meter");
  assert.equal(device.souls, 1, "a discharge harvests a soul");
  assert.equal(dimension.sounds.some((cue) => cue.id === CONFIG.sounds.surge), true);
  assert.equal(dimension.sounds.some((cue) => cue.id === CONFIG.sounds.soul), true);
});

test("the soul charge drives the client-synced entity property", () => {
  const { dimension, device, deviceEntity } = setup();
  captureForTorture(dimension, device, { health: 1000, maxHealth: 1000 }, "minecraft:zombie");

  withRandomSequence([0.5], () => {
    advanceTicks(TORTURE_INTERVAL * 2);
  });

  assert.ok(device.charge >= 1);
  assert.equal(deviceEntity.getProperty("cc:charge"), device.charge);
  assert.equal(deviceEntity.getDynamicProperty("cc:device_charge"), device.charge);
});

test("harvested souls leave the wreck as soul shards", () => {
  const { dimension, device } = setup();
  device.souls = 10;
  assert.equal(device.takeDamage(device.durability), true);

  const shards = dimension.droppedItems.filter((entry) => entry.item.typeId === CONFIG.souls.itemId);
  assert.equal(shards.length, 10 / CONFIG.souls.perShard);
  assert.equal(device.souls, 0);
  assert.equal(dimension.droppedItems.some((entry) => entry.item.typeId === "cc:item_iron_maiden"), true);
});

test("a damaged device is repaired with the configured material", () => {
  const { dimension, device } = setup();
  device.takeDamage(100);
  const damaged = device.durability;

  const inventory = new FakeContainer();
  inventory.setItem(0, { typeId: "minecraft:iron_ingot", amount: 2, setAmount(amount) { this.amount = amount; } });
  const player = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 4, y: 64, z: 4,
  }, { inventory }));

  assert.equal(device.onInteract(player, inventory.getItem(0)), true);
  const expectedGain = Math.ceil(device.maxDurability * CONFIG.repair.materials.metal["minecraft:iron_ingot"]);
  assert.equal(device.durability, Math.min(device.maxDurability, damaged + expectedGain));
  assert.equal(inventory.getItem(0).amount, 1, "one ingot is consumed");

  // At full durability the material is refused instead of eaten.
  device.durability = device.maxDurability;
  assert.equal(device.onInteract(player, inventory.getItem(0)), false);
  assert.equal(inventory.getItem(0).amount, 1);
});

test("a soul shard wards its holder from capture and is consumed once", () => {
  const { dimension, device } = setup();
  const inventory = new FakeContainer();
  inventory.setItem(0, { typeId: CONFIG.souls.itemId, amount: 1, setAmount(amount) { this.amount = amount; } });
  const player = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 0.5, y: 64, z: 0.5,
  }, { inventory, isSneaking: true }));

  assert.equal(device.onInteract(player, inventory.getItem(0)), true);
  assert.equal(inventory.getItem(0), undefined);
  assert.equal(player.hasTag("cc:immune"), true);
  assert.match(player.messages.at(-1), /will not claim you/);

  device.tick(true);
  assert.equal(device.stateMachine.state, "idle", "an immune player is not detected");
  advanceTicks(CONFIG.ironMaiden.captureDelay);
  assert.equal(device.stateMachine.state, "idle");
  assert.equal(player.hasTag("cc:trapped"), false);
});

test("a rescuer frees a captured player and restores their movement", () => {
  const { dimension, device } = setup();
  const victim = captureForTorture(dimension, device);
  assert.equal(victim.inputPermissions.movement, false);

  const rescuer = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 3, y: 64, z: 3,
  }));
  assert.equal(device.onInteract(rescuer, null), true);
  assert.match(rescuer.messages.at(-1), /You freed the captive/);

  advanceTicks(CONFIG.timings.releaseAnimationTicks * 2);
  assert.equal(victim.hasTag("cc:trapped"), false);
  assert.equal(victim.inputPermissions.movement, true);
  assert.equal(device.stateMachine.state, "idle");
  assert.equal(dimension.sounds.some((cue) => cue.id === CONFIG.sounds.release), true);
});

test("a captured player sees a live action-bar status", () => {
  const { dimension, device } = setup();
  const victim = captureForTorture(dimension, device);

  assert.ok(victim.actionBars.length > 0, "the HUD is written on capture");
  const latest = victim.actionBars.at(-1);
  assert.match(latest, /Iron Maiden/);
  assert.match(latest, /Ask a teammate/);

  const before = victim.actionBars.length;
  advanceTicks(CONFIG.hud.intervalTicks + 1);
  assert.ok(victim.actionBars.length > before, "the HUD refreshes while held");
});

test("reinforcement and repair hints stay device-specific", () => {
  const { dimension, device } = setup();
  const player = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 4, y: 64, z: 4,
  }));

  device.onInteract(player, null);
  assert.match(player.messages.at(-1), /iron ingot or iron bars to repair/);

  const reliquaryEntity = dimension.add(new FakeEntity("cc:black_reliquary", dimension, {
    x: 20.5, y: 64, z: 20.5,
  }, { health: 1000, maxHealth: 1000 }));
  const reliquary = new TortureDevice("cc:black_reliquary", CONFIG.blackReliquary, reliquaryEntity);
  const other = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 24, y: 64, z: 24,
  }));
  reliquary.onInteract(other, null);
  assert.match(other.messages.at(-1), /obsidian to repair/);
});

test("the device drops its item exactly once even when the frame is hit twice", () => {
  const { dimension, device } = setup();
  resetSystem;
  assert.equal(device.takeDamage(device.maxDurability - 5), true);
  assert.equal(device.stateMachine.state, "idle");
  assert.equal(dimension.droppedItems.length, 0);

  assert.equal(device.takeDamage(5), true);
  assert.equal(device.stateMachine.state, "broken");
  assert.equal(dimension.droppedItems.length, 1);

  assert.equal(device.takeDamage(50), false);
  assert.equal(dimension.droppedItems.length, 1);
  assert.equal(dimension.sounds.some((cue) => cue.id === CONFIG.sounds.break), true);
});

test("a player who dies inside a device gets their movement back on respawn", () => {
  const { dimension, device } = setup();
  const victim = captureForTorture(dimension, device);
  assert.equal(victim.inputPermissions.movement, false);
  const victimId = String(victim.id);

  // Death: the device link is retired and the player entity is gone.
  device.onVictimUnavailable(victimId);
  victim.removeTag("cc:trapped");
  victim.removeTag("cc:capture_reserved");

  // The stale movement lock and its saved value are still on the player, so
  // the respawn recovery path must repair them.
  assert.equal(TortureDevice.needsCaptureRecovery(victim), true);
  TortureDevice.clearStaleCapture(victim);
  assert.equal(victim.inputPermissions.movement, true);
  assert.equal(victim.getDynamicProperty("cc:movement_was_enabled"), undefined);
  assert.equal(TortureDevice.needsCaptureRecovery(victim), false);

  // A player who was already locked down before capture keeps that state.
  const other = dimension.add(new FakeEntity("minecraft:player", dimension, {
    x: 6, y: 64, z: 6,
  }, { movementEnabled: false }));
  other.setDynamicProperty("cc:movement_was_enabled", false);
  TortureDevice.clearStaleCapture(other);
  assert.equal(other.inputPermissions.movement, false);
  assert.equal(other.getDynamicProperty("cc:movement_was_enabled"), undefined);
});
