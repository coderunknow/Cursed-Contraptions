/**
 * Cursed Contraptions — Torture Device Base Class
 *
 * Owns the complete lifecycle of one device: detection, capture, containment,
 * torture, rescue, damage, persistence, and cleanup.
 *
 * v0.1.5 fixes the underlying defects reported against v0.1.3:
 *  - Mobs were held with Slowness VII (amplifier 6), which only slows mobs by
 *    ~85%; strong mobs could still wander or attack captors. Mobs are now
 *    held with a stack of effects (Slowness 25, Jump Boost -128, Mining
 *    Fatigue V, Weakness IV, Blindness) that fully pins movement, prevents
 *    jumping/attacking/targeting, and works across every vanilla mob.
 *  - The release / broken / open animation timers used global constants
 *    while every device had a different client-side animation length, so
 *    transitions cut off early or held dead air. Per-device timings now
 *    come from config.js and are matched to the client animation lengths.
 *  - Position corrections now use the per-device seat offset so captives
 *    sit *inside* the contraption rather than on its origin corner.
 *  - Vanilla sound events play at every state transition and on hit for
 *    atmosphere (no custom sound assets are shipped).
 *  - Extreme critical hits deal exactly 20 HP (10 hearts) and can kill the
 *    captive outright; standard damage remains capped at 1 HP.
 *  - Proximity detection uses a single entity query (families combined via
 *    exclude filter on the `inanimate` family) instead of two queries per
 *    device, halving the query cost.
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
const STRAIN_TAG = "cc:anim_strain";
const ANIMATION_STATES = Object.freeze(Object.values(DeviceState));

/**
 * Entity events triggered on the behavior entity. These swap component
 * groups so the device hitbox keeps the captive clickable: the rescuer
 * must be able to aim at the frame, not at a captive hidden inside it.
 */
const DEVICE_SEAT_EVENT = "cc:seat_victim";
const DEVICE_CLEAR_EVENT = "cc:clear_victim";

/** Mob containment: a stack of effects that pins every vanilla mob. */
const MOB_EFFECTS = Object.freeze([
  { id: "slowness", amplifierField: "mobFreezeAmplifier" },
  { id: "jump_boost", amplifierField: "mobJumpAmplifier" },
  { id: "mining_fatigue", amplifierField: "mobFatigueAmplifier" },
  { id: "weakness", amplifierField: "mobWeaknessAmplifier" },
  { id: "blindness", amplifierField: "mobBlindnessAmplifier" },
]);

