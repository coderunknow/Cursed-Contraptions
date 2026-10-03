/**
 * Cursed Contraptions — Device Manager
 * 
 * Central registry for all active torture devices.
 * Handles entity lifecycle, chunk events, and the tick loop.
 * 
 * Performance architecture:
 *   - Only active devices (those with victims or powered) tick frequently
 *   - Idle devices check for entities at a reduced rate
 *   - Broken/disposed devices are removed immediately
 *   - No global entity scans — each device only checks its local area
 */

import { world, system } from "@minecraft/server";
import { CONFIG } from "../config.js";
import { Debug } from "../utils/debug.js";
import { DeviceState } from "../utils/state-machine.js";
import { IronMaiden } from "../devices/iron-maiden.js";
import { CursedStocks } from "../devices/cursed-stocks.js";
import { GravebinderCage } from "../devices/gravebinder-cage.js";
import { RegretRack } from "../devices/regret-rack.js";
import { BlackReliquary } from "../devices/black-reliquary.js";

// Map of entity type ID → device class constructor
const DEVICE_TYPES = {
  "cc:iron_maiden":      IronMaiden,
  "cc:cursed_stocks":    CursedStocks,
  "cc:gravebinder_cage": GravebinderCage,
  "cc:regret_rack":      RegretRack,
  "cc:black_reliquary":  BlackReliquary,
};

class DeviceManager {
  constructor() {
    /** @type {Map<string, TortureDevice>} entityId → device */
    this.devices = new Map();
    this._tickHandle = null;
    this._tickCounter = 0;
    this._initialized = false;
  }

  /**
   * Register a device entity. Creates the appropriate device instance
   * and adds it to the registry.
   */
  register(entity) {
    if (!entity || !entity.isValid()) return null;
    const typeId = entity.typeId;
    const DeviceClass = DEVICE_TYPES[typeId];
    if (!DeviceClass) {
      Debug.warn("Manager", `Unknown device type: ${typeId}`);
      return null;
    }

    // Prevent duplicates
    const eid = String(entity.id);
    if (this.devices.has(eid)) {
      return this.devices.get(eid);
    }

    const device = new DeviceClass(entity);
    this.devices.set(eid, device);
    Debug.info("Manager", `Registered ${typeId} (${this.devices.size} total)`);
    return device;
  }

  /**
   * Unregister a device entity.
   */
  unregister(entityId) {
    const eid = String(entityId);
    const device = this.devices.get(eid);
    if (device) {
      device.dispose();
      this.devices.delete(eid);
      Debug.info("Manager", `Unregistered device (${this.devices.size} remaining)`);
    }
  }

  /**
   * Get a device by entity reference.
   */
  getDevice(entity) {
    if (!entity) return null;
    return this.devices.get(String(entity.id)) || null;
  }

  /**
   * Start the manager tick loop.
   */
  start() {
    if (this._initialized) return;
    this._initialized = true;

    // Main tick loop — runs every N ticks
    this._tickHandle = system.runInterval(() => {
      this._tick();
    }, 5); // Check every 5 ticks (0.25 seconds)

    Debug.info("Manager", "Device manager started");
  }

  stop() {
    if (this._tickHandle) {
      try { system.clearRun(this._tickHandle); } catch (_) {}
      this._tickHandle = null;
    }
    // Dispose all devices
    for (const [_, device] of this.devices) {
      device.dispose();
    }
    this.devices.clear();
    this._initialized = false;
    Debug.info("Manager", "Device manager stopped");
  }

  /**
   * Internal tick — processes active devices and periodically checks idle ones.
   */
  _tick() {
    this._tickCounter++;

    const toRemove = [];

    for (const [eid, device] of this.devices) {
      // Check if entity is still valid
      if (!device._entityValid()) {
        toRemove.push(eid);
        continue;
      }

      const state = device.stateMachine.state;

      // Active states get ticked every cycle
      if (state === DeviceState.TORTURING || state === DeviceState.CAPTURING || state === DeviceState.DETECTING) {
        device.tick();
      }
      // Idle devices check for entities at a reduced rate
      else if (state === DeviceState.IDLE) {
        if (this._tickCounter % 4 === 0) { // ~every second at 5-tick interval
          device.tick();
        }
      }
      // Other states don't need ticking
    }

    // Clean up removed devices
    for (const eid of toRemove) {
      const device = this.devices.get(eid);
      if (device) device.dispose();
      this.devices.delete(eid);
    }
  }

  /**
   * Discover and register all device entities in the world.
   * Called on world load to restore state.
   */
  discoverAll() {
    for (const dimId of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
      try {
        const dim = world.getDimension(dimId);
        for (const typeId of Object.keys(DEVICE_TYPES)) {
          try {
            const entities = dim.getEntities({ type: typeId });
            for (const entity of entities) {
              this.register(entity);
            }
          } catch (_) {}
        }
      } catch (_) {}
    }
    Debug.info("Manager", `Discovered ${this.devices.size} devices on load`);
  }

  /**
   * Get count of active (non-idle, non-broken) devices.
   */
  get activeCount() {
    let count = 0;
    for (const [_, device] of this.devices) {
      if (!device.stateMachine.is(DeviceState.IDLE, DeviceState.BROKEN, DeviceState.RELEASED)) {
        count++;
      }
    }
    return count;
  }

  get totalCount() {
    return this.devices.size;
  }
}

// Singleton
export const deviceManager = new DeviceManager();
