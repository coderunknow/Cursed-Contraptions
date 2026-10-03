let currentTick = 0;
let nextHandle = 1;
const scheduled = new Map();
const entities = new Map();
const dimensions = new Map();

/**
 * Mirrors the stable 1.17.0 event-signal shape: subscribe(callback, options?)
 * returns the callback, unsubscribe removes it. `fire` and `subscriberCount`
 * are test-only dispatch helpers and are not part of the real API surface.
 */
class MockEventSignal {
  constructor() {
    this.subscribers = new Set();
  }

  subscribe(callback, options) {
    if (typeof callback !== "function") throw new TypeError("callback must be a function");
    const entry = { callback, options };
    this.subscribers.add(entry);
    return callback;
  }

  unsubscribe(callback) {
    for (const entry of this.subscribers) {
      if (entry.callback === callback) this.subscribers.delete(entry);
    }
  }

  subscriberCount() {
    return this.subscribers.size;
  }

  fire(payload) {
    for (const { callback, options } of [...this.subscribers]) {
      if (options?.namespaces) {
        const namespace = String(payload?.id ?? "").split(":")[0];
        if (!options.namespaces.includes(namespace)) continue;
      }
      callback(payload);
    }
  }
}

export const EntityDamageCause = Object.freeze({ contact: "contact" });
export const InputPermissionCategory = Object.freeze({ Movement: "movement" });

export const world = {
  // Stable 1.17.0 has no world.beforeEvents.chatSend.
  beforeEvents: {},
  afterEvents: {
    entityDie: new MockEventSignal(),
    entityHurt: new MockEventSignal(),
    entityLoad: new MockEventSignal(),
    playerInteractWithEntity: new MockEventSignal(),
    playerLeave: new MockEventSignal(),
    playerPlaceBlock: new MockEventSignal(),
    playerSpawn: new MockEventSignal(),
  },
  getEntity(id) { return entities.get(String(id)); },
  registerEntity(entity) { entities.set(String(entity.id), entity); },
  getDimension(id) {
    const dimension = dimensions.get(String(id));
    if (!dimension) throw new Error(`Unknown dimension: ${id}`);
    return dimension;
  },
  registerDimension(dimension) { dimensions.set(String(dimension.id), dimension); },
  sendMessage() {},
};

export const system = {
  afterEvents: {
    scriptEventReceive: new MockEventSignal(),
  },
  run(callback) { return this.runTimeout(callback, 1); },
  runTimeout(callback, ticks) {
    const handle = nextHandle++;
    scheduled.set(handle, {
      handle,
      callback,
      interval: 0,
      due: currentTick + Math.max(1, Math.ceil(ticks)),
    });
    return handle;
  },
  runInterval(callback, ticks) {
    const handle = nextHandle++;
    const interval = Math.max(1, Math.ceil(ticks));
    scheduled.set(handle, { handle, callback, interval, due: currentTick + interval });
    return handle;
  },
  clearRun(handle) { scheduled.delete(handle); },
};

export class ItemStack {
  constructor(typeId, amount = 1) {
    this.typeId = typeId;
    this.amount = amount;
  }
  setAmount(amount) {
    if (!Number.isInteger(amount) || amount < 1 || amount > 64) throw new RangeError("invalid amount");
    this.amount = amount;
  }
}

export function resetSystem() {
  currentTick = 0;
  nextHandle = 1;
  scheduled.clear();
  entities.clear();
  dimensions.clear();
}

export function advanceTicks(ticks) {
  const endTick = currentTick + ticks;
  while (true) {
    const next = [...scheduled.values()]
      .filter((task) => task.due <= endTick)
      .sort((first, second) => first.due - second.due || first.handle - second.handle)[0];
    if (!next) break;

    currentTick = next.due;
    if (next.interval > 0) next.due += next.interval;
    else scheduled.delete(next.handle);
    next.callback();
  }
  currentTick = endTick;
}
