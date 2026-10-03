/**
 * Cursed Contraptions — The Black Reliquary
 * Endgame fantasy device. Visually elaborate, rarer, stronger effects.
 */
import { TortureDevice } from "./device-base.js";
import { CONFIG } from "../config.js";

export class BlackReliquary extends TortureDevice {
  constructor(entity) {
    super("cc:black_reliquary", CONFIG.blackReliquary, entity);
  }
}
