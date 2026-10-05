/**
 * Cursed Contraptions — Torture Device Base Class
 *
 * Owns the complete lifecycle of one device: detection, capture, containment,
 * torture, rescue, damage, persistence, and cleanup.
 *
 * Containment contract (v0.1.4)
 * ----------------------------
 * A captive is either *seated* (inside ``containmentRadius``, glued to the seat
 * by the anchoring loop in ``utils/containment.js``) or *outside*. Damage is
 * only ever applied while the captive is seated, so the v0.1.3 bug where a
 * shoved mob kept taking damage while it was pushed out of the device is
 * impossible by construction. A captive that cannot be reseated is released
 * instead of being left in limbo.
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
import { anchorEntity, distanceSquared, stopMotion } from "../utils/containment.js";
import { IMMUNITY_TAG, clearImmunity, grantImmunity, immunitySecondsLeft, isImmune } from "../utils/immunity.js";
import { playCue, showStatus } from "../utils/feedback.js";
import { CONFIG } from "../config.js";

const TRAPPED_TAG = "cc:trapped";
const CAPTURE_RESERVED_TAG = "cc:capture_reserved";
const MOVEMENT_SAVED_PROPERTY = "cc:movement_was_enabled";
const STRAIN_TAG = "cc:anim_strain";
const BURST_TAG = "cc:anim_burst";
const ANIMATION_STATES = Object.values(DeviceState);
const WEAR_STAGES = 4;

/**
 * Entity events. The behavior-pack entity declaration turns these into
 * component-group swaps.
 */
const DEVICE_SEAT_EVENT = "cc:seat_victim";
const DEVICE_CLEAR_EVENT = "cc:clear_victim";

/**
 * Mob containment uses effects on top of the anchoring loop: Slowness VII pins
 * the movement multiplier at zero and Blindness stops a caged zombie from
 * targeting whoever walks past. Both work on every vanilla mob, so no custom
 * entity definitions are needed.
 */
const MOB_FREEZE_EFFECT = "slowness";
const MOB_BLIND_EFFECT = "blindness";