// States in which a device holds a captive.
const OCCUPIED_STATES = Object.freeze([
  DeviceState.CAPTURING,
  DeviceState.CLOSED,
  DeviceState.TORTURING,
]);

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
    this._pendingTargetId = null;
    this._pendingTarget = null;
    this._captureTimer = null;
    this._tortureTimer = null;
    this._redstoneTimer = null;
    this._strainTimer = null;
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
    this._nextStruggleTick = null;
    this._strainUntilTick = null;

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

  /** Seat position where the captive should stand, in world coordinates. */
  get _seatPosition() {
    const position = this.position;
    if (!position) return null;
    const offset = this.config.seatOffset || { x: 0, y: 0, z: 0 };
    return { x: position.x + offset.x, y: position.y + offset.y, z: position.z + offset.z };
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

  /** True while the device is holding a captive. */
  get isOccupied() {
    return this.stateMachine.is(...OCCUPIED_STATES);
  }

  /** Human-readable one-line status used by admin commands and feedback. */
  get statusLine() {
    const armor = this.config.armorSlots > 0
      ? `, reinforced ${this.armorCount}/${this.config.armorSlots}`
      : "";
    return `${this.stateMachine.state} — Durability: ${this.durability}/${this.maxDurability}${armor}`;
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

    if (this.stateMachine.is(...OCCUPIED_STATES)) {
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
    this._seatVictim(this._victimEntity);
    this._setAnimationState("torturing");
    this._applyMobEffects(this._victimEntity);
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

    const dimension = this.entity.dimension;
    /** @type {import('@minecraft/server').Entity[]} */
    let nearby = [];
    try {
      // Single query using the `inanimate` exclusion: we want players and
      // mobs, which is cheaper than two separate family queries per device.
      nearby = dimension.getEntities({
        location: position,
        maxDistance: this.config.captureRadius,
        excludeFamilies: ["inanimate", "cc_device"],
      });
    } catch (_) {
      // Fallback to two family queries if excludeFamilies is unavailable.
      for (const family of ["player", "mob"]) {
        try {
          nearby.push(...dimension.getEntities({
            location: position,
            maxDistance: this.config.captureRadius,
            families: [family],
          }));
        } catch (_) {}
      }
    }

    let closest = null;
    let closestDistance = Infinity;
    for (const target of nearby) {
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
    this._playSound("detect");
    this._spawnBurst(CONFIG.particles.captureBurstCount * 0.5);
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
      target.removeTag(CAPTURE_RESERVED_TAG);
    } catch (_) {}

    this._seatVictim(target);
    this._teleportToSeat(target);
    this._applyMobEffects(target);
    this._saveState();
    this._setAnimationState("capturing");
    this._playSound("close");
    this._spawnBurst(CONFIG.particles.captureBurstCount);
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
    this._spawnBurst(Math.ceil(CONFIG.particles.captureBurstCount * 0.75));
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

  // --------------------------------------------------------------- torture --
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
    let damage;
    if (isExtreme) {
      // Extreme critical hit: a flat 20 HP (10 hearts) that may be lethal.
      damage = Math.floor(this.config.extremeDamageAmount * multiplier);
    } else {
      damage = Math.floor(randomDamage(this.config.tortureMinDamage, this.config.tortureMaxDamage) * multiplier);
      // Standard damage leaves the captive at 1 HP minimum.
      const health = this._getHealth(victim);
      const survivableDamage = health ? Math.max(0, health.currentValue - 1) : 0;
      damage = Math.min(damage, survivableDamage);
    }

    this._playSound("torture");
    this._spawnParticles(isExtreme ? "extreme" : "normal");
    if (damage > 0) applyDamage(victim, damage, EntityDamageCause.contact);
    if (isExtreme && damage > 0) {
      this._notifyVictim(victim, "§cA critical spike pierces you!");
    }
    this._applyMobEffects(victim);
    this._applyDebuff(victim);
    this._triggerStruggle(CONFIG.struggle.strainDurationTicks, true);
    this.durability = this.durability - 1;

    if (this.durability <= 0) {
      this.break();
      return;
    }

    if (CONFIG.vignette.enabled) this._applyVignette(victim);
    this._scheduleNextDamage();
  }

  // ----------------------------------------------------------- containment --
  /**
   * Keep the captive in the seat.
   *
   * v0.1.3 teleported every five ticks and used Slowness VII (amplifier 6),
   * which only slows mobs by ~85%. v0.1.5 uses a stack of effects that pins
   * every vanilla mob (Slowness 25, Jump -128, Mining Fatigue V, Weakness IV,
   * Blindness), and only teleports on a genuine escape — which keeps
   * containment looking tight without the old "judder" stutter.
   */
  _containVictim() {
    const victim = this._getVictim();
    if (!victim || !this._hasTag(victim, TRAPPED_TAG)) {
      this.release();
      return;
    }

    const seat = this._seatPosition;
    const position = this.position;
    if (!seat || !position || !this._sameDimension(victim)) {
      this.release();
      return;
    }

    if (!this._victimSeated) this._seatVictim(victim);

    const now = system.currentTick;
    if (!Number.isFinite(now) || now - this._lastSeatRefreshTick >= CONFIG.containment.seatRefreshTicks) {
      this._lastSeatRefreshTick = now;
      this._refreshSeat(victim);
    }

    const distance = Math.sqrt(this._distanceSquared(victim.location, seat));
    const isPlayer = victim.typeId === "minecraft:player";
    const escapeLimit = isPlayer
      ? CONFIG.containment.playerDriftLimit
      : CONFIG.containment.mobEscapeLimit;

    if (distance > escapeLimit) {
      if (!Number.isFinite(now) || now - this._lastCorrectionTick >= CONFIG.containment.correctionCooldownTicks) {
        this._lastCorrectionTick = now;
        this._teleportToSeat(victim);
        this._triggerStruggle(CONFIG.struggle.strainDurationTicks, true);
        Debug.info(this.typeId, `Captive drifted ${distance.toFixed(2)} blocks; reseated`);
      }
      return;
    }

    this._tickStruggle(distance);
  }

  /** Re-assert the hold: effect durations tick down and can be dispelled. */
  _refreshSeat(victim) {
    if (!isEntityValid(victim)) return;
    if (victim.typeId === "minecraft:player") {
      try {
        victim.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, false);
      } catch (_) {}
      return;
    }
    this._applyMobEffects(victim);
  }

  /**
   * Apply the mob containment stack. Slowness 25+ pins the movement
   * multiplier at zero in Bedrock; Jump -128 prevents jumps/spider climbs;
   * Mining Fatigue V prevents attacks; Weakness IV keeps incidental
   * knockback trivial; Blindness stops target tracking.
   */
  _applyMobEffects(victim) {
    if (!isEntityValid(victim) || victim.typeId === "minecraft:player") return;
    const duration = CONFIG.containment.mobFreezeDurationTicks;
    for (const effect of MOB_EFFECTS) {
      const amplifier = CONFIG.containment[effect.amplifierField];
      try {
        victim.addEffect(effect.id, duration, {
          amplifier,
          showParticles: false,
        });
      } catch (_) {}
    }
  }

  _clearMobEffects(victim) {
    if (!isEntityValid(victim) || victim.typeId === "minecraft:player") return;
    for (const effect of MOB_EFFECTS) {
      try { victim.removeEffect(effect.id); } catch (_) {}
    }
  }

  /**
   * Occasionally make the contraption rattle, so a seated (motionless) captive
   * still reads as alive. The device animation carries the struggle.
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
    const forced = distance > CONFIG.containment.mobDriftLimit;
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
          x: victim.location.x + (Math.random() - 0.5) * 0.4,
          y: victim.location.y + 0.6 + Math.random() * 0.4,
          z: victim.location.z + (Math.random() - 0.5) * 0.4,
        });
      } catch (_) {}
    }
  }

  _clearStrain() {
    if (!this._entityValid()) return;
    try { this.entity.removeTag(STRAIN_TAG); } catch (_) {}
    this._strainUntilTick = null;
  }

  _seatVictim(victim) {
    if (!isEntityValid(victim)) return;
    this._victimSeated = true;

    if (victim.typeId === "minecraft:player") {
      this._lockVictimMovement(victim);
    } else {
      this._applyMobEffects(victim);
    }

    try { this.entity.triggerEvent(DEVICE_SEAT_EVENT); } catch (_) {}
  }

  _unseatVictim(victim) {
    this._victimSeated = false;
    this._clearStrain();
    this._nextStruggleTick = null;

    if (isEntityValid(victim)) {
      if (victim.typeId === "minecraft:player") {
        this._restoreVictimMovement(victim);
      } else {
        this._clearMobEffects(victim);
      }
    }

    try { this.entity.triggerEvent(DEVICE_CLEAR_EVENT); } catch (_) {}
  }

  _onOpening() {
    this._clearTimer(this._captureTimer);
    this._captureTimer = null;
    this._clearTimer(this._tortureTimer);
    this._tortureTimer = null;
    this._setAnimationState("opening");
    this._playSound("open");
    this._spawnBurst(Math.max(2, Math.floor(CONFIG.particles.captureBurstCount / 2)));

    // Per-device open animation length (ticks), not the global default.
    const openTicks = this.config.openTicks ?? CONFIG.timings.openTicks;
    this._scheduleTimeout(() => {
      if (this.stateMachine.state === DeviceState.OPENING) {
        this.stateMachine.transition(DeviceState.RELEASED);
        this._saveState();
      }
    }, openTicks);
  }

  _onReleased() {
    const victim = this._releaseVictim();
    this._setAnimationState("released");
    this._playSound("release");
    if (victim) this._notifyVictim(victim, "§aYou have been freed.");

    const releasedTicks = this.config.releasedTicks ?? CONFIG.timings.releasedTicks;
    this._scheduleTimeout(() => {
      if (this.stateMachine.state === DeviceState.RELEASED) {
        this.stateMachine.transition(DeviceState.IDLE);
        this._saveState();
      }
    }, releasedTicks);
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
    const victim = this._releaseVictim();
    if (victim) this._notifyVictim(victim, "§cThe device shatters and you are thrown free!");
    this._saveState();
    this._setAnimationState("broken");
    this._playSound("break");
    const position = this.position;
    this._spawnBurst(CONFIG.particles.breakBurstCount);
    this._dropItem(this._lastDimension, position);

    const brokenTicks = this.config.brokenTicks ?? CONFIG.timings.brokenTicks;
    this._scheduleTimeout(() => this._removeBrokenEntity(), brokenTicks);
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
        if (!this._isNearDevice(candidate, CONFIG.containment.leashRadius)) continue;
      }
      this._victimEntity = candidate;
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
      if (this._sameDimension(victim)
        && this._isNearDevice(victim, 2)) {
        this._teleportAway(victim);
      }
    } else {
      this._unseatVictim(null);
    }

    this.victimId = null;
    this._victimEntity = null;
    clearProp(this.entity, "victim_id");
    return victim;
  }

  _applyDebuff(entity) {
    if (!isEntityValid(entity) || entity.typeId === "minecraft:player") return;
    // Per-device weakness is layered on top of the containment stack for mobs.
    try {
      entity.addEffect("weakness", this.config.weaknessDuration, {
        amplifier: CONFIG.containment.mobWeaknessAmplifier + (this.config.weaknessAmplifier || 0),
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
          y: position.y + 0.3 + Math.random() * 1.6,
          z: position.z + (Math.random() - 0.5) * 0.9,
        });
      }
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
            y: position.y + 0.5 + Math.random() * 0.8,
            z: position.z + Math.random() - 0.5,
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

  /** Play a sound event at the device location. */
  _playSound(eventKey) {
    if (!CONFIG.sounds.enabled || !this._entityValid()) return;
    const sound = this.config.sounds?.[eventKey];
    if (!sound) return;
    const position = this.position;
    const dimension = this._lastDimension;
    if (!position || !dimension) return;

    const jitter = (Math.random() - 0.5) * 2 * CONFIG.sounds.pitchJitter;
    const pitch = Math.max(0.1, (sound.pitch || 1.0) + jitter);
    const volume = (sound.volume || CONFIG.sounds.volume) * CONFIG.sounds.volume;
    try {
      dimension.playSound(sound.event, position, { volume, pitch });
    } catch (_) {}
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

    if (this.stateMachine.is(DeviceState.IDLE, DeviceState.DETECTING)) {
      this._sendInteractionFeedback(
        player,
        `§7${this._displayName()} — ${this.statusLine}. It activates automatically when a player or mob comes within §f${this.config.captureRadius.toFixed(1)}§7 blocks. Hold armor or an elytra to reinforce it.`,
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
    this._playSound("reinforce");
    this._spawnBurst(4);
    Debug.info(this.typeId, `Reinforced (${this.armorCount}/${this.config.armorSlots})`);
    try {
      player.sendMessage(
        `§aReinforced ${this._displayName()} (§f${this.armorCount}/${this.config.armorSlots}§a). `
        + `Durability is now §f${this.durability}/${this.maxDurability}§a.`,
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

  _isArmorItem(typeId) {
    return typeId === "minecraft:elytra"
      || /^minecraft:[a-z0-9]+_(helmet|chestplate|leggings|boots)$/.test(typeId);
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

  _teleportToSeat(entity) {
    if (!isEntityValid(entity)) return;
    const seat = this._seatPosition;
    const dimension = this._lastDimension;
    if (!seat || !dimension) return;

    try {
      entity.teleport(seat, { dimension, facingLocation: this.position || seat });
    } catch (_) {
      try { entity.teleport(seat, { dimension }); } catch (_) {}
    }
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

    // Audio/visual hit feedback.
    this._playSound("hit");
    if (this.isOccupied) this._triggerStruggle(CONFIG.struggle.strainDurationTicks, true);
    else this._spawnBurst(3);

    if (this.durability <= 0) {
      this.break();
      return true;
    }
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
