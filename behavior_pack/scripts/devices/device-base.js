/**
 * Cursed Contraptions — Torture Device Base Class
 *
 * Owns the complete lifecycle of one device: detection, capture, containment,
 * torture, rescue, damage, persistence, and cleanup.
 */

import {
  world,
  system,
  EntityDamageCause,
  InputPermissionCategory,
  ItemStack,
} from "@minecraft/server";
import { StateMachine, DeviceState } from "../utils/state-machine.js";
import { Debug } from "../utils/debug.js";
import {
  clearProp,
  getIntProp,
  getStringProp,
  setIntProp,
  setStringProp,
} from "../utils/persistence.js";
import { applyDamage, isEntityValid, randomDamage, rollExtremeDamage } from "../utils/damage.js";
import { CONFIG } from "../config.js";

const TRAPPED_TAG = "cc:trapped";
const CAPTURE_RESERVED_TAG = "cc:capture_reserved";
const MOVEMENT_SAVED_PROPERTY = "cc:movement_was_enabled";
const ANIMATION_STATES = Object.values(DeviceState);
const DEVICE_NAMES = Object.freeze({
  "cc:iron_maiden": "Iron Maiden",
  "cc:cursed_stocks": "Cursed Stocks",
  "cc:gravebinder_cage": "Gravebinder Cage",
  "cc:regret_rack": "The Regret Rack",
  "cc:black_reliquary": "The Black Reliquary",
});

export class TortureDevice {
  constructor(typeId, config, entity) {
    this.typeId = typeId;
    this.config = config;
    this.entity = entity;
    this.stateMachine = new StateMachine();

    this.victimId = null;
    this._victimEntity = null;
    this._victimMovementWasEnabled = null;
    this._pendingTargetId = null;
    this._pendingTarget = null;
    this._captureTimer = null;
    this._tortureTimer = null;
    this._redstoneTimer = null;
    this._timers = new Set();
    this._redstonePowered = false;
    this._redstoneActivationPending = false;
    this._canActivate = false;
    this._disposed = false;
    this._brokenHandled = false;
    this._lastPosition = null;
    this._lastDimension = null;

    this._loadState();
    this._recoverState();
    this._registerTransitions();
    this._resumeRecoveredState();
  }

  get position() {
    try {
      const location = this.entity.location;
      this._lastPosition = { x: location.x, y: location.y, z: location.z };
      this._lastDimension = this.entity.dimension;
      return this._lastPosition;
    } catch (_) {
      return this._lastPosition;
    }
  }

  get durability() {
    const saved = getIntProp(this.entity, "durability", this.config.baseDurability);
    return Math.max(0, Math.min(this.maxDurability, saved));
  }

  set durability(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return;
    const normalized = Math.max(0, Math.min(this.maxDurability, Math.floor(number)));
    setIntProp(this.entity, "durability", normalized);
    this._setEntityProperty("cc:durability", normalized);
  }

  get maxDurability() {
    return this.config.baseDurability + this.armorCount * this.config.armorDurabilityBonus;
  }

  get armorCount() {
    return Math.max(0, Math.min(
      this.config.armorSlots,
      getIntProp(this.entity, "armor_count", 0),
    ));
  }

  set armorCount(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return;
    const normalized = Math.max(0, Math.min(this.config.armorSlots, Math.floor(number)));
    setIntProp(this.entity, "armor_count", normalized);
    this._setEntityProperty("cc:armor_count", normalized);
  }

  _setEntityProperty(identifier, value) {
    try {
      if (isEntityValid(this.entity)) this.entity.setProperty(identifier, value);
    } catch (_) {
      // Dynamic properties remain authoritative if a client-sync property is unavailable.
    }
  }

  _loadState() {
    const savedState = getStringProp(this.entity, "state", DeviceState.IDLE);
    this.stateMachine = StateMachine.deserialize(savedState);

    this.armorCount = getIntProp(this.entity, "armor_count", 0);
    const savedDurability = getIntProp(this.entity, "durability", this.config.baseDurability);
    this.durability = savedDurability;

    const savedVictimId = getStringProp(this.entity, "victim_id", "");
    this.victimId = savedVictimId || null;
    const pendingTargetId = getStringProp(this.entity, "pending_victim_id", "");
    this._pendingTargetId = pendingTargetId || null;
  }

