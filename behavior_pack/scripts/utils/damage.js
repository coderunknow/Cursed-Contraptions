/**
 * Cursed Contraptions — Damage Utilities
 */

/** Supports both the 1.x method form and the 2.x property form of isValid. */
export function isEntityValid(entity) {
  if (!entity) return false;

  try {
    return typeof entity.isValid === "function"
      ? entity.isValid()
      : entity.isValid === true;
  } catch (_) {
    return false;
  }
}

/** Apply damage through Minecraft's entity API; return whether it succeeded. */
export function applyDamage(entity, amount, cause = "contact") {
  if (!isEntityValid(entity) || !Number.isFinite(amount) || amount <= 0) return false;

  try {
    return entity.applyDamage(amount, { cause }) !== false;
  } catch (_) {
    return false;
  }
}

/** Return an inclusive integer in [min, max]. */
export function randomDamage(min, max, random = Math.random) {
  const lower = Math.ceil(Number(min));
  const upper = Math.floor(Number(max));
  if (!Number.isFinite(lower) || !Number.isFinite(upper) || lower > upper) {
    throw new RangeError("Damage range must contain at least one finite integer");
  }

  const roll = Number(random());
  if (!Number.isFinite(roll)) throw new TypeError("Random source must return a finite number");
  const boundedRoll = Math.min(Math.max(roll, 0), 1 - Number.EPSILON);
  return Math.floor(boundedRoll * (upper - lower + 1)) + lower;
}

/** Roll a probability in the inclusive range [0, 1]. */
export function rollExtremeDamage(chance, random = Math.random) {
  const probability = Number(chance);
  if (!Number.isFinite(probability)) return false;
  if (probability <= 0) return false;
  if (probability >= 1) return true;
  return Number(random()) < probability;
}
