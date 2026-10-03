/**
 * Cursed Contraptions — Torture Device Base Class
 * 
 * Reusable abstract base for all torture contraptions.
 * A new device needs only:
 *   1. Device definition (typeId, config)
 *   2. Model/animation references
 *   3. Interaction rules (optional overrides)
 * 
 * This class manages:
 *   - State machine
 *   - Capture logic
 *   - Torture cycle
 *   - Damage + healing
 *   - Durability + armor
 *   - Rescue/escape
 *   - Redstone activation
 *   - Cleanup on destruction
 *   - Persistence
 */

import {
  world,
  system,
  EntityDamageCause,
  EffectTypes,
  MinecraftDimensionTypes,
  GameMode,
  BlockPermutation,
  ItemStack,
} from "@minecraft/server";
import { StateMachine, DeviceState } from "../utils/state-machine.js";
import { Debug } from "../utils/debug.js";
import {
  setStringProp, getStringProp,
  setIntProp, getIntProp,
  setBoolProp, getBoolProp,
} from "../utils/persistence.js";
import { CONFIG } from "../config.js";

export class TortureDevice {
  /**
   * @param {string} typeId - Entity identifier, e.g. "cc:iron_maiden"
   * @param {object} config - Device-specific config block (from CONFIG)
   * @param {Entity} entity - The Bedrock entity instance
   */
  constructor(typeId, config, entity) {
    this.typeId = typeId;
    this.config = config;
    this.entity = entity;
    this.stateMachine = new StateMachine(DeviceState.IDLE);
    this.victimId = null;       // Runtime only — victim runtimeId
    this._captureTimer = null;
    this._tortureTimer = null;
    this._ambientTimer = null;
    this._redstonePowered = false;
    this._disposed = false;

    // Restore persisted state
    this._loadState();

    // Register state-transition side effects
    this._registerTransitions();
  }

  // ── Public getters ──

  get position() {
    try {
      return this.entity.location;
    } catch (_) {
      return null;
    }
  }

  get durability() {
    return getIntProp(this.entity, "durability", this.config.baseDurability);
  }

  set durability(v) {
    setIntProp(this.entity, "durability", v);
  }

  get maxDurability() {
    const base = this.config.baseDurability;
    const armor = this.armorCount;
    return base + armor * this.config.armorDurabilityBonus;
  }

  get armorCount() {
    return getIntProp(this.entity, "armorCount", 0);
  }

  set armorCount(v) {
    setIntProp(this.entity, "armorCount", Math.min(v, this.config.armorSlots));
  }

  // ── State persistence ──

  _loadState() {
    const saved = getStringProp(this.entity, "state", DeviceState.IDLE);
    this.stateMachine = StateMachine.deserialize(saved);
    const dur = getIntProp(this.entity, "durability", -1);
    if (dur < 0) {
      // First time — initialize
      this.durability = this.config.baseDurability;
      this.armorCount = 0;
    }
    // If we were in an active state on reload, recover gracefully
    if (this.stateMachine.is(
      DeviceState.CAPTURING,
      DeviceState.CLOSED,
      DeviceState.TORTURING
    )) {
      // Check if victim still exists
      const victimIdStr = getStringProp(this.entity, "victimId", "");
      if (victimIdStr) {
        this.victimId = victimIdStr;
        // Verify victim is still valid and nearby
        if (!this._getVictim()) {
          this.victimId = null;
          setStringProp(this.entity, "victimId", "");
          this.stateMachine.forceState(DeviceState.IDLE);
        } else {
          // Resume torture cycle
          this._startTortureCycle();
        }
      } else {
        this.stateMachine.forceState(DeviceState.IDLE);
      }
    }
    this._saveState();
  }

  _saveState() {
    if (this._disposed) return;
    try {
      setStringProp(this.entity, "state", this.stateMachine.state);
    } catch (_) {}
  }

  // ── State transitions ──

