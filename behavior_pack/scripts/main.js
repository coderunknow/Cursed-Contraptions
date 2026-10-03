/**
 * Cursed Contraptions — Main Entry Point
 * 
 * Initializes the add-on, registers event handlers, and starts
 * the device manager. This is the entry point specified in manifest.json.
 */

import {
  world,
  system,
  ItemStack,
  EntityDamageCause,
} from "@minecraft/server";
import { deviceManager } from "./devices/device-manager.js";
import { CONFIG } from "./config.js";
import { Debug } from "./utils/debug.js";
import { DeviceState } from "./utils/state-machine.js";

// ── Device type registry ──
const BLOCK_TO_ENTITY = {
  "cc:iron_maiden_block":      "cc:iron_maiden",
  "cc:cursed_stocks_block":    "cc:cursed_stocks",
  "cc:gravebinder_cage_block": "cc:gravebinder_cage",
  "cc:regret_rack_block":      "cc:regret_rack",
  "cc:black_reliquary_block":  "cc:black_reliquary",
};

const ENTITY_TYPES = new Set(Object.values(BLOCK_TO_ENTITY));
const ALL_DEVICE_ENTITY_TYPES = Object.values(BLOCK_TO_ENTITY);

// ── Initialization ──
system.run(() => {
  Debug.info("Main", "Cursed Contraptions initializing...");
  deviceManager.start();
  deviceManager.discoverAll();
  Debug.info("Main", `Initialization complete. ${deviceManager.totalCount} devices loaded.`);
});

// ── Block placement → Spawn device entity ──
world.afterEvents.playerPlaceBlock.subscribe((event) => {
  const block = event.block;
  const blockTypeId = block.typeId;
  const entityTypeId = BLOCK_TO_ENTITY[blockTypeId];
  
  if (!entityTypeId) return;

  system.run(() => {
    try {
      const dim = event.player.dimension;
      const pos = block.location;
      
      // Spawn the device entity at the block location
      const entity = dim.spawnEntity(entityTypeId, {
        x: pos.x + 0.5,
        y: pos.y,
        z: pos.z + 0.5,
      });

      // Remove the anchor block — entity is the persistent object
      try {
        dim.setBlockType(pos, "minecraft:air");
      } catch (_) {}

      const device = deviceManager.register(entity);
      if (device) {
        Debug.info("Main", `Placed ${entityTypeId} at ${pos.x}, ${pos.y}, ${pos.z}`);
      }
    } catch (err) {
      Debug.error("Main", "Failed to spawn device entity", err);
    }
  });
});

// ── Entity interact → Rescue / Armor ──
// Use both possible event names for compatibility
function handleInteract(player, target) {
  if (!target || !ENTITY_TYPES.has(target.typeId)) return;

  const device = deviceManager.getDevice(target);
  if (!device) return;

  // Get held item
  let heldItem = null;
  try {
    const inv = player.getComponent("minecraft:inventory");
    if (inv && inv.container) {
      heldItem = inv.container.getItem(player.selectedSlotIndex);
    }
  } catch (_) {}

  device.onInteract(player, heldItem);
}

// Try the newer API first, fall back to older
try {
  world.afterEvents.playerInteractWithEntity?.subscribe?.((event) => {
    system.run(() => handleInteract(event.player, event.target));
  });
} catch (_) {}

// Also subscribe to entity hit for rescue mechanic
world.afterEvents.entityHurt.subscribe((event) => {
  const hurtEntity = event.hurtEntity;
  if (!hurtEntity) return;

  // Device entity hurt → apply durability damage
  if (ENTITY_TYPES.has(hurtEntity.typeId)) {
    const device = deviceManager.getDevice(hurtEntity);
    if (device) {
      const damage = event.damage;
      if (damage > 0) {
        device.takeDamage(Math.ceil(damage / 2));
      }
    }
    return;
  }

  // Victim died while trapped → release
  try {
    if (hurtEntity.hasTag("cc:trapped")) {
      const health = hurtEntity.getComponent("minecraft:health");
      if (health && health.currentValue <= 0) {
        try { hurtEntity.removeTag("cc:trapped"); } catch (_) {}
        for (const [_, device] of deviceManager.devices) {
          if (String(device.victimId) === String(hurtEntity.id)) {
            device.victimId = null;
            device.release();
            break;
          }
        }
      }
    }
  } catch (_) {}
});

// ── Entity death → Cleanup ──
world.afterEvents.entityDie?.subscribe?.((event) => {
  const deadEntity = event.deadEntity;
  if (!deadEntity) return;

  // Device entity died
  if (ENTITY_TYPES.has(deadEntity.typeId)) {
    const device = deviceManager.getDevice(deadEntity);
    if (device) {
      device.dispose();
      deviceManager.unregister(deadEntity.id);
    }
    return;
  }

  // Victim died while trapped
  try {
    if (deadEntity.hasTag("cc:trapped")) {
      try { deadEntity.removeTag("cc:trapped"); } catch (_) {}
      for (const [_, device] of deviceManager.devices) {
        if (String(device.victimId) === String(deadEntity.id)) {
          device.victimId = null;
          device.release();
          break;
        }
      }
    }
  } catch (_) {}
});

