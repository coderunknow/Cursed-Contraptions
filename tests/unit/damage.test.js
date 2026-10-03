import assert from "node:assert/strict";
import test from "node:test";
import {
  applyDamage,
  isEntityValid,
  randomDamage,
  rollExtremeDamage,
} from "../../behavior_pack/scripts/utils/damage.js";

test("random damage includes both configured endpoints", () => {
  assert.equal(randomDamage(4, 8, () => 0), 4);
  assert.equal(randomDamage(4, 8, () => 0.999999), 8);
  assert.throws(() => randomDamage(8, 4), RangeError);
});

test("critical probability handles boundary values", () => {
  assert.equal(rollExtremeDamage(0, () => 0), false);
  assert.equal(rollExtremeDamage(1, () => 0.999), true);
  assert.equal(rollExtremeDamage(0.2, () => 0.19), true);
  assert.equal(rollExtremeDamage(0.2, () => 0.2), false);
});

test("damage checks validity and reports API failures", () => {
  let total = 0;
  const entity = {
    isValid: () => true,
    applyDamage(amount, options) { total += amount; assert.equal(options.cause, "contact"); return true; },
  };
  assert.equal(isEntityValid(entity), true);
  assert.equal(applyDamage(entity, 5), true);
  assert.equal(total, 5);
  assert.equal(applyDamage(entity, -1), false);
  assert.equal(applyDamage({ isValid: false }, 1), false);
  assert.equal(applyDamage({ isValid: true, applyDamage() { return false; } }, 1), false);
  assert.equal(applyDamage({ isValid: true, applyDamage() { throw new Error("invalid"); } }, 1), false);
});