  _recoverState() {
    const savedState = this.stateMachine.state;

    if (savedState === DeviceState.BROKEN) {
      // A crash may happen during the break-animation delay. Do not drop a
      // second item; the original break already emitted its single drop.
      this._brokenHandled = true;
      this._setAnimationState("broken");
      return;
    }

    if (savedState === DeviceState.IDLE) {
      this._setAnimationState("idle");
      return;
    }

    if (savedState === DeviceState.DETECTING) {
      this._clearPendingCapture();
      this._releaseVictim();
      this.stateMachine.forceState(DeviceState.IDLE);
      this._setAnimationState("idle");
      this._saveState();
      return;
    }

    if (this.stateMachine.is(
      DeviceState.CAPTURING,
      DeviceState.CLOSED,
      DeviceState.TORTURING,
    )) {
      const victim = this._getVictim();
      if (victim && this._hasTag(victim, TRAPPED_TAG)) {
        this._victimEntity = victim;
        this.stateMachine.forceState(DeviceState.TORTURING);
        return;
      }

      this._releaseVictim();
      this.stateMachine.forceState(DeviceState.IDLE);
      this._setAnimationState("idle");
      this._saveState();
      return;
    }

    if (this.stateMachine.is(DeviceState.OPENING, DeviceState.RELEASED)) {
      this._releaseVictim();
      this.stateMachine.forceState(DeviceState.IDLE);
      this._setAnimationState("idle");
      this._saveState();
    }
  }

  _resumeRecoveredState() {
    if (this._brokenHandled) {
      this._scheduleTimeout(() => this._removeBrokenEntity(), 1);
      return;
    }

    if (this.stateMachine.state !== DeviceState.TORTURING || !this._victimEntity) return;
    this._lockVictimMovement(this._victimEntity);
    this._setAnimationState("torturing");
    this._applyDebuff(this._victimEntity);
    this._startTortureCycle();
    this._saveState();
  }

  _saveState() {
    if (this._disposed || !this._entityValid()) return;
    setStringProp(this.entity, "state", this.stateMachine.state);
    this._setEntityProperty("cc:state", this.stateMachine.state);
  }