// States in which a device holds a captive.
const OCCUPIED_STATES = [
  DeviceState.CAPTURING,
  DeviceState.CLOSED,
  DeviceState.TORTURING,
];

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
    this._victimSeated = false;
    this._victimIsPlayer = false;
    this._pendingTargetId = null;
    this._pendingTarget = null;
    this._captureTimer = null;
    this._tortureTimer = null;
    this._redstoneTimer = null;
    this._strainTimer = null;
    this._burstTimer = null;
    this._hudTimer = null;
    this._timers = new Set();
    this._redstonePowered = false;
    this._redstoneActivationPending = false;
    this._canActivate = false;
    this._disposed = false;
    this._brokenHandled = false;
    this._interactionFeedbackTicks = new Map();
    this._lastPosition = null;
    this._lastDimension = null;
    this._lastCorrectionTick = -Infinity;
    this._lastSeatRefreshTick = -Infinity;
    this._lastFailures = 0;
    this._nextStruggleTick = null;
    this._strainUntilTick = null;
    this._captureStartedTick = 0;

    this._loadState();
    this._recoverState();
    this._registerTransitions();
    this._resumeRecoveredState();
  }

  // ------------------------------------------------------------------ state --
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
    this._updateWearStage(normalized);
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

  /** Souls harvested by this device; they drop as shards when it is destroyed. */
  get souls() {
    return Math.max(0, getIntProp(this.entity, "souls", 0));
  }

  set souls(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return;
    const normalized = Math.max(0, Math.min(1000, Math.floor(number)));
    setIntProp(this.entity, "souls", normalized);
    this._setEntityProperty("cc:souls", normalized);
  }

  /** Soul charge 0..CONFIG.charge.max; drives escalation and the client tier. */
  get charge() {
    return Math.max(0, Math.min(CONFIG.charge.max, getIntProp(this.entity, "charge", 0)));
  }

  set charge(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return;
    const normalized = Math.max(0, Math.min(CONFIG.charge.max, Math.floor(number)));
    setIntProp(this.entity, "charge", normalized);
    // Client-synced, so the animation controller escalates to the hotter
    // torture loop without another server round trip.
    this._setEntityProperty("cc:charge", normalized);
  }

  /** True while the device is holding a captive. */
  get isOccupied() {
    return this.stateMachine.is(...OCCUPIED_STATES);
  }

  /** True while the device is empty and ready for a new victim. */
  get isReady() {
    return this.stateMachine.is(DeviceState.IDLE, DeviceState.DETECTING);
  }

  /** Human-readable one-line status used by admin commands and feedback. */
  get statusLine() {
    const armor = this.config.armorSlots > 0
      ? `, reinforced ${this.armorCount}/${this.config.armorSlots}`
      : "";
    const souls = this.souls > 0 ? `, souls ${this.souls}` : "";
    return `${this.stateMachine.state} — Durability: ${this.durability}/${this.maxDurability}${armor}${souls}`;
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
    this.durability = getIntProp(this.entity, "durability", this.config.baseDurability);
    this.charge = getIntProp(this.entity, "charge", 0);

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
      this.charge = 0;
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

    if (this.stateMachine.is(...OCCUPIED_STATES)) {
      const victim = this._getVictim();
      if (victim && this._hasTag(victim, TRAPPED_TAG)) {
        this._victimEntity = victim;
        this._victimIsPlayer = victim.typeId === "minecraft:player";
        this.stateMachine.forceState(DeviceState.TORTURING);
        return;
      }

      this._releaseVictim();
      this.stateMachine.forceState(DeviceState.IDLE);
      this._setAnimationState("idle");
      this.charge = 0;
      this._saveState();
      return;
    }

    if (this.stateMachine.is(DeviceState.OPENING, DeviceState.RELEASED)) {
      this._releaseVictim();
      this.stateMachine.forceState(DeviceState.IDLE);
      this._setAnimationState("idle");
      this.charge = 0;
      this._saveState();
    }
  }

  _resumeRecoveredState() {
    if (this._brokenHandled) {
      this._scheduleTimeout(() => this._removeBrokenEntity(), 1);
      return;
    }

    if (this.stateMachine.state !== DeviceState.TORTURING || !this._victimEntity) return;
    const victim = this._victimEntity;
    this._seatVictim(victim);
    this._setAnimationState("torturing");
    this._applyDebuff(victim);
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

  // ------------------------------------------------------------------- tick --
  tick(canActivate = this._canActivate, checkForTargets = true) {
    if (this._disposed || !this._entityValid()) return;
    this._canActivate = Boolean(canActivate);

    switch (this.stateMachine.state) {
      case DeviceState.IDLE:
        if (checkForTargets && this._canActivate) this._tryDetect();
        if (this.charge > 0) this._decayCharge();
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

    let closest = null;
    let closestDistance = Infinity;
    for (const target of targets) {
      if (!this._isCapturable(target)) continue;
      const distance = this._distanceSquared(target.location, position);
      if (distance < closestDistance) {
        closest = target;
        closestDistance = distance;
      }
    }
    if (closest) this._beginCapture(closest);
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
        if (isImmune(entity)) return false;
      }

      return !this._hasTag(entity, TRAPPED_TAG)
        && !this._hasTag(entity, CAPTURE_RESERVED_TAG);
    } catch (_) {
      return false;
    }
  }

  // ---------------------------------------------------------------- capture --
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
    this._spawnBurst(CONFIG.particles.captureBurstCount);
    playCue(this._lastDimension, this.position, "capture", this.config);
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
        if (isImmune(target)) return false;
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
    this._victimIsPlayer = target.typeId === "minecraft:player";
    this.victimId = String(target.id);
    setStringProp(this.entity, "victim_id", this.victimId);
    try {
      target.addTag(TRAPPED_TAG);
      target.removeTag(CAPTURE_RESERVED_TAG);
    } catch (_) {}

    this._seatVictim(target);
    this._teleportToDevice(target);
    this._applyDebuff(target);
    this._saveState();
    this._setAnimationState("capturing");
    this._spawnBurst(CONFIG.particles.captureBurstCount);
    playCue(this._lastDimension, this.position, "slam", this.config);
    this._captureStartedTick = Number.isFinite(system.currentTick) ? system.currentTick : 0;
    this._notifyVictim(target, `You are trapped in the ${this._displayName()}. A teammate can interact with it to free you.`);
    this._refreshHud(true);
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
    this._spawnBurst(CONFIG.particles.captureBurstCount);
    playCue(this._lastDimension, this.position, "latch", this.config);
    this._refreshHud(true);
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
    this._refreshHud(true);
  }

  // --------------------------------------------------------------- torture --
  _startTortureCycle() {
    this._clearTimer(this._tortureTimer);
    this._tortureTimer = null;
    this._scheduleNextDamage();
  }

  /** Cycle length after armor speed-up and soul-charge escalation. */
  get cycleTicks() {
    const armor = Math.pow(this.config.armorSpeedMultiplier, this.armorCount);
    const charge = 1 - this.charge * CONFIG.charge.speedBonusPerStep;
    return Math.max(10, Math.floor(this.config.tortureInterval * armor * charge));
  }

  _scheduleNextDamage() {
    if (this._disposed || !this.stateMachine.is(DeviceState.TORTURING)) return;

    // Always retire the pending cycle first: a discharge reschedules from
    // inside an already-planned cycle, and a forgotten timer would keep
    // damaging the captive on the old cadence.
    this._clearTimer(this._tortureTimer);
    this._tortureTimer = this._scheduleTimeout(() => {
      this._tortureTimer = null;
      if (this._disposed || !this.stateMachine.is(DeviceState.TORTURING) || !this._entityValid()) return;
      this._performDamageCycle();
    }, this.cycleTicks);
  }

  /** Damage the current charge step adds on top of the configured range. */
  get chargeDamageMultiplier() {
    return 1 + this.charge * CONFIG.charge.damageBonusPerStep;
  }

  /**
   * One torture strike, then the wind-up. The soul charge is advanced by each
   * survived strike (not by a second timer), which keeps the escalation exactly
   * in step with the damage cycle: full charge vents as an extra surge strike.
   */
  _performDamageCycle(isSurge = false) {
    const struck = this._strike(isSurge);
    if (!struck) return;

    if (!isSurge) this._escalate();
    this._scheduleNextDamage();
  }

  /**
   * @returns {boolean} False when the cycle must stop (victim gone, reseat
   *   needed, or the frame broke).
   */
  _strike(isSurge) {
    const victim = this._getVictim();
    if (!victim || !this._hasTag(victim, TRAPPED_TAG)) {
      this.release();
      return false;
    }

    // The bug fix: a captive that is not inside its device is never damaged.
    // It is pulled back instead, and released if that keeps failing.
    if (!this._isContained(victim)) {
      const seated = this._reseat(victim, "damage cycle");
      if (!seated) {
        this._lastFailures += 1;
        Debug.warn(this.typeId, `Captive is outside the device; strike skipped (${this._lastFailures})`);
        if (this._lastFailures >= CONFIG.containment.maxFailedReseatCycles) {
          this._notifyVictim(victim, "You slipped free of the device.");
          this.release();
        }
      } else {
        this._lastFailures = 0;
      }
      return false;
    }

    this._lastFailures = 0;
    this._applyHealing(victim);

    const multiplier = Math.pow(this.config.armorDamageMultiplier, this.armorCount)
      * this.chargeDamageMultiplier
      * (isSurge ? CONFIG.charge.surgeMultiplier : 1);
    const isExtreme = rollExtremeDamage(this.config.extremeDamageChance);
    const baseDamage = isExtreme
      ? this.config.extremeDamageAmount
      : randomDamage(this.config.tortureMinDamage, this.config.tortureMaxDamage);
    const health = this._getHealth(victim);
    const survivableDamage = health ? Math.max(0, health.currentValue - 1) : 0;
    const damage = Math.min(Math.floor(baseDamage * multiplier), survivableDamage);

    this._spawnParticles(isExtreme || isSurge ? "extreme" : "normal");
    if (damage > 0) applyDamage(victim, damage, EntityDamageCause.contact);
    this._applyDebuff(victim);
    this._triggerStruggle(CONFIG.struggle.strainDurationTicks, true);
    this._triggerBurst();
    playCue(this._lastDimension, this.position, "hit", this.config);
    this.durability = this.durability - 1;

    if (this.durability <= 0) {
      this.break();
      return false;
    }

    this._applyVignette(victim);
    this._refreshHud(true);
    return true;
  }

  /** Add one charge step; a full meter vents immediately. */
  _escalate() {
    if (!CONFIG.charge.enabled) return;

    this.charge = Math.min(CONFIG.charge.max, this.charge + 1);
    if (this.charge < CONFIG.charge.max) {
      Debug.info(this.typeId, `Soul charge ${this.charge}/${CONFIG.charge.max}`);
      return;
    }
    this._vent();
  }

  /** Full charge: harvest a soul, then tear into the captive one more time. */
  _vent() {
    this._triggerBurst();
    this._spawnBurst(CONFIG.particles.captureBurstCount);
    playCue(this._lastDimension, this.position, "surge", this.config);
    playCue(this._lastDimension, this.position, "soul", this.config);
    Debug.info(this.typeId, `Vented soul charge ${this.charge}/${CONFIG.charge.max}`);
    // Harvest before the surge strike: if that strike breaks the frame, the
    // soul has to be part of the wreck's drop count.
    this.souls = this.souls + 1;
    this._strike(true);
    this.charge = 0;
    this._refreshHud(true);
  }

  // ------------------------------------------------------------------ charge --
  _decayCharge() {
    const now = system.currentTick;
    if (!Number.isFinite(now)) return;
    if (this._nextDecayTick === undefined || this._nextDecayTick === null) {
      this._nextDecayTick = now + CONFIG.charge.decayIntervalTicks;
      return;
    }
    if (now < this._nextDecayTick) return;
    this._nextDecayTick = now + CONFIG.charge.decayIntervalTicks;
    this.charge = this.charge - 1;
  }

  // ----------------------------------------------------------- containment --
  /** Wall-clock seconds the current victim has been held. */
  get captiveSeconds() {
    if (!this.isOccupied) return 0;
    const now = system.currentTick;
    if (!Number.isFinite(now) || !Number.isFinite(this._captureStartedTick)) return 0;
    return Math.max(0, Math.floor((now - this._captureStartedTick) / 20));
  }

  /** True while the victim is inside the device's containment radius. */
  _isContained(victim, margin = 0) {
    if (!isEntityValid(victim) || !this._sameDimension(victim)) return false;
    const position = this.position;
    if (!position) return false;
    const radius = (this.config.containmentRadius ?? CONFIG.containment.defaultRadius) + margin;
    return this._distanceSquared(victim.location, position) <= radius * radius;
  }

  /**
   * Keep the captive where the contraption can be seen holding them.
   * See the class comment for the contract; ``_reseat`` is the recovery path
   * used when drift, knockback or a shove pushes someone out.
   */
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

    if (!this._victimSeated) this._seatVictim(victim);

    const now = system.currentTick;
    const refreshDue = !Number.isFinite(now)
      || now - this._lastSeatRefreshTick >= CONFIG.containment.seatRefreshTicks;
    if (refreshDue) {
      this._lastSeatRefreshTick = now;
      this._refreshSeat(victim);
    }

    const radius = this.config.containmentRadius ?? CONFIG.containment.defaultRadius;
    const distance = Math.sqrt(this._distanceSquared(victim.location, position));
    if (distance <= radius) {
      this._lastFailures = 0;
      this._tickStruggle(distance);
      this._refreshHud(false);
      return;
    }

    if (this._reseat(victim, "drift")) {
      this._lastFailures = 0;
    } else {
      this._lastFailures += 1;
      Debug.warn(this.typeId, `Captive could not be reseated (${this._lastFailures})`);
      if (this._lastFailures >= CONFIG.containment.maxFailedReseatCycles) {
        this._notifyVictim(victim, "You slipped free of the device.");
        this.release();
        return;
      }
    }
    this._refreshHud(true);
  }

  /**
   * Pull a captive back to its seat.
   * @returns {boolean} True when the captive is inside the device afterwards.
   */
  _reseat(victim, reason) {
    if (!isEntityValid(victim) || !this._sameDimension(victim)) return false;

    const seat = this._seatPosition();
    if (!seat) return false;

    const now = system.currentTick;
    const maySnap = !Number.isFinite(now)
      || now - this._lastCorrectionTick >= CONFIG.containment.correctionCooldownTicks;
    const distance = Math.sqrt(this._distanceSquared(victim.location, seat));
    const radius = this.config.containmentRadius ?? CONFIG.containment.defaultRadius;

    // Outside the seat window the captive is snapped straight back (rate
    // limited); inside it, the anchoring impulse is enough.
    const result = anchorEntity(victim, seat, {
      radius,
      snap: maySnap && distance > radius,
    });
    if (result === "snapped") {
      this._lastCorrectionTick = now;
      Debug.info(this.typeId, `Reseated captive (${reason}) from ${distance.toFixed(2)} blocks`);
    }

    // Re-check where the captive actually is: an impulse may need a tick to
    // take effect, so a large drift is reported as still-unseated.
    return this._distanceSquared(victim.location, seat) <= radius * radius;
  }

  /** Re-assert the hold: effect durations tick down and can be dispelled. */
  _refreshSeat(victim) {
    if (!isEntityValid(victim)) return;
    if (victim.typeId === "minecraft:player") {
      // Cheaper re-assert: the original value is already cached, so this is a
      // single engine call and never overwrites the saved permission flag.
      try {
        victim.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, false);
      } catch (_) {}
      return;
    }
    this._freezeMob(victim);
  }

  /**
   * Occasionally make the contraption rattle, so a seated captive still reads
   * as alive. The device animation carries the struggle.
   */
  _tickStruggle(distance = 0) {
    if (!CONFIG.struggle.enabled || this._disposed) return;
    const now = system.currentTick;
    if (!Number.isFinite(now)) return;

    if (this._nextStruggleTick === null) {
      this._nextStruggleTick = now + this._randomStruggleDelay();
      return;
    }
    if (now < this._nextStruggleTick) return;

    this._nextStruggleTick = now + this._randomStruggleDelay();
    // A captive pressed against the frame struggles more often.
    const forced = distance > (this.config.containmentRadius ?? CONFIG.containment.defaultRadius) * 0.7;
    this._triggerStruggle(CONFIG.struggle.strainDurationTicks, forced);
  }

  _randomStruggleDelay() {
    const span = Math.max(1, CONFIG.struggle.maxIntervalTicks - CONFIG.struggle.minIntervalTicks);
    return CONFIG.struggle.minIntervalTicks + Math.floor(Math.random() * span);
  }

  /** Play the device's one-shot strain overlay. */
  _triggerStruggle(ticks = CONFIG.struggle.strainDurationTicks, force = false) {
    if (!CONFIG.struggle.enabled || this._disposed || !this._entityValid()) return;
    if (!this.isOccupied) return;

    const now = system.currentTick;
    if (!force && Number.isFinite(now) && this._strainUntilTick && now < this._strainUntilTick) {
      return;
    }

    const duration = Math.max(1, Math.ceil(ticks));
    this._strainUntilTick = Number.isFinite(now) ? now + duration : null;
    try {
      this.entity.addTag(STRAIN_TAG);
    } catch (_) {
      return;
    }

    this._clearTimer(this._strainTimer);
    this._strainTimer = this._scheduleTimeout(() => {
      this._strainTimer = null;
      this._clearStrain();
    }, duration);

    // A puff of dust at the captive so the rattle reads as them moving.
    const victim = this._getVictim(true);
    if (victim) {
      const dimension = this._lastDimension;
      try {
        dimension?.spawnParticle("minecraft:basic_smoke_particle", {
          x: victim.location.x,
          y: victim.location.y + 0.6,
          z: victim.location.z,
        });
      } catch (_) {}
    }
  }

  /** The short discharge overlay the animation controller plays on a surge. */
  _triggerBurst(ticks = CONFIG.timings.burstAnimationTicks) {
    if (this._disposed || !this._entityValid()) return;
    try {
      this.entity.addTag(BURST_TAG);
    } catch (_) {
      return;
    }
    this._clearTimer(this._burstTimer);
    this._burstTimer = this._scheduleTimeout(() => {
      this._burstTimer = null;
      if (!this._entityValid()) return;
      try { this.entity.removeTag(BURST_TAG); } catch (_) {}
    }, Math.max(1, Math.ceil(ticks)));
  }

  _clearStrain() {
    if (!this._entityValid()) return;
    try { this.entity.removeTag(STRAIN_TAG); } catch (_) {}
    this._strainUntilTick = null;
  }

  _seatVictim(victim) {
    if (!isEntityValid(victim)) return;
    this._victimSeated = true;
    this._victimIsPlayer = victim.typeId === "minecraft:player";

    if (this._victimIsPlayer) {
      this._lockVictimMovement(victim);
    } else {
      this._freezeMob(victim);
    }

    try { this.entity.triggerEvent(DEVICE_SEAT_EVENT); } catch (_) {}
  }

  _unseatVictim(victim) {
    this._victimSeated = false;
    this._clearStrain();
    this._nextStruggleTick = null;
    if (this._entityValid()) {
      try { this.entity.removeTag(BURST_TAG); } catch (_) {}
    }
    this.charge = 0;

    if (isEntityValid(victim)) {
      if (victim.typeId === "minecraft:player") {
        this._restoreVictimMovement(victim);
      } else {
        try { victim.removeEffect(MOB_FREEZE_EFFECT); } catch (_) {}
        try { victim.removeEffect(MOB_BLIND_EFFECT); } catch (_) {}
      }
      stopMotion(victim);
    }

    try { this.entity.triggerEvent(DEVICE_CLEAR_EVENT); } catch (_) {}
  }

  _freezeMob(victim) {
    if (!isEntityValid(victim) || victim.typeId === "minecraft:player") return;
    try {
      victim.addEffect(MOB_FREEZE_EFFECT, CONFIG.containment.mobFreezeDurationTicks, {
        amplifier: CONFIG.containment.mobFreezeAmplifier,
        showParticles: false,
      });
    } catch (_) {}
    try {
      victim.addEffect(MOB_BLIND_EFFECT, CONFIG.containment.mobFreezeDurationTicks, {
        amplifier: 0,
        showParticles: false,
      });
    } catch (_) {}
  }

  _onOpening() {
    this._clearTimer(this._captureTimer);
    this._captureTimer = null;
    this._clearTimer(this._tortureTimer);
    this._tortureTimer = null;
    this._setAnimationState("opening");
    this._spawnBurst(Math.max(2, Math.floor(CONFIG.particles.captureBurstCount / 2)));
    playCue(this._lastDimension, this.position, "latch", this.config);

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
    if (victim) {
      this._notifyVictim(victim, "You have been freed.");
      playCue(this._lastDimension, this.position, "release", this.config);
    }

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
    playCue(this._lastDimension, position, "break", this.config);
    this._dropItem(this._lastDimension, position);
    this._dropSouls(this._lastDimension, position);

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

  /** Harvested souls leave the wreck as a few soul shards. */
  _dropSouls(dimension = this._lastDimension, position = this.position) {
    if (!dimension || !position) return 0;
    const shards = Math.min(
      CONFIG.souls.maxShards,
      Math.floor(this.souls / Math.max(1, CONFIG.souls.perShard)),
    );
    if (shards <= 0) return 0;

    let dropped = 0;
    for (let index = 0; index < shards; index++) {
      try {
        dimension.spawnItem(
          new ItemStack(CONFIG.souls.itemId, 1),
          { x: position.x, y: position.y + 0.4, z: position.z },
        );
        dropped++;
      } catch (error) {
        Debug.error(this.typeId, "Could not drop a soul shard", error);
        break;
      }
    }
    this.souls = this.souls - dropped * CONFIG.souls.perShard;
    return dropped;
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
        // A captive that has genuinely left the device (teleport, portal, far
        // knockback) is released; the leash is far wider than the seat, so
        // ordinary drift is never a release.
        if (!this._sameDimension(candidate)) continue;
        if (!this._isNearDevice(candidate, CONFIG.containment.leashRadius)) continue;
      }
      this._victimEntity = candidate;
      this._victimIsPlayer = candidate.typeId === "minecraft:player";
      return candidate;
    }

    return null;
  }

  _releaseVictim() {
    const victim = this._getVictim(true);
    if (victim) {
      try { victim.removeTag(TRAPPED_TAG); } catch (_) {}
      try { victim.removeTag(CAPTURE_RESERVED_TAG); } catch (_) {}
      this._unseatVictim(victim);
      if (this._sameDimension(victim) && this._isNearDevice(victim, 2)) {
        this._teleportAway(victim);
      }
    } else {
      this._unseatVictim(null);
    }

    this.victimId = null;
    this._victimEntity = null;
    this._lastFailures = 0;
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

  _spawnBurst(count) {
    if (!CONFIG.particles.impactEnabled || !this._entityValid()) return;
    const position = this.position;
    const dimension = this._lastDimension;
    if (!position || !dimension) return;

    const limit = Math.min(Math.max(0, Math.ceil(count)), CONFIG.performance.maxParticlesPerEvent);
    try {
      for (let index = 0; index < limit; index++) {
        dimension.spawnParticle("minecraft:basic_smoke_particle", {
          x: position.x + (Math.random() - 0.5) * 0.9,
          y: position.y + 0.3 + Math.random() * 1.4,
          z: position.z + (Math.random() - 0.5) * 0.9,
        });
      }
    } catch (_) {}
  }

  /**
   * Impact particles for a damage tick. They are emitted *between* the frame
   * and the captive rather than on the device, which is what stopped the
   * device itself from looking like a smoking campfire.
   */
  _spawnParticles(type) {
    if (!this._entityValid()) return;
    const position = this.position;
    const dimension = this._lastDimension;
    if (!position || !dimension) return;

    const victim = this._getVictim(true);
    const origin = victim ? victim.location : position;
    const lerp = (value, target, ratio) => value + (target - value) * ratio;
    const impact = {
      x: lerp(position.x, origin.x, 0.65),
      y: lerp(position.y + 1, origin.y + 1, 0.6),
      z: lerp(position.z, origin.z, 0.65),
    };

    try {
      let emitted = 0;
      const particleLimit = CONFIG.performance.maxParticlesPerEvent;
      if (CONFIG.particles.impactEnabled) {
        const smokeCount = type === "extreme" ? CONFIG.particles.smokeCount * 2 : CONFIG.particles.smokeCount;
        const count = Math.min(smokeCount, particleLimit);
        for (let i = 0; i < count; i++) {
          dimension.spawnParticle("minecraft:basic_smoke_particle", {
            x: impact.x + (Math.random() - 0.5) * 0.7,
            y: impact.y + (Math.random() - 0.5) * 0.5,
            z: impact.z + (Math.random() - 0.5) * 0.7,
          });
          emitted++;
        }
      }

      if (CONFIG.particles.sparkEnabled) {
        const sparkCount = type === "extreme" ? CONFIG.particles.sparkCount * 2 : CONFIG.particles.sparkCount;
        const count = Math.min(sparkCount, Math.max(0, particleLimit - emitted));
        for (let i = 0; i < count; i++) {
          dimension.spawnParticle("minecraft:basic_flame_particle", {
            x: impact.x + (Math.random() - 0.5) * 0.5,
            y: impact.y + (Math.random() - 0.5) * 0.4,
            z: impact.z + (Math.random() - 0.5) * 0.5,
          });
        }
      }
    } catch (_) {}
  }

  _setAnimationState(stateName) {
    if (!this._entityValid()) return;
    this._clearStrain();
    try {
      for (const state of ANIMATION_STATES) {
        this.entity.removeTag(`cc:anim_${state}`);
      }
      this.entity.addTag(`cc:anim_${stateName}`);
    } catch (_) {}
  }

  /** Crack overlays: wear_1..3 light up as durability drops. */
  _updateWearStage(durability = this.durability) {
    if (!this._entityValid()) return;
    const max = Math.max(1, this.maxDurability);
    const ratio = durability / max;
    const stage = ratio > 0.75 ? 0 : ratio > 0.5 ? 1 : ratio > 0.25 ? 2 : 3;

    if (this._wearStage === stage) return;
    this._wearStage = stage;
    for (let index = 0; index < WEAR_STAGES; index++) {
      try {
        if (index === stage) this.entity.addTag(`cc:anim_wear_${index}`);
        else this.entity.removeTag(`cc:anim_wear_${index}`);
      } catch (_) {}
    }
  }

  // -------------------------------------------------------------- redstone --
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

  // ----------------------------------------------------------- interaction --
  /**
   * One interaction entry point, in priority order:
   *
   * 1. an occupied device is always rescued first,
   * 2. armor reinforces an empty device,
   * 3. a matching material repairs a damaged device,
   * 4. a soul shard (sneaking) buys immunity from every device,
   * 5. otherwise the player gets a status read-out.
   */
  onInteract(player, heldItem) {
    if (this._disposed || !isEntityValid(player) || this.stateMachine.is(DeviceState.BROKEN)) return false;

    if (this.isOccupied) {
      if (String(player.id) === String(this.victimId)) {
        this._sendInteractionFeedback(player, "§eYou cannot free yourself. Ask another player to use the device.");
        this._triggerStruggle(CONFIG.struggle.strainDurationTicks, true);
        return false;
      }
      if (!this.release()) return false;
      try {
        player.sendMessage(`§aYou freed the captive from the ${this._displayName()}.`);
      } catch (_) {}
      return true;
    }

    if (heldItem && this._isArmorItem(heldItem.typeId)) {
      return this._reinforce(player, heldItem);
    }

    if (heldItem && this._repairValue(heldItem.typeId) > 0) {
      return this._repair(player, heldItem);
    }

    if (heldItem && heldItem.typeId === CONFIG.souls.itemId && player.isSneaking) {
      return this._buyImmunity(player, heldItem);
    }

    if (this.isReady) {
      const immunity = immunitySecondsLeft(player);
      const ward = immunity > 0 ? ` §d(Warded: ${immunity}s)` : "";
      this._sendInteractionFeedback(
        player,
        `§7${this._displayName()} — ${this.statusLine}${ward}. It activates automatically within §f${this.config.captureRadius.toFixed(1)}§7 blocks. `
        + `Hold armor or an elytra to reinforce, ${this._repairHint()} to repair, or sneak with a soul shard to ward yourself.`,
      );
      return true;
    }

    this._sendInteractionFeedback(player, `§7${this._displayName()} is busy. Try interacting again when it is ready.`);
    return false;
  }

  /**
   * Armor reinforcement.
   *
   * The item is reserved before any state is written, and only removed once the
   * reservation succeeded. v0.1.2 raised the reinforcement count first and
   * consumed the item afterwards, so a failed consumption could grant a free
   * upgrade — and a failed upgrade combined with a successful consumption could
   * eat a piece of armor for nothing.
   */
  _reinforce(player, heldItem) {
    if (this.armorCount >= this.config.armorSlots) {
      this._sendInteractionFeedback(player, "§eThis device cannot be reinforced any further.");
      return false;
    }

    if (!this._consumeHeldItem(player, heldItem)) {
      this._sendInteractionFeedback(player, "§eHold the armor piece in your selected slot to reinforce this device.");
      return false;
    }

    this.armorCount += 1;
    this.durability = this.durability + this.config.armorDurabilityBonus;
    this._setAnimationState(this.stateMachine.state);
    this._spawnBurst(3);
    playCue(this._lastDimension, this.position, "reinforce", this.config);
    Debug.info(this.typeId, `Reinforced (${this.armorCount}/${this.config.armorSlots})`);
    try {
      player.sendMessage(
        `§aReinforced ${this._displayName()} (§f${this.armorCount}/${this.config.armorSlots}§a). `
        + `Durability is now §f${this.durability}/${this.maxDurability}§a.`,
      );
    } catch (_) {}
    return true;
  }

  /** Fraction of max durability a held item restores, or 0 if it is not a material. */
  _repairValue(typeId) {
    const materials = CONFIG.repair.materials[this.config.repairMaterial];
    if (!CONFIG.repair.enabled || !materials) return 0;
    return materials[typeId] ?? 0;
  }

  _repair(player, heldItem) {
    if (this.durability >= this.maxDurability) {
      this._sendInteractionFeedback(player, `§7${this._displayName()} is already at full durability.`);
      return false;
    }

    if (!this._consumeHeldItem(player, heldItem)) {
      this._sendInteractionFeedback(player, "§eHold the repair material in your selected slot to repair this device.");
      return false;
    }

    const amount = Math.max(1, Math.ceil(this.maxDurability * this._repairValue(heldItem.typeId)));
    const before = this.durability;
    this.durability = Math.min(this.maxDurability, before + amount);
    this._spawnBurst(2);
    playCue(this._lastDimension, this.position, "repair", this.config);
    Debug.info(this.typeId, `Repaired ${this.durability - before} durability`);
    try {
      player.sendMessage(
        `§aRepaired ${this._displayName()} (§f${this.durability}/${this.maxDurability}§a, §f+${this.durability - before}§a).`,
      );
    } catch (_) {}
    return true;
  }

  /** Spend one soul shard for temporary immunity from every contraption. */
  _buyImmunity(player, heldItem) {
    if (isImmune(player)) {
      this._sendInteractionFeedback(player, `§dYour ward holds for another ${immunitySecondsLeft(player)}s.`);
      return false;
    }
    if (!this._consumeHeldItem(player, heldItem)) {
      this._sendInteractionFeedback(player, "§eHold the soul shard in your selected slot to spend it.");
      return false;
    }

    if (!grantImmunity(player)) {
      try { player.sendMessage("§cThe soul shard could not bind to you; it was not consumed."); } catch (_) {}
      return false;
    }

    playCue(this._lastDimension, this.position, "soul", this.config);
    try {
      player.sendMessage(
        `§dThe ward takes hold: devices will not claim you for ${Math.round(CONFIG.souls.immunityTicks / 20)}s.`,
      );
    } catch (_) {}
    return true;
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

  /** Human-readable repair materials, derived from the configured set. */
  _repairHint() {
    const samples = Object.keys(CONFIG.repair.materials[this.config.repairMaterial] ?? {});
    if (samples.length === 0) return "nothing";
    const names = samples
      .filter((id) => !id.endsWith("_block") && !id.endsWith("_planks"))
      .slice(0, 2)
      .map((id) => id.replace("minecraft:", "").replace(/_/g, " "));
    const list = names.length > 0 ? names : [samples[0].replace("minecraft:", "").replace(/_/g, " ")];
    return list.length === 1 ? list[0] : `${list[0]} or ${list[1]}`;
  }

  _isArmorItem(typeId) {
    return typeId === "minecraft:elytra"
      || /^minecraft:[a-z0-9_]+_(helmet|chestplate|leggings|boots)$/.test(typeId);
  }

  _displayName() {
    return DEVICE_NAMES[this.typeId] || "Cursed Contraption";
  }

  _sendInteractionFeedback(player, message) {
    if (!isEntityValid(player) || player.typeId !== "minecraft:player") return false;

    const playerId = String(player.id);
    const now = system.currentTick;
    const last = this._interactionFeedbackTicks.get(playerId);
    if (Number.isFinite(last)
      && Number.isFinite(now)
      && now - last < CONFIG.performance.interactionFeedbackCooldownTicks) {
      return false;
    }

    if (!this._interactionFeedbackTicks.has(playerId) && this._interactionFeedbackTicks.size >= 128) {
      const oldestPlayerId = this._interactionFeedbackTicks.keys().next().value;
      if (oldestPlayerId !== undefined) this._interactionFeedbackTicks.delete(oldestPlayerId);
    }
    if (Number.isFinite(now)) this._interactionFeedbackTicks.set(playerId, now);

    try {
      player.sendMessage(message);
      return true;
    } catch (_) {
      return false;
    }
  }

  _notifyVictim(victim, message) {
    if (!isEntityValid(victim) || victim.typeId !== "minecraft:player") return;
    try { victim.sendMessage(`§c[Cursed Contraptions] ${message}`); } catch (_) {}
  }

  /**
   * Action-bar HUD for a captured player: state, time served, soul charge and
   * how to get out. Refreshed on every meaningful change and on a slow timer.
   */
  _refreshHud(force) {
    if (!this.config || !CONFIG.hud.enabled) return;
    const now = system.currentTick;
    let due = force;
    if (!due) {
      if (!Number.isFinite(now)) return;
      if (this._hudTimer !== null && now < this._hudTimer) return;
      due = true;
      this._hudTimer = now + CONFIG.hud.intervalTicks;
    }

    const victim = this._getVictim(true);
    if (!victim || victim.typeId !== "minecraft:player") return;

    const pips = "▮".repeat(this.charge) + "▯".repeat(Math.max(0, CONFIG.charge.max - this.charge));
    const state = this.stateMachine.state.toUpperCase();
    showStatus(
      victim,
      `§c${this._displayName()}§7 | §f${state} §7| §f${this.captiveSeconds}s §7| §f${pips} §7| §aAsk a teammate to use the device`,
    );
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

  /** Where a captive's feet belong: on the device, lifted onto its seat. */
  _seatPosition() {
    const position = this.position;
    if (!position) return null;
    return {
      x: Math.floor(position.x) + 0.5,
      y: position.y,
      z: Math.floor(position.z) + 0.5,
    };
  }

  _teleportToDevice(entity) {
    if (!isEntityValid(entity)) return;
    const seat = this._seatPosition();
    const dimension = this._lastDimension;
    if (!seat || !dimension) return;

    try {
      entity.teleport(seat, { dimension, keepVelocity: false });
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
        entity.teleport(location, { dimension, keepVelocity: false });
        return;
      } catch (_) {}
    }

    try {
      entity.teleport({ x: position.x + 2, y: position.y, z: position.z }, { dimension, keepVelocity: false });
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
    return distanceSquared(first, second);
  }

  // --------------------------------------------------------------- timers --
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
    this._strainTimer = null;
    this._burstTimer = null;
    this._hudTimer = null;
    this._redstoneActivationPending = false;
  }

  // -------------------------------------------------------------- recovery --
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

    if (String(this.victimId) !== id || !this.stateMachine.is(...OCCUPIED_STATES)) return false;

    this._victimEntity = entity;
    try { entity.addTag(TRAPPED_TAG); } catch (_) {}
    this._seatVictim(entity);
    return true;
  }

  /**
   * Clear a stale capture from an entity that no device is holding: drop the
   * tags and give a player their movement back.
   *
   * This is also the death/relog recovery path. A player who dies inside a
   * device leaves the device link behind (the entity is gone), so the movement
   * lock and its saved value have to be released from the player's own state:
   * with no saved value to read, movement is re-enabled, because the only way
   * a player can reach here is after being a captive.
   */
  static clearStaleCapture(entity) {
    if (!isEntityValid(entity)) return;
    try {
      entity.removeTag(TRAPPED_TAG);
      entity.removeTag(CAPTURE_RESERVED_TAG);
    } catch (_) {}

    if (entity.typeId !== "minecraft:player") return;
    let saved;
    try { saved = entity.getDynamicProperty(MOVEMENT_SAVED_PROPERTY); } catch (_) {}
    const restored = typeof saved === "boolean" ? saved : true;
    try { entity.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, restored); } catch (_) {}
    try { entity.setDynamicProperty(MOVEMENT_SAVED_PROPERTY, undefined); } catch (_) {}
  }

  /** True when a player carries capture leftovers that must be repaired. */
  static needsCaptureRecovery(entity) {
    if (!isEntityValid(entity)) return false;
    try {
      if (entity.hasTag(TRAPPED_TAG) || entity.hasTag(CAPTURE_RESERVED_TAG)) return true;
      if (entity.typeId !== "minecraft:player") return false;
      return typeof entity.getDynamicProperty(MOVEMENT_SAVED_PROPERTY) === "boolean";
    } catch (_) {
      return false;
    }
  }

  // ------------------------------------------------------------- lifecycle --
  release() {
    if (this._disposed) return false;

    if (this.stateMachine.is(DeviceState.DETECTING)) {
      const changed = this.stateMachine.transition(DeviceState.IDLE);
      if (changed) this._saveState();
      return changed;
    }

    if (!this.stateMachine.is(...OCCUPIED_STATES)) return false;

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
    if (this.durability <= 0) {
      this.break();
      return true;
    }

    // Hitting the frame makes whoever is inside flinch; an empty device still
    // throws sparks so the hit always reads.
    if (this.isOccupied) this._triggerStruggle(CONFIG.struggle.strainDurationTicks, true);
    else this._spawnBurst(CONFIG.particles.hitBounceCount);
    playCue(this._lastDimension, this.position, "hit", this.config);
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
      this._dropSouls(dimension || this._lastDimension, deathPosition);
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

export { clearImmunity };
