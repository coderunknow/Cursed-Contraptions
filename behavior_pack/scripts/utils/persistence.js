/**
 * Cursed Contraptions — Persistence Utilities
 *
 * Gameplay state is stored as entity dynamic properties. Legacy entity
 * properties remain readable as migration fallbacks for existing worlds.
 */

const DYNAMIC_PREFIX = "cc:device_";
const LEGACY_ENTITY_PROPERTIES = Object.freeze({
  state: "cc:state",
  durability: "cc:durability",
  armor_count: "cc:armor_count",
});

function readDynamic(entity, key) {
  try {
    return entity.getDynamicProperty(`${DYNAMIC_PREFIX}${key}`);
  } catch (_) {
    return undefined;
  }
}

function readLegacy(entity, key) {
  const propertyId = LEGACY_ENTITY_PROPERTIES[key];
  if (!propertyId) return undefined;

  try {
    return entity.getProperty(propertyId);
  } catch (_) {
    return undefined;
  }
}

function readValue(entity, key) {
  const value = readDynamic(entity, key);
  return value === undefined || value === null ? readLegacy(entity, key) : value;
}

function writeValue(entity, key, value) {
  try {
    entity.setDynamicProperty(`${DYNAMIC_PREFIX}${key}`, value);
    return true;
  } catch (_) {
    return false;
  }
}

export function setStringProp(entity, key, value) {
  return writeValue(entity, key, String(value));
}

export function getStringProp(entity, key, defaultValue = "") {
  const value = readValue(entity, key);
  return value === undefined || value === null ? defaultValue : String(value);
}

export function setIntProp(entity, key, value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return false;
  return writeValue(entity, key, Math.floor(number));
}

export function getIntProp(entity, key, defaultValue = 0) {
  const number = Number(readValue(entity, key));
  return Number.isFinite(number) ? Math.floor(number) : defaultValue;
}

export function setBoolProp(entity, key, value) {
  return writeValue(entity, key, Boolean(value));
}

export function getBoolProp(entity, key, defaultValue = false) {
  const value = readValue(entity, key);
  return typeof value === "boolean" ? value : defaultValue;
}

export function clearProp(entity, key) {
  try {
    entity.setDynamicProperty(`${DYNAMIC_PREFIX}${key}`, undefined);
    return true;
  } catch (_) {
    return false;
  }
}
