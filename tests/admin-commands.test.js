import assert from "node:assert/strict";
import test from "node:test";
import { CONFIG } from "../behavior_pack/scripts/config.js";
import { deviceManager } from "../behavior_pack/scripts/devices/device-manager.js";
import {
  resetSystem,
  system,
} from "./mocks/minecraft-server.mjs";

// Importing the real entry point subscribes every event handler against the
// 1.17.0-shaped mock, which is itself a regression test for finding F1: the
// module must evaluate without throwing on the stable-only API surface.
import "../behavior_pack/scripts/main.js";

class FakeContainer {
  constructor(size = 9, filledSlots = 0) {
    this.slots = new Array(size);
    for (let slot = 0; slot < filledSlots; slot++) {
      this.slots[slot] = { typeId: "minecraft:dirt", amount: 1 };
    }
  }
  getItem(slot) { return this.slots[slot]; }
  setItem(slot, item) { this.slots[slot] = item; }
  addItem(item) {
    // Real Container.addItem contract: undefined when the whole stack fits,
    // or the leftover stack when it does not.
    const slot = this.slots.findIndex((current) => !current);
    if (slot < 0) return item;
    this.slots[slot] = item;
    return undefined;
  }
}

let nextId = 1;
class FakePlayer {
  constructor(options = {}) {
    this.id = options.id || `player-${nextId++}`;
    this.typeId = "minecraft:player";
    this.valid = true;
    this.tags = new Set(options.tags || []);
    this.messages = [];
    this.inventory = options.inventory || new FakeContainer();
    this.selectedSlotIndex = 0;
    this.dynamicProperties = new Map();
  }
  isValid() { return this.valid; }
  hasTag(tag) { return this.tags.has(tag); }
  addTag(tag) { this.tags.add(tag); }
  removeTag(tag) { this.tags.delete(tag); }
  sendMessage(message) { this.messages.push(message); }
  getComponent(typeId) {
    if (typeId === "minecraft:inventory") return { container: this.inventory };
    return undefined;
  }
  getDynamicProperty(id) { return this.dynamicProperties.get(id); }
  setDynamicProperty(id, value) {
    if (value === undefined) this.dynamicProperties.delete(id);
    else this.dynamicProperties.set(id, value);
  }
}

class FakeDeviceEntity {
  constructor() {
    this.id = `device-${nextId++}`;
    this.typeId = "cc:iron_maiden";
    this.valid = true;
    this.tags = new Set();
    this.dynamicProperties = new Map();
    this.properties = new Map([
      ["cc:state", "idle"],
      ["cc:durability", CONFIG.ironMaiden.baseDurability],
      ["cc:armor_count", 0],
    ]);
  }
  isValid() { return this.valid; }
  hasTag(tag) { return this.tags.has(tag); }
  addTag(tag) { this.tags.add(tag); }
  removeTag(tag) { this.tags.delete(tag); }
  getDynamicProperty(id) { return this.dynamicProperties.get(id); }
  setDynamicProperty(id, value) {
    if (value === undefined) this.dynamicProperties.delete(id);
    else this.dynamicProperties.set(id, value);
  }
  getProperty(id) { return this.properties.get(id); }
  setProperty(id, value) { this.properties.set(id, value); }
}

function fireScriptEvent(payload) {
  system.afterEvents.scriptEventReceive.fire(payload);
}

test.beforeEach(() => {
  resetSystem();
  deviceManager.stop();
  CONFIG.debug.enabled = false;
  CONFIG.debug.chatDebug = false;
});

test.after(() => {
  deviceManager.stop();
});

test("the entry point subscribes to scriptevent with the cc: namespace filter", () => {
  assert.equal(system.afterEvents.scriptEventReceive.subscriberCount(), 1);
  // A different namespace must be filtered out before reaching the handler.
  const admin = new FakePlayer({ tags: ["cc:admin"] });
  fireScriptEvent({ id: "other:give", message: "", sourceEntity: admin });
  assert.equal(admin.messages.length, 0);
});

test("commands are ignored for non-player or missing sources", () => {
  fireScriptEvent({ id: "cc:give", message: "", sourceEntity: undefined });
  const zombie = new FakePlayer();
  zombie.typeId = "minecraft:zombie";
  fireScriptEvent({ id: "cc:give", message: "", sourceEntity: zombie });
  assert.equal(zombie.messages.length, 0);
});

