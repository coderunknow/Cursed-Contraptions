/**
 * Cursed Contraptions — Cursed Stocks
 * Low-tech medieval restraint. Short capture range, lower damage, high comedy.
 */
import { TortureDevice } from "./device-base.js";
import { CONFIG } from "../config.js";

export class CursedStocks extends TortureDevice {
  constructor(entity) {
    super("cc:cursed_stocks", CONFIG.cursedStocks, entity);
  }
}
