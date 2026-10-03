let currentTick = 0;
let nextHandle = 1;
const scheduled = new Map();
const entities = new Map();

export const EntityDamageCause = Object.freeze({ contact: "contact" });
export const InputPermissionCategory = Object.freeze({ Movement: "movement" });

export const world = {
  getEntity(id) { return entities.get(String(id)); },
  registerEntity(entity) { entities.set(String(entity.id), entity); },
  sendMessage() {},
};

export const system = {
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

export function pendingTimerCount() {
  return scheduled.size;
}
