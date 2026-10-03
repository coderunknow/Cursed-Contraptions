/**
 * Cursed Contraptions — dev-only GameTest pack.
 *
 * This pack is NEVER part of the shipped .mcaddon. It targets beta script
 * modules on purpose (GameTest is beta-only) and must run in a test world
 * with the "Beta APIs" experiment enabled. See tests/GAMETESTS.md for the
 * full world setup and run instructions.
 *
 * Written against @minecraft/server-gametest@1.0.0-beta.1.21.60-preview.24
 * typings (the 1.21.60 target) and @minecraft/server 1.17.0-beta.
 */
import { EntityDamageCause, GameMode, InputPermissionCategory, ItemStack } from "@minecraft/server";
import { register } from "@minecraft/server-gametest";

const DEVICE_ID = "cc:iron_maiden";
const DEVICE_ITEM = "cc:item_iron_maiden";
const SUITE_TAG = "cc:all";

// Relative block coordinates inside each 12x12x12 test structure.
const HOME = { x: 5, y: 1, z: 5 }; // device
const INSIDE = { x: 6, y: 1, z: 5 }; // 1 block away: inside the 1.5 capture radius
const OUTSIDE = { x: 8, y: 1, z: 5 }; // 3 blocks away: outside the radius
const AWAY = { x: 10, y: 1, z: 10 }; // capture-cancel distance
const POWER_TOP = { x: 5, y: 2, z: 5 }; // directly above the device block

// The behavior pack registers freshly loaded device entities after a
// chunk-load grace period, so every test waits this long before acting.
const REGISTER_TICKS = 50;
// captureDelay(20) + closeDuration(30) + closedPause(10), plus margin.
const CAPTURE_TICKS = 80;

function deviceState(device) {
  try {
    return String(device.getProperty("cc:state"));
  } catch (_) {
    return "<unreadable>";
  }
}

function assertDeviceState(test, device, accepted, context) {
  if (!accepted.includes(deviceState(device))) {
    test.fail(`${context}: expected state ${accepted.join("/")}, got ${deviceState(device)}`);
  }
}

function spawnDevice(test) {
  return test.spawnAtLocation(DEVICE_ID, test.worldLocation(HOME));
}

function dropCount(test) {
  return test.getDimension().getEntities({ type: DEVICE_ITEM, location: test.worldLocation(HOME), maxDistance: 8 }).length;
}

register("cc", "capture_rescue", (test) => {
  const device = spawnDevice(test);
  const victim = test.spawnSimulatedPlayer(test.worldLocation(INSIDE), "victim", GameMode.survival);
  const rescuer = test.spawnSimulatedPlayer(test.worldLocation(OUTSIDE), "rescuer", GameMode.survival);

  test.startSequence()
    .thenIdle(REGISTER_TICKS)
    .thenIdle(CAPTURE_TICKS)
    .thenExecute(() => {
      assertDeviceState(test, device, ["capturing", "closed", "torturing"], "after capture delay");
      if (!victim.hasTag("cc:trapped")) test.fail("victim should carry the cc:trapped tag");
      if (victim.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.Movement)) {
        test.fail("captured victim movement should be disabled");
      }
    })
    .thenExecute(() => {
      if (!rescuer.interactWithEntity(device)) test.fail("rescue interaction was not accepted");
    })
    .thenIdle(60) // release animation + settle
    .thenExecute(() => {
      assertDeviceState(test, device, ["idle"], "after rescue");
      if (victim.hasTag("cc:trapped")) test.fail("victim should be released after rescue");
      if (!victim.inputPermissions.isPermissionCategoryEnabled(InputPermissionCategory.Movement)) {
        test.fail("rescued victim movement should be restored");
      }
    })
    .thenSucceed();
}).maxTicks(600).tag(SUITE_TAG);

register("cc", "escape_cancels", (test) => {
  const device = spawnDevice(test);
  const victim = test.spawnSimulatedPlayer(test.worldLocation(INSIDE), "escapist", GameMode.survival);

  test.startSequence()
    .thenIdle(REGISTER_TICKS)
    .thenIdle(15) // capture delay is 20; still inside the escape window
    .thenExecute(() => {
      assertDeviceState(test, device, ["detecting"], "before the escape");
      victim.teleport(test.worldLocation(AWAY));
    })
    .thenIdle(40) // capture delay would have finished by now
    .thenExecute(() => {
      assertDeviceState(test, device, ["idle"], "after escaping the capture radius");
      if (victim.hasTag("cc:trapped") || victim.hasTag("cc:capture_reserved")) {
        test.fail("escaped victim must not keep capture tags");
      }
    })
    .thenSucceed();
}).maxTicks(300).tag(SUITE_TAG);

