/**
 * Cursed Contraptions — Debug Utilities
 * 
 * Lightweight debug pathway. Disabled in normal gameplay.
 * When enabled, provides inspection of device state without
 * spamming chat every tick.
 */

import { CONFIG } from "../config.js";
import { world } from "@minecraft/server";

export class Debug {
  static info(tag, message) {
    if (!CONFIG.debug.enabled) return;
    const prefix = `[CC:${tag}]`;
    if (CONFIG.debug.chatDebug) {
      try {
        world.sendMessage(`§7${prefix} ${message}`);
      } catch (_) { /* no players */ }
    }
    // Always log to server console for dev
    console.warn(`${prefix} ${message}`);
  }

  static warn(tag, message) {
    const prefix = `[CC:${tag}:WARN]`;
    console.warn(`${prefix} ${message}`);
    if (CONFIG.debug.chatDebug) {
      try {
        world.sendMessage(`§e${prefix} ${message}`);
      } catch (_) {}
    }
  }

  static error(tag, message, err) {
    const prefix = `[CC:${tag}:ERROR]`;
    const fullMsg = err ? `${message}: ${err.message || err}` : message;
    console.error(`${prefix} ${fullMsg}`);
    if (CONFIG.debug.chatDebug) {
      try {
        world.sendMessage(`§c${prefix} ${fullMsg}`);
      } catch (_) {}
    }
  }

  /**
   * Inspect a device's state for debugging.
   */
  static inspectDevice(device) {
    if (!CONFIG.debug.enabled) return;
    Debug.info("DEBUG", JSON.stringify({
      type: device.typeId,
      state: device.stateMachine.state,
      durability: device.durability,
      maxDurability: device.maxDurability,
      victimId: device.victimId || "none",
      armorCount: device.armorCount,
      position: device.position ? 
        `${device.position.x.toFixed(1)}, ${device.position.y.toFixed(1)}, ${device.position.z.toFixed(1)}` 
        : "unknown",
      activeTimer: device._tortureTimer ? "running" : "none",
    }));
  }
}
