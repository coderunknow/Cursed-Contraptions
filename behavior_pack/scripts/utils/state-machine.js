/**
 * Cursed Contraptions — State Machine
 *
 * Centralized device state transitions with serialization support.
 */

export const DeviceState = Object.freeze({
  IDLE: "idle",
  DETECTING: "detecting",
  CAPTURING: "capturing",
  CLOSED: "closed",
  TORTURING: "torturing",
  OPENING: "opening",
  RELEASED: "released",
  BROKEN: "broken",
});

const VALID_TRANSITIONS = Object.freeze({
  [DeviceState.IDLE]: [DeviceState.DETECTING, DeviceState.BROKEN],
  [DeviceState.DETECTING]: [DeviceState.CAPTURING, DeviceState.IDLE, DeviceState.BROKEN],
  [DeviceState.CAPTURING]: [DeviceState.CLOSED, DeviceState.OPENING, DeviceState.BROKEN],
  [DeviceState.CLOSED]: [DeviceState.TORTURING, DeviceState.OPENING, DeviceState.BROKEN],
  [DeviceState.TORTURING]: [DeviceState.OPENING, DeviceState.BROKEN],
  [DeviceState.OPENING]: [DeviceState.RELEASED, DeviceState.BROKEN],
  [DeviceState.RELEASED]: [DeviceState.IDLE, DeviceState.BROKEN],
  [DeviceState.BROKEN]: [],
});

export class StateMachine {
  constructor(initialState = DeviceState.IDLE) {
    this._state = Object.values(DeviceState).includes(initialState)
      ? initialState
      : DeviceState.IDLE;
    this._listeners = new Map();
  }

  get state() {
    return this._state;
  }

  transition(newState) {
    if (this._state === newState) return true;
    const allowed = VALID_TRANSITIONS[this._state] || [];
    if (!allowed.includes(newState)) return false;

    const oldState = this._state;
    this._state = newState;
    this._fireListeners(oldState, newState);
    return true;
  }

  /** Used only to recover a valid state from persisted world data. */
  forceState(newState) {
    if (!Object.values(DeviceState).includes(newState)) return false;
    const oldState = this._state;
    this._state = newState;
    if (oldState !== newState) this._fireListeners(oldState, newState);
    return true;
  }

  onTransition(fromState, callback) {
    if (!Object.values(DeviceState).includes(fromState) || typeof callback !== "function") {
      return false;
    }
    const listeners = this._listeners.get(fromState) || [];
    listeners.push(callback);
    this._listeners.set(fromState, listeners);
    return true;
  }

  _fireListeners(from, to) {
    const listeners = this._listeners.get(from) || [];
    for (const callback of [...listeners]) {
      try {
        callback(from, to);
      } catch (_) {
        // One extension callback must not prevent the remaining listeners.
      }
    }
  }

  is(...states) {
    return states.includes(this._state);
  }

  serialize() {
    return this._state;
  }

  static deserialize(value) {
    return new StateMachine(
      Object.values(DeviceState).includes(value) ? value : DeviceState.IDLE
    );
  }
}