// ── Entity load → Register if device ──
world.afterEvents.entityLoad.subscribe((event) => {
  const entity = event.entity;
  if (!entity || !ENTITY_TYPES.has(entity.typeId)) return;

  system.runTimeout(() => {
    if (entity.isValid()) {
      deviceManager.register(entity);
    }
  }, CONFIG.performance.chunkLoadGracePeriod);
});

// ── Player leave → Release from devices ──
world.afterEvents.playerLeave.subscribe((event) => {
  for (const [_, device] of deviceManager.devices) {
    if (device.victimId) {
      const victim = device._getVictim();
      if (!victim) {
        device.victimId = null;
        device.release();
      }
    }
  }
});

// ── Redstone detection via periodic check ──
// Check if devices near redstone power sources are being powered
system.runInterval(() => {
  for (const [_, device] of deviceManager.devices) {
    if (device._disposed || !device._entityValid()) continue;
    
    const pos = device.position;
    if (!pos) continue;

    try {
      // Check adjacent blocks for redstone signal
      const dim = device.entity.dimension;
      const offsets = [
        { x: 1, y: 0, z: 0 },
        { x: -1, y: 0, z: 0 },
        { x: 0, y: 1, z: 0 },
        { x: 0, y: -1, z: 0 },
        { x: 0, y: 0, z: 1 },
        { x: 0, y: 0, z: -1 },
      ];

      let powered = false;
      for (const off of offsets) {
        const block = dim.getBlock({
          x: Math.floor(pos.x) + off.x,
          y: Math.floor(pos.y) + off.y,
          z: Math.floor(pos.z) + off.z,
        });
        if (block && block.getRedstonePower() > 0) {
          powered = true;
          break;
        }
      }

      device.onRedstonePower(powered);
    } catch (_) {}
  }
}, 10); // Check every 0.5 seconds — not every tick

// ── Chat commands for debug ──
world.beforeEvents.chatSend.subscribe((event) => {
  const msg = event.message;
  
  if (msg === "!cc devices") {
    event.cancel = true;
    system.run(() => {
      const info = [
        `§6[Cursed Contraptions]`,
        `Total: ${deviceManager.totalCount}, Active: ${deviceManager.activeCount}`,
      ];
      for (const [eid, device] of deviceManager.devices) {
        info.push(`  ${device.typeId} — ${device.stateMachine.state} — HP: ${device.durability}/${device.maxDurability}`);
      }
      event.sender.sendMessage(info.join("\n"));
    });
  }
  
  if (msg === "!cc debug on") {
    event.cancel = true;
    CONFIG.debug.enabled = true;
    CONFIG.debug.chatDebug = true;
    system.run(() => event.sender.sendMessage("§a[Cursed Contraptions] Debug mode enabled"));
  }
  
  if (msg === "!cc debug off") {
    event.cancel = true;
    CONFIG.debug.enabled = false;
    CONFIG.debug.chatDebug = false;
    system.run(() => event.sender.sendMessage("§c[Cursed Contraptions] Debug mode disabled"));
  }

  if (msg === "!cc give") {
    event.cancel = true;
    system.run(() => {
      const player = event.sender;
      try {
        const inv = player.getComponent("minecraft:inventory");
        if (inv && inv.container) {
          for (const itemId of [
            "cc:item_iron_maiden",
            "cc:item_cursed_stocks", 
            "cc:item_gravebinder_cage",
            "cc:item_regret_rack",
            "cc:item_black_reliquary",
          ]) {
            const item = new ItemStack(itemId, 1);
            inv.container.addItem(item);
          }
          player.sendMessage("§a[Cursed Contraptions] All devices added to inventory");
        }
      } catch (err) {
        player.sendMessage(`§c[Cursed Contraptions] Error: ${err.message || err}`);
      }
    });
  }
});

// ── Periodic fail-safe cleanup ──
system.runInterval(() => {
  // Clean up any orphaned device references
  const toRemove = [];
  for (const [eid, device] of deviceManager.devices) {
    if (!device._entityValid()) {
      toRemove.push(eid);
    }
  }
  for (const eid of toRemove) {
    deviceManager.unregister(eid);
  }

  // Clean orphaned "cc:trapped" tags on entities not held by any device
  // (This is expensive, so only do it rarely)
  try {
    const dim = world.getDimension("minecraft:overworld");
    const trapped = dim.getEntities({ tags: ["cc:trapped"] });
    for (const entity of trapped) {
      let held = false;
      for (const [_, device] of deviceManager.devices) {
        if (String(device.victimId) === String(entity.id)) {
          held = true;
          break;
        }
      }
      if (!held) {
        try { entity.removeTag("cc:trapped"); } catch (_) {}
      }
    }
  } catch (_) {}
}, 200); // Every 10 seconds
