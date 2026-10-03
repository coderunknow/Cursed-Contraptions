import assert from "node:assert/strict";
import test from "node:test";
import {
  clearProp,
  getBoolProp,
  getIntProp,
  getStringProp,
  setBoolProp,
  setIntProp,
  setStringProp,
} from "../../behavior_pack/scripts/utils/persistence.js";

class FakeEntity {
  dynamic = new Map();
  legacy = new Map();

  getDynamicProperty(id) { return this.dynamic.get(id); }
  setDynamicProperty(id, value) {
    if (value === undefined) this.dynamic.delete(id);
    else this.dynamic.set(id, value);
  }
  getProperty(id) { return this.legacy.get(id); }
}

test("typed values round-trip through dynamic properties", () => {
  const entity = new FakeEntity();
  assert.equal(setStringProp(entity, "state", "torturing"), true);
  assert.equal(setIntProp(entity, "durability", 77.8), true);
  assert.equal(setBoolProp(entity, "enabled", true), true);
  assert.equal(getStringProp(entity, "state"), "torturing");
  assert.equal(getIntProp(entity, "durability"), 77);
  assert.equal(getBoolProp(entity, "enabled"), true);
});

test("old entity properties are read as migration fallbacks", () => {
  const entity = new FakeEntity();
  entity.legacy.set("cc:state", "closed");
  entity.legacy.set("cc:durability", 125);
  entity.legacy.set("cc:armor_count", 2);
  assert.equal(getStringProp(entity, "state"), "closed");
  assert.equal(getIntProp(entity, "durability"), 125);
  assert.equal(getIntProp(entity, "armor_count"), 2);
});

test("invalid typed values use safe defaults and properties can be cleared", () => {
  const entity = new FakeEntity();
  assert.equal(setIntProp(entity, "bad", Number.NaN), false);
  assert.equal(getIntProp(entity, "missing", 19), 19);
  assert.equal(getBoolProp(entity, "missing", true), true);
  setStringProp(entity, "state", "idle");
  assert.equal(clearProp(entity, "state"), true);
  assert.equal(getStringProp(entity, "state", "fallback"), "fallback");
});
