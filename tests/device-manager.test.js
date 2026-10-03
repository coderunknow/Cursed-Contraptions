import assert from "node:assert/strict";
import test from "node:test";
import { DeviceState } from "../behavior_pack/scripts/utils/state-machine.js";
import { deviceManager } from "../behavior_pack/scripts/devices/device-manager.js";
import { resetSystem } from "./mocks/minecraft-server.mjs";

function fakeDevice(overrides = {}) {
  return {
    _disposed: false,
    stateMachine: {
      state: DeviceState.IDLE,
      is(...states) { return states.includes(this.state); },
    },
    _entityValid: () => true,
    dispose() { this._disposed = true; },
    tick() {},
    ...overrides,
  };
}

test.beforeEach(() => {
  resetSystem();
  deviceManager.devices.clear();
});

test.after(() => {
  deviceManager.devices.clear();
});

test("one throwing device cannot break the shared tick interval (F9)", () => {
  let goodTicks = 0;
  const bad = fakeDevice({
    tick() { throw new Error("device exploded mid-tick"); },
  });
  const good = fakeDevice({
    tick() { goodTicks++; },
  });
  deviceManager.devices.set("bad-device", bad);
  deviceManager.devices.set("good-device", good);

  deviceManager._tick();
  deviceManager._tick();

  assert.equal(goodTicks, 2);
  assert.equal(deviceManager.totalCount, 2);
});

test("invalid devices are still disposed and removed by the tick", () => {
  let disposed = 0;
  const stale = fakeDevice({
    _entityValid: () => false,
    dispose() { disposed++; },
  });
  const alive = fakeDevice();
  deviceManager.devices.set("stale-device", stale);
  deviceManager.devices.set("alive-device", alive);

  deviceManager._tick();

  assert.equal(disposed, 1);
  assert.equal(deviceManager.devices.has("stale-device"), false);
  assert.equal(deviceManager.devices.has("alive-device"), true);
  assert.equal(deviceManager.totalCount, 1);
});