test("every command requires the cc:admin tag", () => {
  const player = new FakePlayer();
  fireScriptEvent({ id: "cc:give", message: "", sourceEntity: player });
  fireScriptEvent({ id: "cc:devices", message: "", sourceEntity: player });
  fireScriptEvent({ id: "cc:debug", message: "on", sourceEntity: player });
  assert.equal(player.messages.length, 3);
  assert.ok(player.messages.every((line) => line.includes("cc:admin")));
  assert.equal(player.inventory.slots.filter(Boolean).length, 0);
  assert.equal(CONFIG.debug.enabled, false);
});

test("cc:give adds all five devices when the inventory has room", () => {
  const admin = new FakePlayer({ tags: ["cc:admin"] });
  fireScriptEvent({ id: "cc:give", message: "", sourceEntity: admin });
  const storedTypes = admin.inventory.slots.filter(Boolean).map((item) => item.typeId);
  assert.deepEqual(storedTypes, [
    "cc:item_iron_maiden",
    "cc:item_cursed_stocks",
    "cc:item_gravebinder_cage",
    "cc:item_regret_rack",
    "cc:item_black_reliquary",
  ]);
  assert.equal(admin.inventory.slots.length, 9);
  assert.equal(admin.messages.length, 1);
  assert.ok(admin.messages[0].includes("All five devices were added"));
});

test("cc:give counts addItem leftovers as failures (v0.1.0 counters were correct)", () => {
  // Container.addItem returns the leftover stack (truthy) on failure and
  // undefined on success; the v0.1.0 give handler already counted truthy as
  // "did not fit". This test pins that contract (audit finding F2).
  const admin = new FakePlayer({ tags: ["cc:admin"], inventory: new FakeContainer(9, 9) });
  fireScriptEvent({ id: "cc:give", message: "", sourceEntity: admin });
  assert.equal(admin.messages.length, 1);
  assert.ok(admin.messages[0].includes("Added 0 device(s); inventory space ran out"));
  assert.ok(admin.inventory.slots.every((item) => item?.typeId === "minecraft:dirt"));
});

test("cc:devices sends one message per device and never relies on a giant string", () => {
  const admin = new FakePlayer({ tags: ["cc:admin"] });
  const deviceCount = 40;
  for (let i = 0; i < deviceCount; i++) {
    assert.ok(deviceManager.register(new FakeDeviceEntity()));
  }
  fireScriptEvent({ id: "cc:devices", message: "", sourceEntity: admin });

  // Bedrock truncates a single chat message at a few hundred characters, so
  // the listing must not be one concatenated string (audit finding F6).
  assert.equal(admin.messages.length, 1 + deviceCount);
  assert.ok(admin.messages[0].includes(`Total: ${deviceCount}, Active: 0`));
  assert.ok(admin.messages.slice(1).every((line) => line.includes("cc:iron_maiden") && line.includes("Durability:")));
  assert.ok(admin.messages.every((line) => line.length < 512));
  assert.ok(admin.messages.join("\n").length > 512);
});

test("cc:debug toggles both debug flags and rejects unknown arguments", () => {
  const admin = new FakePlayer({ tags: ["cc:admin"] });

  fireScriptEvent({ id: "cc:debug", message: "on", sourceEntity: admin });
  assert.equal(CONFIG.debug.enabled, true);
  assert.equal(CONFIG.debug.chatDebug, true);
  assert.ok(admin.messages[0].includes("Debug enabled"));

  fireScriptEvent({ id: "cc:debug", message: "off", sourceEntity: admin });
  assert.equal(CONFIG.debug.enabled, false);
  assert.equal(CONFIG.debug.chatDebug, false);
  assert.ok(admin.messages[1].includes("Debug disabled"));

  fireScriptEvent({ id: "cc:debug", message: "maybe", sourceEntity: admin });
  assert.equal(CONFIG.debug.enabled, false);
  assert.ok(admin.messages[2].includes("cc:debug on"));
});

test("unknown cc: commands get a usage hint instead of silent failure", () => {
  const admin = new FakePlayer({ tags: ["cc:admin"] });
  fireScriptEvent({ id: "cc:wat", message: "", sourceEntity: admin });
  assert.equal(admin.messages.length, 1);
  assert.ok(admin.messages[0].includes("cc:give"));
  assert.ok(admin.messages[0].includes("cc:devices"));
  assert.ok(admin.messages[0].includes("cc:debug"));
});