  _registerTransitions() {
    this.stateMachine.onTransition(DeviceState.IDLE, (_, to) => {
      if (to === DeviceState.DETECTING) this._onDetecting();
    });
    this.stateMachine.onTransition(DeviceState.DETECTING, (_, to) => {
      if (to === DeviceState.CAPTURING) this._onCapturing();
      if (to === DeviceState.IDLE) this._cancelCapture();
    });
    this.stateMachine.onTransition(DeviceState.CAPTURING, (_, to) => {
      if (to === DeviceState.CLOSED) this._onClosed();
    });
    this.stateMachine.onTransition(DeviceState.CLOSED, (_, to) => {
      if (to === DeviceState.TORTURING) this._onTorturing();
      if (to === DeviceState.OPENING) this._onOpening();
    });
    this.stateMachine.onTransition(DeviceState.TORTURING, (_, to) => {
      if (to === DeviceState.OPENING) this._onOpening();
    });
    this.stateMachine.onTransition(DeviceState.OPENING, (_, to) => {
      if (to === DeviceState.RELEASED) this._onReleased();
    });
    this.stateMachine.onTransition(DeviceState.RELEASED, (_, to) => {
      if (to === DeviceState.IDLE) this._onIdle();
    });
    // Any transition to BROKEN
    for (const from of Object.values(DeviceState)) {
      this.stateMachine.onTransition(from, (_, to) => {
        if (to === DeviceState.BROKEN) this._onBroken();
      });
    }
  }

  // ── Core logic ──

  /**
   * Called every tick by the device manager for active devices.
   * Handles detection of nearby entities when in IDLE state.
   */
  tick() {
    if (this._disposed) return;
    if (!this._entityValid()) {
      this.dispose();
      return;
    }

    switch (this.stateMachine.state) {
      case DeviceState.IDLE:
        this._tryDetect();
        break;
      case DeviceState.DETECTING:
        // Waiting for capture delay — handled by timer
        break;
      case DeviceState.CAPTURING:
        // Waiting for close animation — handled by timer
        break;
      case DeviceState.TORTURING:
        // Handled by torture timer
        break;
      case DeviceState.OPENING:
        // Handled by timer
        break;
      case DeviceState.BROKEN:
        // Nothing to do
        break;
    }
  }

  _entityValid() {
    try {
      return this.entity && this.entity.isValid();
    } catch (_) {
      return false;
    }
  }

  _tryDetect() {
    if (!this._entityValid()) return;
    const pos = this.position;
    if (!pos) return;

    const dim = this.entity.dimension;
    let targets;
    try {
      targets = dim.getEntities({
        location: pos,
        maxDistance: this.config.captureRadius,
        families: ["player", "mob"],
        excludeTypes: ["item", "xp_orb", "arrow", "experience_bottle"],
      });
    } catch (_) {
      return;
    }

    for (const target of targets) {
      if (this._isCapturable(target)) {
        this._beginCapture(target);
        return;
      }
    }
  }

  _isCapturable(entity) {
    try {
      if (!entity || !entity.isValid()) return false;
      // Must be a living entity with health
      const health = entity.getComponent("minecraft:health");
      if (!health) return false;
      if (health.currentValue <= 0) return false;
      // Players in creative/spectator are immune
      if (entity.typeId === "minecraft:player") {
        try {
          const gm = entity.getGameMode();
          if (gm === GameMode.creative || gm === GameMode.spectator) return false;
        } catch (_) {}
      }
      // Don't re-capture the same entity already in another device
      if (entity.hasTag("cc:trapped")) return false;
      return true;
    } catch (_) {
      return false;
    }
  }

  _beginCapture(target) {
    if (!this.stateMachine.transition(DeviceState.DETECTING)) return;
    this._saveState();
    Debug.info(this.typeId, `Detected entity ${target.typeId}, beginning capture sequence`);

    // Set detecting animation state
    this._setAnimationState("detecting");

    // Start capture delay timer
    this._captureTimer = system.runTimeout(() => {
      this._captureTimer = null;
      if (this.stateMachine.state !== DeviceState.DETECTING) return;
      if (!this._entityValid()) return;
      if (!target || !target.isValid()) {
        this.stateMachine.transition(DeviceState.IDLE);
        this._saveState();
        return;
      }
      this._executeCapture(target);
    }, this.config.captureDelay);
  }

  _executeCapture(target) {
    if (!this.stateMachine.transition(DeviceState.CAPTURING)) return;
    this.victimId = target.id;
    setStringProp(this.entity, "victimId", String(target.id));
    this._saveState();

    // Tag the victim so other devices don't grab them
    try { target.addTag("cc:trapped"); } catch (_) {}

    // Teleport victim to device center
    const pos = this.position;
    if (pos) {
      try {
        target.teleport(pos, { dimension: this.entity.dimension });
      } catch (_) {}
    }

    // Apply weakness to victim
    this._applyDebuff(target);

    // Set capturing animation state
    this._setAnimationState("capturing");

    // After close duration, transition to CLOSED
    this._captureTimer = system.runTimeout(() => {
      this._captureTimer = null;
      if (this.stateMachine.state !== DeviceState.CAPTURING) return;
      this.stateMachine.transition(DeviceState.CLOSED);
      this._saveState();
    }, this.config.closeDuration);
  }

