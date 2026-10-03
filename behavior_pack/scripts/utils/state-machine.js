/**
 * Cursed Contraptions — State Machine
 * 
 * A centralized, serializable state machine for torture devices.
 * State is persisted via entity dynamic properties so it survives
 * chunk unload/reload and server restarts.
 */

export const DeviceState = Object.freeze({
  IDLE:       "idle",
  DETECTING:  "detecting",
  CAPTURING:  "capturing",
  CLOSED:     "closed",
  TORTURING:  "torturing",
  OPENING:    "opening",
  RELEASED:   "released",
  DAMAGED:    "damaged",
  BROKEN:     "broken",
});

/**
 * Valid state transitions. Each key can only transition to the listed states.
 * This prevents impossible jumps (e.g. IDLE → TORTURING without closing).
 */
const VALID_TRANSITIONS = {
  [DeviceState.IDLE]:      [DeviceState.DETECTING, DeviceState.DAMAGED, DeviceState.BROKEN],
  [DeviceState.DETECTING]: [DeviceState.CAPTURING, DeviceState.IDLE, DeviceState.DAMAGED, DeviceState.BROKEN],
  [DeviceState.CAPTURING]: [DeviceState.CLOSED, DeviceState.OPENING, DeviceState.DAMAGED, DeviceState.BROKEN],
  [DeviceState.CLOSED]:    [DeviceState.TORTURING, DeviceState.OPENING, DeviceState.DAMAGED, DeviceState.BROKEN],
  [DeviceState.TORTURING]: [DeviceState.OPENING, DeviceState.CLOSED, DeviceState.DAMAGED, DeviceState.BROKEN],
  [DeviceState.OPENING]:   [DeviceState.RELEASED, DeviceState.DAMAGED, DeviceState.BROKEN],
  [DeviceState.RELEASED]:  [DeviceState.IDLE, DeviceState.DAMAGED, DeviceState.BROKEN],
  [DeviceState.DAMAGED]:   [DeviceState.BROKEN, DeviceState.IDLE],
  [DeviceState.BROKEN]:    [],
};

export class StateMachine {
  constructor(initialState = DeviceState.IDLE) {
    this._state = initialState;
    this._listeners = new Map();
  }

  get state() {
    return this._state;
  }

  /**
   * Attempt a state transition. Returns true if valid, false otherwise.
   * Fires registered listeners on success.
   */
  transition(newState) {
    if (this._state === newState) return true; // Already in this state
    const allowed = VALID_TRANSITIONS[this._state] || [];
    if (!allowed.includes(newState)) {
      return false;
    }
    const oldState = this._state;
    this._state = newState;
    this._fireListeners(oldState, newState);
    return true;
  }

  /**
   * Force a state (used only during deserialization / chunk reload recovery).
   * Bypasses transition validation — use with care.
   */
  forceState(newState) {
    const oldState = this._state;
    this._state = newState;
    if (oldState !== newState) {
      this._fireListeners(oldState, newState);
    }
  }

  /**
   * Register a listener for transitions from a specific state.
   * callback(fromState, toState)
   */
  onTransition(fromState, callback) {
    if (!this._listeners.has(fromState)) {
      this._listeners.set(fromState, []);
    }
    this._listeners.get(fromState).push(callback);
  }

  _fireListeners(from, to) {
    const list = this._listeners.get(from);
    if (list) {
      for (const cb of list) {
        try { cb(from, to); } catch (_) { /* swallow */ }
      }
    }
  }

  is(...states) {
    return states.includes(this._state);
  }

  serialize() {
    return this._state;
  }

  static deserialize(data) {
    const sm = new StateMachine();
    if (data && Object.values(DeviceState).includes(data)) {
      sm.forceState(data);
    }
    return sm;
  }
}
