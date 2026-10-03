/**
 * Cursed Contraptions — Iron Maiden
 * The flagship torture device. A stylized medieval iron cabinet.
 */
import { TortureDevice } from "./device-base.js";
import { CONFIG } from "../config.js";

export class IronMaiden extends TortureDevice {
  constructor(entity) {
    super("cc:iron_maiden", CONFIG.ironMaiden, entity);
  }
}