  _registerTransitions() {
    this.stateMachine.onTransition(DeviceState.DETECTING, (_, to) => {
      if (to === DeviceState.IDLE) this._cancelCapture();
    });
    this.stateMachine.onTransition(DeviceState.CAPTURING, (_, to) => {
      if (to === DeviceState.CLOSED) this._onClosed();
      if (to === DeviceState.OPENING) this._onOpening();
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

    for (const from of Object.values(DeviceState)) {
      this.stateMachine.onTransition(from, (_, to) => {
        if (to === DeviceState.BROKEN) this._onBroken();
      });
    }
  }

  tick(canActivate = this._canActivate, checkForTargets = true) {
    if (this._disposed || !this._entityValid()) return;
    this._canActivate = Boolean(canActivate);

    switch (this.stateMachine.state) {
      case DeviceState.IDLE:
        if (checkForTargets && this._canActivate) this._tryDetect();
        break;
      case DeviceState.DETECTING:
        if (!this._isPendingCaptureValid()) this._cancelPendingCaptureToIdle();
        break;
      case DeviceState.CAPTURING:
      case DeviceState.CLOSED:
      case DeviceState.TORTURING:
        this._containVictim();
        break;
      default:
        break;
    }
  }

  _entityValid() {
    return isEntityValid(this.entity);
  }

  _tryDetect() {
    if (this._disposed || !this._canActivate || !this.stateMachine.is(DeviceState.IDLE)) return;
    const position = this.position;
    if (!position || !this._entityValid()) return;

    const targets = [];
    const dimension = this.entity.dimension;
    for (const family of ["player", "mob"]) {
      try {
        targets.push(...dimension.getEntities({
          location: position,
          maxDistance: this.config.captureRadius,
          families: [family],
        }));
      } catch (_) {
        // One unavailable family query should not prevent the other from working.
      }
    }

    for (const target of targets) {
      if (this._isCapturable(target)) {
        this._beginCapture(target);
        return;
      }
    }
  }

  _isCapturable(entity) {
    if (!isEntityValid(entity)) return false;

    try {
      const health = entity.getComponent("minecraft:health");
      if (!health || health.currentValue <= 0) return false;

      if (entity.typeId === "minecraft:player") {
        try {
          const gameMode = String(entity.getGameMode()).toLowerCase();
          if (gameMode === "creative" || gameMode === "spectator") return false;
        } catch (_) {
          // If game mode is unavailable, use the normal health/tag checks.
        }
      }

      return !this._hasTag(entity, TRAPPED_TAG)
        && !this._hasTag(entity, CAPTURE_RESERVED_TAG);
    } catch (_) {
      return false;
    }
  }

  _beginCapture(target) {
    if (!this._canActivate || !this.stateMachine.transition(DeviceState.DETECTING)) return;

    this._pendingTarget = target;
    this._pendingTargetId = String(target.id);
    try {
      target.addTag(CAPTURE_RESERVED_TAG);
    } catch (_) {}
    setStringProp(this.entity, "pending_victim_id", this._pendingTargetId);
    this._saveState();
    this._setAnimationState("detecting");
    Debug.info(this.typeId, `Detected ${target.typeId}; starting capture sequence`);

    this._captureTimer = this._scheduleTimeout(() => {
      this._captureTimer = null;
      if (!this.stateMachine.is(DeviceState.DETECTING)) return;
      const pendingTarget = this._getPendingTarget();
      if (!this._isPendingCaptureValid(pendingTarget)) {
        this._cancelPendingCaptureToIdle();
        return;
      }
      this._executeCapture(pendingTarget);
    }, this.config.captureDelay);
  }

  _getPendingTarget() {
    if (!this._pendingTargetId) return null;
    if (isEntityValid(this._pendingTarget)
      && String(this._pendingTarget.id) === String(this._pendingTargetId)) {
      return this._pendingTarget;
    }

    try {
      const target = world.getEntity(String(this._pendingTargetId));
      if (isEntityValid(target)) {
        this._pendingTarget = target;
        return target;
      }
    } catch (_) {}
    return null;
  }

  _isPendingCaptureValid(target = this._getPendingTarget()) {
    if (!target || !isEntityValid(target)) return false;
    if (String(target.id) !== String(this._pendingTargetId)) return false;
    if (!this._sameDimension(target)) return false;
    if (!this._isNearDevice(target, this.config.captureRadius)) return false;

    try {
      const health = target.getComponent("minecraft:health");
      if (!health || health.currentValue <= 0) return false;
      if (this._hasTag(target, TRAPPED_TAG)) return false;
      if (!this._hasTag(target, CAPTURE_RESERVED_TAG)) return false;

      if (target.typeId === "minecraft:player") {
        try {
          const gameMode = String(target.getGameMode()).toLowerCase();
          if (gameMode === "creative" || gameMode === "spectator") return false;
        } catch (_) {
          // Continue with health and capture-reservation checks.
        }
      }
    } catch (_) {
      return false;
    }

    return true;
  }

  _executeCapture(target) {
    if (!this.stateMachine.transition(DeviceState.CAPTURING)) return;
    this._clearPendingCapture();

    this._victimEntity = target;
    this.victimId = String(target.id);
    setStringProp(this.entity, "victim_id", this.victimId);
    try {
      target.addTag(TRAPPED_TAG);
    } catch (_) {}

    this._teleportToDevice(target);
    this._lockVictimMovement(target);
    this._applyDebuff(target);
    this._saveState();
    this._setAnimationState("capturing");
    this._notifyVictim(target, `You are trapped in the ${this._displayName()}. A teammate can interact with it to free you.`);
    Debug.info(this.typeId, `Captured entity ${this.victimId}`);

    this._captureTimer = this._scheduleTimeout(() => {
      this._captureTimer = null;
      if (this.stateMachine.state !== DeviceState.CAPTURING) return;
      if (!this._getVictim()) {
        this.release();
        return;
      }
      this.stateMachine.transition(DeviceState.CLOSED);
      this._saveState();
    }, this.config.closeDuration);
  }

  _cancelPendingCaptureToIdle() {
    if (this.stateMachine.state !== DeviceState.DETECTING) return;
    this.stateMachine.transition(DeviceState.IDLE);
    this._saveState();
  }

  _clearPendingCapture() {
    this._clearTimer(this._captureTimer);
    this._captureTimer = null;

    let pending = this._pendingTarget;
    if (!isEntityValid(pending) && this._pendingTargetId) {
      try {
        pending = world.getEntity(String(this._pendingTargetId));
      } catch (_) {
        pending = null;
      }
    }
    if (isEntityValid(pending)) {
      try {
        pending.removeTag(CAPTURE_RESERVED_TAG);
      } catch (_) {}
    }

    this._pendingTarget = null;
    this._pendingTargetId = null;
    clearProp(this.entity, "pending_victim_id");
  }

  _cancelCapture() {
    this._clearPendingCapture();
    this._setAnimationState("idle");
  }

  _onClosed() {
    this._setAnimationState("closed");
    this._scheduleTimeout(() => {
      if (this.stateMachine.state === DeviceState.CLOSED) {
        this.stateMachine.transition(DeviceState.TORTURING);
        this._saveState();
      }
    }, CONFIG.timings.closedPauseTicks);
  }

  _onTorturing() {
    this._setAnimationState("torturing");
    this._startTortureCycle();
  }

  _startTortureCycle() {
    this._clearTimer(this._tortureTimer);
    this._tortureTimer = null;
    this._scheduleNextDamage();
  }

  _scheduleNextDamage() {
    if (this._disposed || !this.stateMachine.is(DeviceState.TORTURING)) return;

    const cycleTime = Math.floor(
      this.config.tortureInterval * Math.pow(this.config.armorSpeedMultiplier, this.armorCount),
    );
    this._tortureTimer = this._scheduleTimeout(() => {
      this._tortureTimer = null;
      if (this._disposed || !this.stateMachine.is(DeviceState.TORTURING) || !this._entityValid()) return;
      this._performDamageCycle();
    }, Math.max(cycleTime, 10));
  }

  _performDamageCycle() {
    const victim = this._getVictim();
    if (!victim || !this._hasTag(victim, TRAPPED_TAG)) {
      this.release();
      return;
    }

    this._applyHealing(victim);

    const multiplier = Math.pow(this.config.armorDamageMultiplier, this.armorCount);
    const isExtreme = rollExtremeDamage(this.config.extremeDamageChance);
    const baseDamage = isExtreme
      ? this.config.extremeDamageAmount
      : randomDamage(this.config.tortureMinDamage, this.config.tortureMaxDamage);
    const health = this._getHealth(victim);
    const survivableDamage = health ? Math.max(0, health.currentValue - 1) : 0;
    const damage = Math.min(Math.floor(baseDamage * multiplier), survivableDamage);

    this._spawnParticles(isExtreme ? "extreme" : "normal");
    if (damage > 0) applyDamage(victim, damage, EntityDamageCause.contact);
    this._applyDebuff(victim);
    this.durability = this.durability - 1;

    if (this.durability <= 0) {
      this.break();
      return;
    }

    this._applyVignette(victim);
    this._scheduleNextDamage();
  }

  _containVictim() {
    const victim = this._getVictim();
    if (!victim || !this._hasTag(victim, TRAPPED_TAG)) {
      this.release();
      return;
    }

    const position = this.position;
    if (!position || !this._sameDimension(victim)) {
      this.release();
      return;
    }

    if (this._distanceSquared(victim.location, position) > 0.25) {
      this._teleportToDevice(victim);
    }

    if (victim.typeId === "minecraft:player") {
      this._lockVictimMovement(victim);
    }
  }

  _onOpening() {
    this._clearTimer(this._captureTimer);
    this._captureTimer = null;
    this._clearTimer(this._tortureTimer);
    this._tortureTimer = null;
    this._setAnimationState("opening");

    this._scheduleTimeout(() => {
      if (this.stateMachine.state === DeviceState.OPENING) {
        this.stateMachine.transition(DeviceState.RELEASED);
        this._saveState();
      }
    }, CONFIG.timings.releaseAnimationTicks);
  }

  _onReleased() {
    const victim = this._releaseVictim();
    this._setAnimationState("released");
    if (victim) this._notifyVictim(victim, "You have been freed.");

    this._scheduleTimeout(() => {
      if (this.stateMachine.state === DeviceState.RELEASED) {
        this.stateMachine.transition(DeviceState.IDLE);
        this._saveState();
      }
    }, CONFIG.timings.releaseAnimationTicks);
  }

  _onIdle() {
    this._setAnimationState("idle");
  }

  _onBroken() {
    if (this._brokenHandled) return;
    this._brokenHandled = true;
    Debug.info(this.typeId, "Device broken");

    this._stopAll();
    this._clearPendingCapture();
    this._releaseVictim();
    this._saveState();
    this._setAnimationState("broken");
    const position = this.position;
    this._dropItem(this._lastDimension, position);

    this._scheduleTimeout(() => this._removeBrokenEntity(), CONFIG.timings.brokenAnimationTicks);
  }

  _removeBrokenEntity() {
    try {
      if (this._entityValid()) this.entity.kill();
    } catch (_) {}
    this.dispose();
  }

  _dropItem(dimension = this._lastDimension, position = this.position) {
    if (!this.config.dropOnBreak || !dimension || !position) return false;

    try {
      const itemId = this.typeId.replace(/^cc:/, "cc:item_");
      dimension.spawnItem(new ItemStack(itemId, 1), position);
      return true;
    } catch (error) {
      Debug.error(this.typeId, "Could not drop the broken device item", error);
      return false;
    }
  }

  _getVictim(includeOutOfRange = false) {
    if (!this.victimId) return null;

    const candidates = [this._victimEntity];
    try {
      candidates.push(world.getEntity(String(this.victimId)));
    } catch (_) {}

    for (const candidate of candidates) {
      if (!isEntityValid(candidate) || String(candidate.id) !== String(this.victimId)) continue;
      if (!includeOutOfRange) {
        if (!this._sameDimension(candidate)) continue;
        if (!this._isNearDevice(candidate, CONFIG.performance.entityScanRadius)) continue;
      }
      this._victimEntity = candidate;
      return candidate;
    }

    // Direct identifier lookups above are authoritative: world.getEntity and
    // Dimension.getEntities read from the same loaded-entity registry, and
    // the same dimension/distance rules already ran for every candidate, so
    // a tag-scoped proximity scan cannot find a victim the id lookups
    // rejected (v0.1.1 audit finding F5).
    return null;
  }

  _releaseVictim() {
    const victim = this._getVictim(true);
    if (victim) {
      try { victim.removeTag(TRAPPED_TAG); } catch (_) {}
      try { victim.removeTag(CAPTURE_RESERVED_TAG); } catch (_) {}
      this._restoreVictimMovement(victim);
      if (this._sameDimension(victim)
        && this._isNearDevice(victim, CONFIG.performance.entityScanRadius)) {
        this._teleportAway(victim);
      }
    }

    this.victimId = null;
    this._victimEntity = null;
    clearProp(this.entity, "victim_id");
    return victim;
  }

  _applyDebuff(entity) {
    if (!isEntityValid(entity)) return;
    try {
      entity.addEffect("weakness", this.config.weaknessDuration, {
        amplifier: this.config.weaknessAmplifier,
        showParticles: false,
      });
    } catch (_) {}
  }

  _applyHealing(entity) {
    const health = this._getHealth(entity);
    if (!health || this.config.healAmount <= 0) return;

    try {
      health.setCurrentValue(Math.min(health.effectiveMax, health.currentValue + this.config.healAmount));
    } catch (_) {}
  }

  _getHealth(entity) {
    if (!isEntityValid(entity)) return null;
    try {
      return entity.getComponent("minecraft:health");
    } catch (_) {
      return null;
    }
  }

  _applyVignette(entity) {
    if (!CONFIG.vignette.enabled || !isEntityValid(entity) || entity.typeId !== "minecraft:player") return;
    try {
      entity.addEffect("blindness", CONFIG.vignette.fadeInTicks, {
        amplifier: 0,
        showParticles: false,
      });
    } catch (_) {}
  }

  _spawnParticles(type) {
    if (!this._entityValid()) return;
    const position = this.position;
    if (!position) return;

    const dimension = this._lastDimension;
    if (!dimension) return;

    try {
      let emitted = 0;
      const particleLimit = CONFIG.performance.maxParticlesPerEvent;
      if (CONFIG.particles.impactEnabled) {
        const smokeCount = type === "extreme" ? CONFIG.particles.smokeCount * 2 : CONFIG.particles.smokeCount;
        const count = Math.min(smokeCount, particleLimit);
        for (let i = 0; i < count; i++) {
          dimension.spawnParticle("minecraft:basic_smoke_particle", {
            x: position.x + Math.random() - 0.5,
            y: position.y + 1,
            z: position.z + Math.random() - 0.5,
          });
          emitted++;
        }
      }

      if (CONFIG.particles.sparkEnabled) {
        const sparkCount = type === "extreme" ? CONFIG.particles.sparkCount * 2 : CONFIG.particles.sparkCount;
        const count = Math.min(sparkCount, Math.max(0, particleLimit - emitted));
        for (let i = 0; i < count; i++) {
          dimension.spawnParticle("minecraft:basic_flame_particle", {
            x: position.x + Math.random() - 0.5,
            y: position.y + 0.5,
            z: position.z + Math.random() - 0.5,
          });
        }
      }
    } catch (_) {}
  }

  _setAnimationState(stateName) {
    if (!this._entityValid()) return;
    try {
      for (const state of ANIMATION_STATES) {
        this.entity.removeTag(`cc:anim_${state}`);
      }
      this.entity.addTag(`cc:anim_${stateName}`);
    } catch (_) {}
  }

  onRedstonePower(powered) {
    if (this._disposed || !this._entityValid()) return;
    const signal = Boolean(powered);

    if (!signal) {
      this._redstonePowered = false;
      return;
    }
    if (this._redstonePowered) return;

    this._redstonePowered = true;
    if (!this.stateMachine.is(DeviceState.IDLE) || this._redstoneActivationPending) return;

    this._redstoneActivationPending = true;
    this._redstoneTimer = this._scheduleTimeout(() => {
      this._redstoneTimer = null;
      this._redstoneActivationPending = false;
      if (!this._disposed && this._canActivate && this.stateMachine.is(DeviceState.IDLE)) {
        this._tryDetect();
      }
    }, this.config.redstoneActivationDelay);
  }

  onInteract(player, heldItem) {
    if (this._disposed || !isEntityValid(player) || this.stateMachine.is(DeviceState.BROKEN)) return false;

    if (this.stateMachine.is(DeviceState.CAPTURING, DeviceState.CLOSED, DeviceState.TORTURING)) {
      if (String(player.id) === String(this.victimId)) return false;
      if (!this.release()) return false;
      try {
        player.sendMessage(`§aYou freed the captive from the ${this._displayName()}.`);
      } catch (_) {}
      return true;
    }

    if (heldItem && this._isArmorItem(heldItem.typeId)) {
      if (this.armorCount >= this.config.armorSlots) {
        try { player.sendMessage("§eThis device cannot be reinforced any further."); } catch (_) {}
        return false;
      }
      if (!this._consumeHeldItem(player, heldItem)) return false;

      this.armorCount += 1;
      this.durability += this.config.armorDurabilityBonus;
      this._setAnimationState(this.stateMachine.state);
      Debug.info(this.typeId, `Reinforced (${this.armorCount}/${this.config.armorSlots})`);
      try { player.sendMessage(`§aReinforced ${this._displayName()} (${this.armorCount}/${this.config.armorSlots}).`); } catch (_) {}
      return true;
    }

    return false;
  }

  _consumeHeldItem(player, heldItem) {
    try {
      const inventory = player.getComponent("minecraft:inventory")?.container;
      const slot = player.selectedSlotIndex;
      if (!inventory || !Number.isInteger(slot)) return false;

      const current = inventory.getItem(slot);
      if (!current || current.typeId !== heldItem.typeId || current.amount < 1) return false;
      if (current.amount === 1) {
        inventory.setItem(slot, undefined);
      } else {
        current.setAmount(current.amount - 1);
        inventory.setItem(slot, current);
      }
      return true;
    } catch (_) {
      return false;
    }
  }

  _isArmorItem(typeId) {
    return typeId === "minecraft:elytra"
      || /^minecraft:[a-z0-9]+_(helmet|chestplate|leggings|boots)$/.test(typeId);
  }

  _displayName() {
    return DEVICE_NAMES[this.typeId] || "Cursed Contraption";
  }

  _notifyVictim(victim, message) {
    if (!isEntityValid(victim) || victim.typeId !== "minecraft:player") return;
    try { victim.sendMessage(`§c[Cursed Contraptions] ${message}`); } catch (_) {}
  }

  _lockVictimMovement(victim) {
    if (!isEntityValid(victim) || victim.typeId !== "minecraft:player") return;

    let saved;
    try { saved = victim.getDynamicProperty(MOVEMENT_SAVED_PROPERTY); } catch (_) {}
    if (typeof saved === "boolean") {
      this._victimMovementWasEnabled = saved;
    } else {
      try {
        this._victimMovementWasEnabled = victim.inputPermissions.isPermissionCategoryEnabled(
          InputPermissionCategory.Movement,
        );
        try { victim.setDynamicProperty(MOVEMENT_SAVED_PROPERTY, this._victimMovementWasEnabled); } catch (_) {}
      } catch (_) {
        // Position containment remains as a fallback if input permissions are unavailable.
      }
    }

    try {
      victim.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, false);
    } catch (_) {
      // Position containment remains as a fallback if input permissions are unavailable.
    }
  }

  _restoreVictimMovement(victim) {
    if (!isEntityValid(victim) || victim.typeId !== "minecraft:player") return;

    let saved;
    try { saved = victim.getDynamicProperty(MOVEMENT_SAVED_PROPERTY); } catch (_) {}
    const wasEnabled = typeof saved === "boolean"
      ? saved
      : (typeof this._victimMovementWasEnabled === "boolean" ? this._victimMovementWasEnabled : true);
    try { victim.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, wasEnabled); } catch (_) {}
    try { victim.setDynamicProperty(MOVEMENT_SAVED_PROPERTY, undefined); } catch (_) {}
    this._victimMovementWasEnabled = null;
  }

