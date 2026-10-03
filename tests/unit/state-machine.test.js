import assert from "node:assert/strict";
import test from "node:test";
import { DeviceState, StateMachine } from "../../behavior_pack/scripts/utils/state-machine.js";

test("device state machine accepts the full capture and rescue path", () => {
  const machine = new StateMachine();
  const transitions = [];
  machine.onTransition(DeviceState.IDLE, (from, to) => transitions.push([from, to]));

  for (const next of [
    DeviceState.DETECTING,
    DeviceState.CAPTURING,
    DeviceState.CLOSED,
    DeviceState.TORTURING,
    DeviceState.OPENING,
    DeviceState.RELEASED,
    DeviceState.IDLE,
  ]) {
    assert.equal(machine.transition(next), true);
  }
  assert.deepEqual(transitions, [[DeviceState.IDLE, DeviceState.DETECTING]]);
  assert.equal(machine.state, DeviceState.IDLE);
});

test("invalid transitions and invalid persisted states fail safely", () => {
  const machine = new StateMachine();
  assert.equal(machine.transition(DeviceState.TORTURING), false);
  assert.equal(machine.transition("unknown"), false);
  assert.equal(StateMachine.deserialize("unknown").state, DeviceState.IDLE);
  assert.equal(machine.forceState("unknown"), false);
  assert.equal(machine.state, DeviceState.IDLE);
});

test("broken is terminal and listeners fire exactly once", () => {
  const machine = new StateMachine(DeviceState.IDLE);
  let brokenCount = 0;
  machine.onTransition(DeviceState.IDLE, (_, to) => {
    if (to === DeviceState.BROKEN) brokenCount++;
  });
  assert.equal(machine.transition(DeviceState.BROKEN), true);
  assert.equal(machine.transition(DeviceState.BROKEN), true);
  assert.equal(machine.transition(DeviceState.IDLE), false);
  assert.equal(brokenCount, 1);
});
