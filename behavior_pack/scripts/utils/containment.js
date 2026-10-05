/**
 * Cursed Contraptions — Captive anchoring
 *
 * Keeps a captive inside its device without the tug-of-war that made earlier
 * versions stutter, and without ever letting a captive be damaged while it is
 * outside. The stock entity API cannot force a mob to stand still, so the hold
 * is a short control loop that runs once per device tick:
 *
 * 1. drop the velocity a mob accumulated from knockback, water or iron bars
 *    (mobs only — clearing a player's velocity every tick would fight their own
 *    input once they are freed),
 * 2. apply a small impulse toward the seat, capped by ``maxAnchorSpeed``,
 * 3. teleport back only when the captive is genuinely out of the seat window
 *    and never more than once per ``correctionCooldownTicks``.
 */

import { CONFIG } from "../config.js";
import { isEntityValid } from "./damage.js";

/**
 * @param {import("@minecraft/server").Entity} entity Captive to hold.
 * @param {{x: number, y: number, z: number}} anchor Seat position.
 * @param {{ radius?: number, snap?: boolean }} [options] ``snap`` allows the
 *   correction teleport (false while a captive is still inside the window).
 * @returns {"held" | "snapped" | "invalid" | "unavailable"} What the hold did.
 */
export function anchorEntity(entity, anchor, options = {}) {
  if (!isEntityValid(entity) || !anchor) return "invalid";

  const position = readLocation(entity);
  if (!position) return "unavailable";

  const dx = anchor.x - position.x;
  const dz = anchor.z - position.z;
  const distance = Math.hypot(dx, dz);

  if (entity.typeId !== "minecraft:player") {
    try {
      entity.clearVelocity();
    } catch (_) {
      // Some entities cannot report velocity; the impulse below still applies.
    }
  }

  const maxSpeed = CONFIG.containment.maxAnchorSpeed;
  if (distance > 0.02) {
    const scale = Math.min(maxSpeed, distance * 0.5) / distance;
    try {
      entity.applyImpulse({ x: dx * scale, y: 0, z: dz * scale });
    } catch (_) {
      // Impulses are a convenience: the teleport correction below is the
      // authoritative fallback when an entity rejects them.
    }
  }

  if (options.snap && distance > (options.radius ?? CONFIG.containment.snapDistance)) {
    try {
      const dimension = entity.dimension;
      entity.teleport({ x: anchor.x, y: anchor.y, z: anchor.z }, { dimension, keepVelocity: false });
      return "snapped";
    } catch (_) {
      return "held";
    }
  }

  return "held";
}

/** Stop a captive dead in its tracks (used on release so it does not skate away). */
export function stopMotion(entity) {
  if (!isEntityValid(entity)) return;
  try {
    entity.clearVelocity();
  } catch (_) {
    // Players reject clearVelocity in some builds; they are freed anyway.
  }
}

function readLocation(entity) {
  try {
    const location = entity.location;
    if (!Number.isFinite(location?.x) || !Number.isFinite(location?.y)) return null;
    return location;
  } catch (_) {
    return null;
  }
}

/** Squared distance between two positions, or Infinity when either is unusable. */
export function distanceSquared(first, second) {
  if (!first || !second) return Infinity;
  const dx = first.x - second.x;
  const dy = first.y - second.y;
  const dz = first.z - second.z;
  return dx * dx + dy * dy + dz * dz;
}
