/**
 * Cursed Contraptions — Gravebinder Cage
 * Fantasy-styled cage. Horror-oriented visual effects.
 */
import { TortureDevice } from "./device-base.js";
import { CONFIG } from "../config.js";

export class GravebinderCage extends TortureDevice {
  constructor(entity) {
    super("cc:gravebinder_cage", CONFIG.gravebinderCage, entity);
  }
}
