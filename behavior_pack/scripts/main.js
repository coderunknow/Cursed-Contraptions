/**
 * Cursed Contraptions — Main Entry Point
 */

import {
  world,
  system,
  ItemStack,
  InputPermissionCategory,
} from "@minecraft/server";
import { deviceManager } from "./devices/device-manager.js";
import { CONFIG } from "./config.js";
import { Debug } from "./utils/debug.js";
import { isEntityValid } from "./utils/damage.js";

const BLOCK_TO_ENTITY = Object.freeze({
  "cc:iron_maiden_block": "cc:iron_maiden",
  "cc:cursed_stocks_block": "cc:cursed_stocks",
  "cc:gravebinder_cage_block": "cc:gravebinder_cage",
  "cc:regret_rack_block": "cc:regret_rack",
  "cc:black_reliquary_block": "cc:black_reliquary",
});
/** @type {Set<string>} */
const ENTITY_TYPES = new Set(Object.values(BLOCK_TO_ENTITY));
const DEVICE_ITEMS = Object.freeze([
  "cc:item_iron_maiden",
  "cc:item_cursed_stocks",
  "cc:item_gravebinder_cage",
  "cc:item_regret_rack",
  "cc:item_black_reliquary",
]);
const TRAPPED_TAG = "cc:trapped";
const CAPTURE_RESERVED_TAG = "cc:capture_reserved";
const MOVEMENT_SAVED_PROPERTY = "cc:movement_was_enabled";

/**
 * A single failing event subscription must never abort module evaluation and
 * leave the pack without any handlers at all.
 * @param {string} name Human-readable subscription name for error logs.
 * @param {() => void} subscribe Body that performs the actual subscription.
 */
function subscribeSafely(name, subscribe) {
  try {
    subscribe();
  } catch (error) {
    Debug.error("Main", `Could not subscribe to ${name}`, error);
  }
}

subscribeSafely("initialization", () => {
  system.run(() => {
    Debug.info("Main", "Cursed Contraptions initializing...");
    deviceManager.start();
    deviceManager.discoverAll();
    Debug.info("Main", `Loaded ${deviceManager.totalCount} devices.`);
  });
});

subscribeSafely("device placement", () => {
  world.afterEvents.playerPlaceBlock.subscribe((event) => {
  const blockTypeId = event.block?.typeId;
  const entityTypeId = BLOCK_TO_ENTITY[blockTypeId];
  if (!entityTypeId) return;

  const dimension = event.player.dimension;
  const blockLocation = { ...event.block.location };
  system.run(() => {
    let entity = null;
    try {
      const placedBlock = dimension.getBlock(blockLocation);
      if (!placedBlock || placedBlock.typeId !== blockTypeId) return;

      entity = dimension.spawnEntity(entityTypeId, {
        x: blockLocation.x + 0.5,
        y: blockLocation.y,
        z: blockLocation.z + 0.5,
      });
      dimension.setBlockType(blockLocation, "minecraft:air");

      if (!deviceManager.register(entity)) {
        try { entity.remove(); } catch (_) {}
        dimension.setBlockType(blockLocation, blockTypeId);
        return;
      }
      Debug.info("Main", `Placed ${entityTypeId} at ${blockLocation.x}, ${blockLocation.y}, ${blockLocation.z}`);
    } catch (error) {
      if (entity && isEntityValid(entity)) {
        try { entity.remove(); } catch (_) {}
      }
      try {
        const current = dimension.getBlock(blockLocation);
        if (current?.typeId === "minecraft:air") dimension.setBlockType(blockLocation, blockTypeId);
      } catch (_) {}
      Debug.error("Main", `Could not place ${entityTypeId}`, error);
    }
  });
  });
});

function handleInteract(player, target) {
  if (!isEntityValid(player) || !target || !ENTITY_TYPES.has(target.typeId)) return;
  const device = deviceManager.getDevice(target);
  if (!device) return;

  let heldItem = null;
  try {
    const inventory = player.getComponent("minecraft:inventory")?.container;
    if (inventory) heldItem = inventory.getItem(player.selectedSlotIndex) || null;
  } catch (_) {}

  device.onInteract(player, heldItem);
}

subscribeSafely("entity interactions", () => {
  world.afterEvents.playerInteractWithEntity.subscribe((event) => {
    system.run(() => handleInteract(event.player, event.target));
  });
});

