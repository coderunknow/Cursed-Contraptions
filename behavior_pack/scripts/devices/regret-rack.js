/**
 * Cursed Contraptions — The Regret Rack
 * Dramatic mechanical stretching device. Higher durability, longer cycle.
 */
import { TortureDevice } from "./device-base.js";
import { CONFIG } from "../config.js";

export class RegretRack extends TortureDevice {
  constructor(entity) {
    super("cc:regret_rack", CONFIG.regretRack, entity);
  }
}