  _teleportToDevice(entity) {
    if (!isEntityValid(entity)) return;
    const position = this.position;
    const dimension = this._lastDimension;
    if (!position || !dimension) return;

    try {
      entity.teleport(position, { dimension });
    } catch (_) {}
  }

  _teleportAway(entity) {
    if (!isEntityValid(entity)) return;
    const position = this.position;
    const dimension = this._lastDimension;
    if (!position || !dimension) return;

    const offsets = [
      { x: 2, z: 0 }, { x: -2, z: 0 }, { x: 0, z: 2 }, { x: 0, z: -2 },
      { x: 2, z: 2 }, { x: 2, z: -2 }, { x: -2, z: 2 }, { x: -2, z: -2 },
    ];
    for (const offset of offsets) {
      const location = {
        x: Math.floor(position.x + offset.x) + 0.5,
        y: position.y,
        z: Math.floor(position.z + offset.z) + 0.5,
      };
      if (!this._isClearReleaseLocation(dimension, location)) continue;
      try {
        entity.teleport(location, { dimension });
        return;
      } catch (_) {}
    }

    try {
      entity.teleport({ x: position.x + 2, y: position.y, z: position.z }, { dimension });
    } catch (_) {}
  }

  _isClearReleaseLocation(dimension, location) {
    try {
      const x = Math.floor(location.x);
      const y = Math.floor(location.y);
      const z = Math.floor(location.z);
      const body = [0, 1, 2].map((height) => dimension.getBlock({ x, y: y + height, z }));
      return body.every((block) => block && this._isPassable(block));
    } catch (_) {
      return false;
    }
  }

