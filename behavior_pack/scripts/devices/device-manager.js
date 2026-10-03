/**
 * Cursed Contraptions — Device Manager
 *
 * Owns device registration, load recovery, and the bounded gameplay tick loop.
 */

import { world, system } from "@minecraft/server";
import { CONFIG } from "../config.js";
import { Debug } from "../utils/debug.js";
import { DeviceState } from "../utils/state-machine.js";
import { IronMaiden } from "./iron-maiden.js";
import { CursedStocks } from "./cursed-stocks.js";
import { GravebinderCage } from "./gravebinder-cage.js";
import { RegretRack } from "./regret-rack.js";
import { BlackReliquary } from "./black-reliquary.js";

const DEVICE_TYPES = Object.freeze({
  "cc:iron_maiden": IronMaiden,
  "cc:cursed_stocks": CursedStocks,
  "cc:gravebinder_cage": GravebinderCage,
  "cc:regret_rack": RegretRack,
  "cc:black_reliquary": BlackReliquary,
});

const ACTIVE_STATES = new Set([
  DeviceState.DETECTING,
  DeviceState.CAPTURING,
  DeviceState.CLOSED,
  DeviceState.TORTURING,
  DeviceState.OPENING,
]);

class DeviceManager {
  constructor() {
    this.devices = new Map();
    this._tickHandle = null;
    this._tickCounter = 0;
    this._nextIdlePollTick = CONFIG.performance.idlePollIntervalTicks;
    this._initialized = false;
  }

  register(entity) {
    if (!entity || !this._isValid(entity)) return null;
    const DeviceClass = DEVICE_TYPES[entity.typeId];
    if (!DeviceClass) {
      Debug.warn("Manager", `Unknown device type: ${entity.typeId}`);
      return null;
    }

    const entityId = String(entity.id);
    const existing = this.devices.get(entityId);
    if (existing) return existing;

    try {
      const device = new DeviceClass(entity);
      this.devices.set(entityId, device);
      Debug.info("Manager", `Registered ${entity.typeId} (${this.devices.size} total)`);
      return device;
    } catch (error) {
      Debug.error("Manager", `Could not register ${entity.typeId}`, error);
      return null;
    }
  }

  unregister(entityId) {
    const id = String(entityId);
    const device = this.devices.get(id);
    if (!device) return false;

    device.dispose();
    this.devices.delete(id);
    Debug.info("Manager", `Unregistered device (${this.devices.size} remaining)`);
    return true;
  }

  getDevice(entity) {
    return entity ? this.devices.get(String(entity.id)) || null : null;
  }

  getDeviceByVictimId(victimId) {
    const id = String(victimId);
    for (const device of this.devices.values()) {
      if (String(device.victimId) === id || String(device._pendingTargetId) === id) return device;
    }
    return null;
  }

  hasVictimOrPending(victimId) {
    return this.getDeviceByVictimId(victimId) !== null;
  }

  start() {
    if (this._initialized) return;
    this._initialized = true;
    this._tickHandle = system.runInterval(
      () => this._tick(),
      CONFIG.performance.pollIntervalTicks,
    );
    Debug.info("Manager", "Device manager started");
  }

  stop() {
    if (this._tickHandle !== null) {
      try { system.clearRun(this._tickHandle); } catch (_) {}
      this._tickHandle = null;
    }
    for (const device of this.devices.values()) device.dispose();
    this.devices.clear();
    this._initialized = false;
    Debug.info("Manager", "Device manager stopped");
  }

  _tick() {
    this._tickCounter += CONFIG.performance.pollIntervalTicks;
    const pollIdleDevices = this._tickCounter >= this._nextIdlePollTick;
    if (pollIdleDevices) {
      do {
        this._nextIdlePollTick += CONFIG.performance.idlePollIntervalTicks;
      } while (this._nextIdlePollTick <= this._tickCounter);
    }

    let activeCount = this.activeCount;
    const removed = [];

    for (const [entityId, device] of this.devices) {
      if (!device._entityValid()) {
        device.dispose();
        removed.push(entityId);
        continue;
      }

      const wasActive = ACTIVE_STATES.has(device.stateMachine.state);
      const canActivate = activeCount < CONFIG.performance.maxActiveDevices;
      const shouldCheckForTargets = device.stateMachine.is(DeviceState.IDLE)
        ? pollIdleDevices
        : true;

      device.tick(canActivate, shouldCheckForTargets);

      const isActive = ACTIVE_STATES.has(device.stateMachine.state);
      if (!wasActive && isActive) activeCount++;
      else if (wasActive && !isActive) activeCount = Math.max(0, activeCount - 1);
    }

    for (const entityId of removed) this.devices.delete(entityId);
  }

  discoverAll() {
    let discovered = 0;
    for (const dimensionId of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
      try {
        const dimension = world.getDimension(dimensionId);
        for (const entity of dimension.getEntities({ families: ["cc_device"] })) {
          if (this.register(entity)) discovered++;
        }
      } catch (_) {
        // Dimensions can be unavailable during early world initialization.
      }
    }
    Debug.info("Manager", `Discovered ${discovered} device entities on load`);
    return discovered;
  }

  _isValid(entity) {
    try {
      return typeof entity.isValid === "function" ? entity.isValid() : entity.isValid === true;
    } catch (_) {
      return false;
    }
  }

  get activeCount() {
    let count = 0;
    for (const device of this.devices.values()) {
      if (ACTIVE_STATES.has(device.stateMachine.state)) count++;
    }
    return count;
  }

  get totalCount() {
    return this.devices.size;
  }
}

export const deviceManager = new DeviceManager();
