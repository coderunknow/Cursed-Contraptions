/**
 * Cursed Contraptions — Voluntary immunity
 *
 * A player can spend one soul shard (sneak + use any device) to become
 * uncapturable for a few minutes. The immunity is a tag plus an expiry tick, so
 * it survives a relog and cannot be forgotten by a device that despawned.
 */

import { system } from "@minecraft/server";
import { CONFIG } from "../config.js";
import { isEntityValid } from "./damage.js";

export const IMMUNITY_TAG = "cc:immune";
const IMMUNITY_UNTIL_PROPERTY = "cc:immune_until";

/** True while the player is immune; clears an expired immunity on the way out. */
export function isImmune(entity) {
  if (!isEntityValid(entity) || entity.typeId !== "minecraft:player") return false;

  let tagged = false;
  try {
    tagged = entity.hasTag(IMMUNITY_TAG);
  } catch (_) {
    return false;
  }
  if (!tagged) return false;

  let expiry = NaN;
  try {
    expiry = Number(entity.getDynamicProperty(IMMUNITY_UNTIL_PROPERTY));
  } catch (_) {
    expiry = NaN;
  }

  const now = system.currentTick;
  if (Number.isFinite(expiry) && Number.isFinite(now) && now >= expiry) {
    clearImmunity(entity);
    return false;
  }
  return true;
}

/**
 * Grant immunity for ``ticks`` (defaults to the configured shard duration).
 * @returns {boolean} Whether the tag stuck.
 */
export function grantImmunity(entity, ticks = CONFIG.souls.immunityTicks) {
  if (!isEntityValid(entity) || entity.typeId !== "minecraft:player") return false;

  const now = system.currentTick;
  const duration = Math.max(1, Math.floor(Number(ticks) || CONFIG.souls.immunityTicks));
  try {
    entity.addTag(IMMUNITY_TAG);
    entity.setDynamicProperty(
      IMMUNITY_UNTIL_PROPERTY,
      Number.isFinite(now) ? now + duration : duration,
    );
    return true;
  } catch (_) {
    return false;
  }
}

export function clearImmunity(entity) {
  if (!isEntityValid(entity)) return;
  try {
    entity.removeTag(IMMUNITY_TAG);
  } catch (_) {
    // Tags can be unavailable on a shutting-down entity; the property still goes.
  }
  try {
    entity.setDynamicProperty(IMMUNITY_UNTIL_PROPERTY, undefined);
  } catch (_) {
    // Ignore: nothing else can be done for a stale property.
  }
}

/** Whole seconds left, or 0 when not immune. Used by the HUD. */
export function immunitySecondsLeft(entity) {
  if (!isImmune(entity)) return 0;
  let expiry = NaN;
  try {
    expiry = Number(entity.getDynamicProperty(IMMUNITY_UNTIL_PROPERTY));
  } catch (_) {
    return 0;
  }
  const now = system.currentTick;
  if (!Number.isFinite(expiry) || !Number.isFinite(now)) return 0;
  return Math.max(0, Math.ceil((expiry - now) / 20));
}