  _isPassable(block) {
    try {
      if (block.isAir) return true;
      return block.isLiquid && !String(block.typeId).includes("lava");
    } catch (_) {
      return false;
    }
  }

  _hasTag(entity, tag) {
    try { return entity.hasTag(tag); } catch (_) { return false; }
  }

  _sameDimension(entity) {
    try {
      const deviceDimension = this._entityValid() ? this.entity.dimension : this._lastDimension;
      if (!deviceDimension || !entity.dimension) return false;
      return deviceDimension.id === entity.dimension.id;
    } catch (_) {
      return false;
    }
  }

  _isNearDevice(entity, radius) {
    const position = this.position;
    if (!position || !entity) return false;
    try {
      return this._distanceSquared(entity.location, position) <= radius * radius;
    } catch (_) {
      return false;
    }
  }

  _distanceSquared(first, second) {
    const dx = first.x - second.x;
    const dy = first.y - second.y;
    const dz = first.z - second.z;
    return dx * dx + dy * dy + dz * dz;
  }

  _scheduleTimeout(callback, ticks) {
    const delay = Math.max(1, Math.ceil(Number(ticks) || 1));
    let handle;
    handle = system.runTimeout(() => {
      this._timers.delete(handle);
      if (!this._disposed) callback();
    }, delay);
    this._timers.add(handle);
    return handle;
  }