subscribeSafely("device damage", () => {
  world.afterEvents.entityHurt.subscribe((event) => {
  const hurtEntity = event.hurtEntity;
  if (!hurtEntity) return;

  if (ENTITY_TYPES.has(hurtEntity.typeId)) {
    const device = deviceManager.getDevice(hurtEntity);
    if (device && event.damage > 0) device.takeDamage(event.damage);
  }
  });
});

subscribeSafely("entity death", () => {
  world.afterEvents.entityDie.subscribe((event) => {
  const deadEntity = event.deadEntity;
  if (!deadEntity) return;

  if (ENTITY_TYPES.has(deadEntity.typeId)) {
    const device = deviceManager.getDevice(deadEntity);
    if (device) {
      let dimension;
      let position;
      try { dimension = deadEntity.dimension; } catch (_) {}
      try { position = deadEntity.location; } catch (_) {}
      device.onEntityDeath(dimension, position);
      deviceManager.unregister(deadEntity.id);
    }
    return;
  }

  const id = String(deadEntity.id);
  const device = deviceManager.getDeviceByVictimId(id);
  if (device) device.onVictimUnavailable(id);
  try {
    deadEntity.removeTag(TRAPPED_TAG);
    deadEntity.removeTag(CAPTURE_RESERVED_TAG);
  } catch (_) {}
  });
});

subscribeSafely("entity load", () => {
  world.afterEvents.entityLoad.subscribe((event) => {
  const entity = event.entity;
  if (!entity) return;

  if (ENTITY_TYPES.has(entity.typeId)) {
    system.runTimeout(() => {
      if (isEntityValid(entity)) deviceManager.register(entity);
    }, CONFIG.performance.chunkLoadGracePeriod);
    return;
  }

  const hasCaptureTag = (() => {
    try { return entity.hasTag(TRAPPED_TAG) || entity.hasTag(CAPTURE_RESERVED_TAG); } catch (_) { return false; }
  })();
  if (!hasCaptureTag) return;

  system.runTimeout(() => {
    if (!isEntityValid(entity) || deviceManager.hasVictimOrPending(entity.id)) return;
    clearStaleCapture(entity);
  }, CONFIG.performance.chunkLoadGracePeriod + 5);
  });
});

subscribeSafely("player spawn", () => {
  world.afterEvents.playerSpawn.subscribe((event) => {
  const player = event.player;
  system.runTimeout(() => {
    if (!isEntityValid(player)) return;
    const device = deviceManager.getDeviceByVictimId(player.id);
    if (device?.reconnectVictim(player)) return;

    try {
      if (player.hasTag(TRAPPED_TAG) || player.hasTag(CAPTURE_RESERVED_TAG)) {
        clearStaleCapture(player);
      }
    } catch (_) {}
  }, CONFIG.performance.chunkLoadGracePeriod + 5);
  });
});

subscribeSafely("player leave", () => {
  world.afterEvents.playerLeave.subscribe((event) => {
  const playerId = String(event.playerId);
  const device = deviceManager.getDeviceByVictimId(playerId);
  if (device) device.onVictimUnavailable(playerId);
  });
});

function clearStaleCapture(entity) {
  try {
    entity.removeTag(TRAPPED_TAG);
    entity.removeTag(CAPTURE_RESERVED_TAG);
  } catch (_) {}

  if (entity.typeId !== "minecraft:player") return;
  let saved;
  try { saved = entity.getDynamicProperty(MOVEMENT_SAVED_PROPERTY); } catch (_) {}
  if (typeof saved === "boolean") {
    try { entity.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, saved); } catch (_) {}
  }
  try { entity.setDynamicProperty(MOVEMENT_SAVED_PROPERTY, undefined); } catch (_) {}
}

subscribeSafely("redstone polling", () => {
  system.runInterval(() => {
  for (const device of deviceManager.devices.values()) {
    if (device._disposed || !device._entityValid()) continue;
    const position = device.position;
    if (!position) continue;

    let powered = false;
    try {
      const dimension = device.entity.dimension;
      const center = {
        x: Math.floor(position.x),
        y: Math.floor(position.y),
        z: Math.floor(position.z),
      };
      const offsets = [
        { x: 1, y: 0, z: 0 }, { x: -1, y: 0, z: 0 },
        { x: 0, y: 1, z: 0 }, { x: 0, y: -1, z: 0 },
        { x: 0, y: 0, z: 1 }, { x: 0, y: 0, z: -1 },
      ];
      for (const offset of offsets) {
        try {
          const block = dimension.getBlock({
            x: center.x + offset.x,
            y: center.y + offset.y,
            z: center.z + offset.z,
          });
          if ((block?.getRedstonePower?.() || 0) > 0) {
            powered = true;
            break;
          }
        } catch (_) {
          // Skip this side if its neighboring chunk is not loaded.
        }
      }
    } catch (_) {
      // Redstone queries may fail at unloaded chunk boundaries.
    }
    try {
      device.onRedstonePower(powered);
    } catch (error) {
      // One broken device must never kill the shared polling interval.
      Debug.error("Main", "Redstone poll failed for a device", error);
    }
  }
  }, CONFIG.performance.redstonePollIntervalTicks);
});