  _cancelCapture() {
    if (this._captureTimer) {
      try { system.clearRun(this._captureTimer); } catch (_) {}
      this._captureTimer = null;
    }
    this._setAnimationState("idle");
  }

  _onDetecting() {
    // Animation handled in _beginCapture
  }

  _onCapturing() {
    // Animation handled in _executeCapture
  }

  _onClosed() {
    Debug.info(this.typeId, "Doors closed, beginning torture");
    this._setAnimationState("closed");
    // Transition to torturing after a brief dramatic pause
    system.runTimeout(() => {
      if (this.stateMachine.state === DeviceState.CLOSED) {
        this.stateMachine.transition(DeviceState.TORTURING);
        this._saveState();
      }
    }, 10);
  }

  _onTorturing() {
    this._setAnimationState("torturing");
    this._startTortureCycle();
  }

  _startTortureCycle() {
    if (this._tortureTimer) {
      try { system.clearRun(this._tortureTimer); } catch (_) {}
    }
    this._scheduleNextDamage();
  }

  _scheduleNextDamage() {
    if (this._disposed) return;
    if (!this.stateMachine.is(DeviceState.TORTURING, DeviceState.CLOSED)) return;

    // Calculate cycle time (affected by armor)
    const cycleTime = Math.floor(
      this.config.tortureInterval * Math.pow(this.config.armorSpeedMultiplier, this.armorCount)
    );

    this._tortureTimer = system.runTimeout(() => {
      this._tortureTimer = null;
      if (this._disposed) return;
      if (!this.stateMachine.is(DeviceState.TORTURING)) return;
      if (!this._entityValid()) return;

      this._performDamageCycle();
    }, Math.max(cycleTime, 10));
  }

  _performDamageCycle() {
    const victim = this._getVictim();
    if (!victim) {
      // Victim died or escaped — release
      this.release();
      return;
    }

    // Calculate damage
    const armorDmgMult = Math.pow(this.config.armorDamageMultiplier, this.armorCount);
    let damage;
    if (Math.random() < this.config.extremeDamageChance) {
      damage = Math.floor(this.config.extremeDamageAmount * armorDmgMult);
      Debug.info(this.typeId, `EXTREME DAMAGE: ${damage}`);
      this._spawnParticles("extreme");
    } else {
      const baseDmg = Math.floor(
        (this.config.tortureMinDamage +
          Math.random() * (this.config.tortureMaxDamage - this.config.tortureMinDamage))
        * armorDmgMult
      );
      damage = baseDmg;
      this._spawnParticles("normal");
    }

    // Apply damage via proper entity damage
    try {
      victim.applyDamage(damage, {
        cause: EntityDamageCause.contact,
      });
    } catch (_) {}

    // Apply healing to keep victim alive for prolonged torture
    this._applyHealing(victim);

    // Re-apply debuff
    this._applyDebuff(victim);

    // Consume durability
    this.durability = Math.max(0, this.durability - 1);
    if (this.durability <= 0) {
      this.break();
      return;
    }

    // Apply vignette effect to victim
    this._applyVignette(victim);

    // Schedule next cycle
    this._scheduleNextDamage();
  }

  _onOpening() {
    Debug.info(this.typeId, "Opening device");
    this._stopTorture();
    this._setAnimationState("opening");

    // After opening animation, release
    system.runTimeout(() => {
      if (this.stateMachine.state === DeviceState.OPENING) {
        this.stateMachine.transition(DeviceState.RELEASED);
        this._saveState();
      }
    }, 20);
  }

  _onReleased() {
    Debug.info(this.typeId, "Victim released");
    this._releaseVictim();
    this._setAnimationState("released");

    // Return to idle after a moment
    system.runTimeout(() => {
      if (this.stateMachine.state === DeviceState.RELEASED) {
        this.stateMachine.transition(DeviceState.IDLE);
        this._saveState();
      }
    }, 20);
  }

  _onIdle() {
    this._setAnimationState("idle");
  }