  _clearTimer(handle) {
    if (handle === null || handle === undefined) return;
    try { system.clearRun(handle); } catch (_) {}
    this._timers.delete(handle);
  }

  _stopAll() {
    for (const handle of [...this._timers]) this._clearTimer(handle);
    this._captureTimer = null;
    this._tortureTimer = null;
    this._redstoneTimer = null;
    this._redstoneActivationPending = false;
  }

  onVictimUnavailable(victimId) {
    const id = String(victimId);
    if (String(this._pendingTargetId) === id && this.stateMachine.is(DeviceState.DETECTING)) {
      this._cancelPendingCaptureToIdle();
      return true;
    }
    if (String(this.victimId) !== id) return false;

    this.victimId = null;
    this._victimEntity = null;
    clearProp(this.entity, "victim_id");
    return this.release();
  }

  reconnectVictim(entity) {
    if (!isEntityValid(entity)) return false;
    const id = String(entity.id);

    if (String(this._pendingTargetId) === id && this.stateMachine.is(DeviceState.DETECTING)) {
      this._pendingTarget = entity;
      try { entity.addTag(CAPTURE_RESERVED_TAG); } catch (_) {}
      return true;
    }

    if (String(this.victimId) !== id || !this.stateMachine.is(
      DeviceState.CAPTURING,
      DeviceState.CLOSED,
      DeviceState.TORTURING,
    )) return false;

    this._victimEntity = entity;
    try { entity.addTag(TRAPPED_TAG); } catch (_) {}
    this._lockVictimMovement(entity);
    return true;
  }

