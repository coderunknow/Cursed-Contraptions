export async function resolve(specifier, context, nextResolve) {
  if (specifier === "@minecraft/server") {
    return {
      url: new URL("./mocks/minecraft-server.mjs", import.meta.url).href,
      shortCircuit: true,
    };
  }
  return nextResolve(specifier, context);
}