/**
 * Admin commands arrive as /scriptevent so they work with the stable
 * @minecraft/server dependency. The beta-only world.beforeEvents.chatSend
 * API is undefined under the stable types (audit finding F1), so the old
 * !cc chat commands never ran at all.
 *
 * Commands (cheats must be enabled; every command requires the cc:admin tag):
 *   /scriptevent cc:give      — add all five devices to your inventory
 *   /scriptevent cc:devices   — list registered devices and their state
 *   /scriptevent cc:debug on  — enable debug logging
 *   /scriptevent cc:debug off — disable debug logging
 */
function handleAdminScriptEvent(event) {
  const sender = event.sourceEntity;
  if (!isEntityValid(sender) || sender.typeId !== "minecraft:player") return;

  let isAdmin = false;
  try {
    isAdmin = sender.hasTag("cc:admin");
  } catch (_) {
    isAdmin = false;
  }
  if (!isAdmin) {
    try { sender.sendMessage("§cCursed Contraptions admin commands require the cc:admin tag."); } catch (_) {}
    return;
  }

  switch (event.id) {
    case "cc:give":
      giveAdminDevices(sender);
      return;
    case "cc:devices":
      listAdminDevices(sender);
      return;
    case "cc:debug":
      toggleAdminDebug(sender, event.message);
      return;
    default:
      sender.sendMessage("§e[Cursed Contraptions] Unknown command. Use /scriptevent cc:give, /scriptevent cc:devices, or /scriptevent cc:debug on|off.");
  }
}

function giveAdminDevices(sender) {
  try {
    const inventory = sender.getComponent("minecraft:inventory")?.container;
    if (!inventory) throw new Error("Player inventory is unavailable");
    let added = 0;
    let remaining = 0;
    for (const itemId of DEVICE_ITEMS) {
      // Container.addItem returns undefined when the whole stack fits, or the
      // leftover stack when it does not — a truthy result means the device
      // could not be added. Do not "fix" these branches (audit finding F2).
      if (inventory.addItem(new ItemStack(itemId, 1))) remaining++;
      else added++;
    }
    sender.sendMessage(remaining
      ? `§e[Cursed Contraptions] Added ${added} device(s); inventory space ran out.`
      : "§a[Cursed Contraptions] All five devices were added.");
  } catch (error) {
    sender.sendMessage(`§c[Cursed Contraptions] ${error.message || error}`);
  }
}

function listAdminDevices(sender) {
  // One message per entry: a single concatenated chat string is truncated by
  // the client once it exceeds a few hundred characters (audit finding F6).
  sender.sendMessage(`§6[Cursed Contraptions] Total: ${deviceManager.totalCount}, Active: ${deviceManager.activeCount}`);
  for (const device of deviceManager.devices.values()) {
    sender.sendMessage(`  ${device.typeId} — ${device.stateMachine.state} — Durability: ${device.durability}/${device.maxDurability}`);
  }
}

function toggleAdminDebug(sender, message) {
  const argument = String(message || "").trim().toLowerCase();
  if (argument !== "on" && argument !== "off") {
    sender.sendMessage("§e[Cursed Contraptions] Use /scriptevent cc:debug on or /scriptevent cc:debug off.");
    return;
  }
  const enabled = argument === "on";
  CONFIG.debug.enabled = enabled;
  CONFIG.debug.chatDebug = enabled;
  sender.sendMessage(`§${enabled ? "a" : "c"}[Cursed Contraptions] Debug ${enabled ? "enabled" : "disabled"}.`);
}

subscribeSafely("admin commands", () => {
  system.afterEvents.scriptEventReceive.subscribe(handleAdminScriptEvent, { namespaces: ["cc"] });
});
