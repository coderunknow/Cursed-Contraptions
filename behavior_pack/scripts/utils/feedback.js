/**
 * Cursed Contraptions — Sound and status feedback
 *
 * Every cue is a vanilla sound id, so no extra resource-pack assets are needed
 * and nothing breaks if a platform is missing an id: playback is wrapped.
 */

import { CONFIG } from "../config.js";
import { isEntityValid } from "./damage.js";

/** Play a device cue at a position. Unknown cues are ignored. */
export function playCue(dimension, location, cue, config, overrides = {}) {
  if (!CONFIG.sounds.enabled || !dimension || !location) return;

  const profile = CONFIG.sounds.profiles[config?.soundProfile] ?? CONFIG.sounds.profiles.metal;
  let soundId = null;
  let pitch = overrides.pitch ?? (profile.pitch ?? 1) * (config?.soundPitch ?? 1);

  switch (cue) {
    case "slam":
      soundId = profile.slam;
      break;
    case "hit":
      soundId = profile.hit;
      break;
    case "latch":
      soundId = CONFIG.sounds.latch;
      break;
    case "release":
    case "rescue":
      soundId = CONFIG.sounds.release;
      break;
    case "reinforce":
    case "repair":
      soundId = CONFIG.sounds.reinforce;
      break;
    case "soul":
      soundId = CONFIG.sounds.soul;
      break;
    case "surge":
      soundId = CONFIG.sounds.surge;
      pitch *= 1.1;
      break;
    case "break":
      soundId = CONFIG.sounds.break;
      pitch *= 0.75;
      break;
    case "capture":
      soundId = CONFIG.sounds.capture;
      pitch *= 1.2;
      break;
    default:
      soundId = null;
  }
  if (!soundId) return;

  try {
    dimension.playSound(soundId, location, {
      pitch: Math.max(0.3, Math.min(2.0, pitch)),
      volume: overrides.volume ?? 1,
    });
  } catch (_) {
    // Audio is decoration; never let a missing sound id break gameplay.
  }
}

/**
 * Send (or refresh) the action-bar status of a captured player.
 * @param {import("@minecraft/server").Player} player
 * @param {string} message
 */
export function showStatus(player, message) {
  if (!CONFIG.hud.enabled || !isEntityValid(player) || player.typeId !== "minecraft:player") return;
  try {
    player.onScreenDisplay.setActionBar(message);
  } catch (_) {
    // Older builds without onScreenDisplay simply get the chat message instead.
  }
}