  _onBroken() {
    Debug.info(this.typeId, "Device broken");
    this._stopAll();
    this._releaseVictim();
    this._setAnimationState("broken");

    // Drop item if configured
    if (this.config.dropOnBreak && this._entityValid()) {
      try {
        const pos = this.position;
        if (pos) {
          const item = new ItemStack(this.typeId.replace("cc:", "cc:item_"), 1);
          this.entity.dimension.spawnItem(item, pos);
        }
      } catch (_) {}
    }

    // Remove entity after brief delay for death animation
    system.runTimeout(() => {
      try {
        if (this._entityValid()) {
          this.entity.kill();
        }
      } catch (_) {}
      this.dispose();
    }, 30);
  }

  // ── Victim management ──

  _getVictim() {
    if (!this.victimId) return null;
    if (!this._entityValid()) return null;
    try {
      const entities = this.entity.dimension.getEntities({ location: this.position, maxDistance: 5 });
      for (const e of entities) {
        if (e.id === this.victimId && e.isValid()) return e;
      }
    } catch (_) {}
    // Try by runtime id string
    try {
      const all = this.entity.dimension.getEntities({});
      for (const e of all) {
        if (String(e.id) === String(this.victimId) && e.isValid()) return e;
      }
    } catch (_) {}
    return null;
  }

  _releaseVictim() {
    const victim = this._getVictim();
    if (victim) {
      try { victim.removeTag("cc:trapped"); } catch (_) {}
      try {
        // Clear debuffs
        victim.removeEffect("weakness");
        victim.removeEffect("slowness");
      } catch (_) {}
      // Teleport victim slightly away from device
      const pos = this.position;
      if (pos) {
        try {
          victim.teleport(
            { x: pos.x + 1, y: pos.y, z: pos.z },
            { dimension: this.entity.dimension }
          );
        } catch (_) {}
      }
      // Clear vignette
      this._clearVignette(victim);
    }
    this.victimId = null;
    setStringProp(this.entity, "victimId", "");
  }

  // ── Effects ──

  _applyDebuff(entity) {
    if (!entity || !entity.isValid()) return;
    try {
      if (this.config.weaknessAmplifier >= 0) {
        entity.addEffect("weakness", this.config.weaknessDuration, {
          amplifier: this.config.weaknessAmplifier,
          showParticles: false,
        });
      }
    } catch (_) {}
  }

  _applyHealing(entity) {
    if (!entity || !entity.isValid()) return;
    try {
      entity.addEffect("regeneration", this.config.healDuration, {
        amplifier: this.config.healAmplifier,
        showParticles: false,
      });
    } catch (_) {}
  }

  _applyVignette(entity) {
    if (!CONFIG.vignette.enabled) return;
    if (!entity || !entity.isValid()) return;
    if (entity.typeId !== "minecraft:player") return;
    try {
      // Use blindness briefly as vignette proxy — short duration, subtle
      entity.addEffect("blindness", CONFIG.vignette.fadeInTicks, {
        amplifier: 0,
        showParticles: false,
      });
    } catch (_) {}
  }

  _clearVignette(entity) {
    if (!entity || !entity.isValid()) return;
    try {
      entity.removeEffect("blindness");
    } catch (_) {}
  }

  _spawnParticles(type) {
    if (!this._entityValid()) return;
    const pos = this.position;
    if (!pos) return;

    try {
      const count = type === "extreme"
        ? CONFIG.particles.bloodCount * 2
        : CONFIG.particles.bloodCount;
      for (let i = 0; i < Math.min(count, CONFIG.performance.maxParticlesPerEvent); i++) {
        this.entity.dimension.spawnParticle(
          "minecraft:basic_smoke_particle",
          { x: pos.x + (Math.random() - 0.5), y: pos.y + 1, z: pos.z + (Math.random() - 0.5) }
        );
      }
      // Red particle for blood effect
      if (CONFIG.particles.bloodEnabled) {
        this.entity.dimension.spawnParticle(
          "minecraft:basic_flame_particle",
          { x: pos.x, y: pos.y + 0.5, z: pos.z }
        );
      }
    } catch (_) {}
  }

  // ── Animation state ──

  _setAnimationState(stateName) {
    if (!this._entityValid()) return;
    try {
      // Clear all device-specific animation tags, then set the new one
      const states = ["idle", "detecting", "capturing", "closed", "torturing", "opening", "released", "broken"];
      for (const s of states) {
        try { this.entity.removeTag(`cc:anim_${s}`); } catch (_) {}
      }
      this.entity.addTag(`cc:anim_${stateName}`);
    } catch (_) {}
  }