register("cc", "reinforce_consumes", (test) => {
  const device = spawnDevice(test);
  const player = test.spawnSimulatedPlayer(test.worldLocation(OUTSIDE), "engineer", GameMode.survival);

  test.startSequence()
    .thenIdle(REGISTER_TICKS)
    .thenExecute(() => {
      const container = player.getComponent("minecraft:inventory")?.container;
      container.setItem(0, new ItemStack("minecraft:iron_helmet", 1));
      player.selectedSlotIndex = 0;
      if (!player.interactWithEntity(device)) test.fail("reinforce interaction was not accepted");
    })
    .thenIdle(2)
    .thenExecute(() => {
      if (Number(device.getProperty("cc:armor_count")) !== 1) test.fail("armor_count should be 1 after reinforcing");
      const container = player.getComponent("minecraft:inventory")?.container;
      if (container.getItem(0) !== undefined) test.fail("the armor piece should have been consumed");
      if (Number(device.getProperty("cc:durability")) !== 250) {
        test.fail(`durability should be 200+50 after one armor piece, got ${device.getProperty("cc:durability")}`);
      }
    })
    .thenSucceed();
}).maxTicks(300).tag(SUITE_TAG);

register("cc", "break_drop", (test) => {
  const device = spawnDevice(test);

  test.startSequence()
    .thenIdle(REGISTER_TICKS)
    .thenExecute(() => {
      if (dropCount(test) !== 0) test.fail("no device item should exist before the break");
      if (!device.applyDamage(250, { cause: EntityDamageCause.contact })) test.fail("damage was not applied");
    })
    .thenExecute(() => {
      assertDeviceState(test, device, ["broken"], "after lethal damage");
      if (dropCount(test) !== 1) test.fail(`break should drop exactly one device item, found ${dropCount(test)}`);
    })
    .thenIdle(40) // brokenAnimationTicks = 30, then the entity is removed
    .thenExecute(() => {
      test.assertEntityPresent(DEVICE_ID, HOME, 2, false);
      if (dropCount(test) !== 1) test.fail("no duplicate drops from entity removal");
    })
    .thenSucceed();
}).maxTicks(300).tag(SUITE_TAG);

register("cc", "creative_immunity", (test) => {
  const device = spawnDevice(test);
  const player = test.spawnSimulatedPlayer(test.worldLocation(INSIDE), "builder", GameMode.creative);

  test.startSequence()
    .thenIdle(REGISTER_TICKS + CAPTURE_TICKS)
    .thenExecute(() => {
      assertDeviceState(test, device, ["idle"], "with only a creative player nearby");
      if (player.hasTag("cc:trapped") || player.hasTag("cc:capture_reserved")) {
        test.fail("creative players must be immune to capture");
      }
    })
    .thenSucceed();
}).maxTicks(300).tag(SUITE_TAG);

register("cc", "redstone_triggered", (test) => {
  const device = spawnDevice(test);
  const victim = test.spawnSimulatedPlayer(test.worldLocation(OUTSIDE), "target", GameMode.survival);

  test.startSequence()
    .thenIdle(REGISTER_TICKS)
    .thenExecute(() => {
      // Negative control: power on, but the only target is out of the
      // capture radius, so the redstone request must not activate anything.
      test.setBlockType("minecraft:redstone_block", POWER_TOP);
    })
    .thenIdle(25) // redstoneActivationDelay(10) + poll margin
    .thenExecute(() => {
      assertDeviceState(test, device, ["idle"], "with power but no in-range target");
    })
    .thenExecute(() => {
      // Re-trigger the rising edge with the target now inside the radius.
      test.setBlockType("minecraft:air", POWER_TOP);
      victim.teleport(test.worldLocation(INSIDE));
    })
    .thenIdle(3)
    .thenExecute(() => {
      test.setBlockType("minecraft:redstone_block", POWER_TOP);
    })
    .thenIdle(15) // redstoneActivationDelay(10) + poll interval margin
    .thenExecute(() => {
      assertDeviceState(test, device, ["detecting", "capturing"], "after redstone activation");
    })
    .thenSucceed();
}).maxTicks(400).tag(SUITE_TAG);
