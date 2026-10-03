/**
 * Cursed Contraptions — Persistence Utilities
 * 
 * Handles reading/writing device state to entity dynamic properties
 * so state survives chunk unload/reload and server restarts.
 */

import { Entity } from "@minecraft/server";

const PROP_PREFIX = "cc:";

export function setStringProp(entity, key, value) {
  try {
    entity.setProperty(`${PROP_PREFIX}${key}`, String(value));
  } catch (_) {}
}

export function getStringProp(entity, key, defaultValue = "") {
  try {
    const v = entity.getProperty(`${PROP_PREFIX}${key}`);
    return v !== undefined && v !== null ? String(v) : defaultValue;
  } catch (_) {
    return defaultValue;
  }
}

export function setIntProp(entity, key, value) {
  try {
    entity.setProperty(`${PROP_PREFIX}${key}`, Math.floor(value));
  } catch (_) {}
}

export function getIntProp(entity, key, defaultValue = 0) {
  try {
    const v = entity.getProperty(`${PROP_PREFIX}${key}`);
    return v !== undefined && v !== null ? Math.floor(v) : defaultValue;
  } catch (_) {
    return defaultValue;
  }
}

export function setBoolProp(entity, key, value) {
  try {
    entity.setProperty(`${PROP_PREFIX}${key}`, value ? 1 : 0);
  } catch (_) {}
}

export function getBoolProp(entity, key, defaultValue = false) {
  try {
    const v = entity.getProperty(`${PROP_PREFIX}${key}`);
    return v !== undefined && v !== null ? v === 1 : defaultValue;
  } catch (_) {
    return defaultValue;
  }
}