  release() {
    if (this._disposed) return false;

    if (this.stateMachine.is(DeviceState.DETECTING)) {
      const changed = this.stateMachine.transition(DeviceState.IDLE);
      if (changed) this._saveState();
      return changed;
    }

    if (!this.stateMachine.is(
      DeviceState.CAPTURING,
      DeviceState.CLOSED,
      DeviceState.TORTURING,
    )) return false;

    const changed = this.stateMachine.transition(DeviceState.OPENING);
    if (changed) this._saveState();
    return changed;
  }

  break() {
    if (this._disposed || this.stateMachine.is(DeviceState.BROKEN)) return false;
    const changed = this.stateMachine.transition(DeviceState.BROKEN);
    if (changed) this._saveState();
    return changed;
  }

  takeDamage(amount) {
    if (this._disposed || this.stateMachine.is(DeviceState.BROKEN)) return false;
    const damage = Number(amount);
    if (!Number.isFinite(damage) || damage <= 0) return false;

    this.durability = this.durability - Math.ceil(damage);
    if (this.durability <= 0) this.break();
    return true;
  }

  onEntityDeath(dimension, position) {
    if (!this._brokenHandled) {
      this._brokenHandled = true;
      this._stopAll();
      this._clearPendingCapture();
      this._releaseVictim();
      this.stateMachine.forceState(DeviceState.BROKEN);
      const deathPosition = position || this.position || this._lastPosition;
      this._dropItem(dimension || this._lastDimension, deathPosition);
    }
    this.dispose();
  }

  dispose() {
    if (this._disposed) return;
    this._disposed = true;
    this._stopAll();
    this._clearPendingCapture();
    this._releaseVictim();
    Debug.info(this.typeId, "Device disposed");
  }
}
