/**
 * Résout `params` des App Router (Next 14 : objet • Next 15+ : `Promise` du même type).
 */
export async function awaitRouteParams<T extends object>(params: T | Promise<T>): Promise<T> {
  return await Promise.resolve(params)
}