  // ── Redstone ──

  onRedstonePower(powered) {
    if (this._disposed) return;
    if (powered && !this._redstonePowered) {
      this._redstonePowered = true;
      if (this.stateMachine.state === DeviceState.IDLE) {
        // Trigger activation after delay
        system.runTimeout(() => {
          if (this.stateMachine.state === DeviceState.IDLE) {
            this._tryDetect();
          }
        }, this.config.redstoneActivationDelay);
      }
    } else if (!powered) {
      this._redstonePowered = false;
    }
  }

  // ── External interaction (rescue, armor) ──

  onInteract(player, heldItem) {
    if (this._disposed) return;

    // Check if player is holding armor to reinforce
    if (heldItem && this._isArmorItem(heldItem.typeId)) {
      if (this.armorCount < this.config.armorSlots) {
        this.armorCount += 1;
        this.durability += this.config.armorDurabilityBonus;
        // Consume the armor
        try {
          heldItem.setAmount(heldItem.amount - 1);
          // Update player's held item
          const inv = player.getComponent("minecraft:inventory");
          if (inv && inv.container) {
            const sel = player.selectedSlotIndex;
            inv.container.setItem(sel, heldItem.amount > 0 ? heldItem : undefined);
          }
        } catch (_) {}
        Debug.info(this.typeId, `Armor reinforced: ${this.armorCount}/${this.config.armorSlots}`);
        // Play reinforcement feedback
        this._setAnimationState(this.stateMachine.state);
        return true;
      }
    }

    // Rescue interaction — player interacting with occupied device
    if (this.stateMachine.is(DeviceState.CLOSED, DeviceState.TORTURING, DeviceState.CAPTURING)) {
      // Only external players can rescue (not the victim)
      if (String(player.id) !== String(this.victimId)) {
        this.release();
        return true;
      }
    }

    return false;
  }

  _isArmorItem(typeId) {
    return [
      "minecraft:iron_helmet", "minecraft:iron_chestplate",
      "minecraft:iron_leggings", "minecraft:iron_boots",
      "minecraft:diamond_helmet", "minecraft:diamond_chestplate",
      "minecraft:diamond_leggings", "minecraft:diamond_boots",
      "minecraft:chainmail_helmet", "minecraft:chainmail_chestplate",
      "minecraft:chainmail_leggings", "minecraft:chainmail_boots",
      "minecraft:golden_helmet", "minecraft:golden_chestplate",
      "minecraft:golden_leggings", "minecraft:golden_boots",
      "minecraft:netherite_helmet", "minecraft:netherite_chestplate",
      "minecraft:netherite_leggings", "minecraft:netherite_boots",
      "minecraft:leather_helmet", "minecraft:leather_chestplate",
      "minecraft:leather_leggings", "minecraft:leather_boots",
      "minecraft:turtle_helmet",
    ].includes(typeId);
  }

  // ── Public API ──

  release() {
    if (this.stateMachine.is(DeviceState.CAPTURING, DeviceState.CLOSED, DeviceState.TORTURING, DeviceState.DETECTING)) {
      this._cancelCapture();
      this.stateMachine.forceState(DeviceState.OPENING);
      this._saveState();
      this._onOpening();
    }
  }

  break() {
    this.stateMachine.forceState(DeviceState.BROKEN);
    this._saveState();
    this._onBroken();
  }

  takeDamage(amount) {
    this.durability = Math.max(0, this.durability - amount);
    if (this.durability <= 0) {
      this.break();
    }
  }

  // ── Timer cleanup ──

  _stopTorture() {
    if (this._tortureTimer) {
      try { system.clearRun(this._tortureTimer); } catch (_) {}
      this._tortureTimer = null;
    }
  }

  _stopAll() {
    this._stopTorture();
    if (this._captureTimer) {
      try { system.clearRun(this._captureTimer); } catch (_) {}
      this._captureTimer = null;
    }
    if (this._ambientTimer) {
      try { system.clearRun(this._ambientTimer); } catch (_) {}
      this._ambientTimer = null;
    }
  }

  dispose() {
    if (this._disposed) return;
    this._disposed = true;
    this._stopAll();
    this._releaseVictim();
    Debug.info(this.typeId, "Device disposed");
  }
}
