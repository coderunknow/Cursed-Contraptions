/**
 * Cursed Contraptions — Damage Utilities
 * 
 * Proper entity damage through Minecraft's health system.
 * No arbitrary instant-death commands.
 */

import { EntityDamageCause, Entity } from "@minecraft/server";

/**
 * Apply damage to an entity using the proper damage API.
 * Returns true if damage was applied.
 */
export function applyDamage(entity, amount, cause = EntityDamageCause.contact) {
  if (!entity || !entity.isValid()) return false;
  
  try {
    // Use the applyDamage method which respects armor, absorption, etc.
    entity.applyDamage(amount, {
      cause: cause,
    });
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Generate a random damage value within a range.
 */
export function randomDamage(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Roll for extreme damage event.
 */
export function rollExtremeDamage(chance) {
  return Math.random() < chance;
}
