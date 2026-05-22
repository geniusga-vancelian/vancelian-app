type CacheEntry<T> = { data: T; expiresAt: number }

const store = new Map<string, CacheEntry<unknown>>()

export class PortalFetchError extends Error {
  status: number

  constructor(status: number) {
    super(`portal_fetch_${status}`)
    this.status = status
  }
}

export type PortalCacheBootstrap<T> = {
  data: T | null
  hasInitialData: boolean
  isFresh: boolean
}

function getEntry<T>(key: string): CacheEntry<T> | null {
  const entry = store.get(key)
  if (!entry) return null
  return entry as CacheEntry<T>
}

/** Lecture cache frais uniquement (TTL respecté). */
export function readPortalCache<T>(key: string): T | null {
  const entry = getEntry<T>(key)
  if (!entry || Date.now() > entry.expiresAt) return null
  return entry.data
}

/** Bootstrap synchrone — inclut les entrées expirées (stale-while-revalidate). */
export function getPortalCacheBootstrap<T>(key: string): PortalCacheBootstrap<T> {
  const entry = getEntry<T>(key)
  if (!entry) {
    return { data: null, hasInitialData: false, isFresh: false }
  }
  return {
    data: entry.data,
    hasInitialData: true,
    isFresh: Date.now() <= entry.expiresAt,
  }
}

export function writePortalCache<T>(key: string, data: T, ttlMs = 90_000): void {
  store.set(key, { data, expiresAt: Date.now() + ttlMs })
}

export function invalidatePortalCache(key?: string): void {
  if (key) store.delete(key)
  else store.clear()
}

/** GET réseau + mise à jour cache (revalidation explicite). */
export async function revalidatePortalCache<T>(
  key: string,
  url: string,
  ttlMs = 90_000,
): Promise<T> {
  const res = await fetch(url, { credentials: 'include' })
  if (res.status === 401) throw new PortalFetchError(401)
  if (!res.ok) throw new PortalFetchError(res.status)

  const data = (await res.json()) as T
  writePortalCache(key, data, ttlMs)
  return data
}

/** GET JSON portail avec cache mémoire (stale-while-revalidate entre onglets). */
export async function fetchPortalCached<T>(
  key: string,
  url: string,
  options?: { ttlMs?: number; force?: boolean },
): Promise<{ data: T; fromCache: boolean }> {
  const force = options?.force ?? false
  const ttlMs = options?.ttlMs ?? 90_000

  if (!force) {
    const cached = readPortalCache<T>(key)
    if (cached) return { data: cached, fromCache: true }
  }

  const data = await revalidatePortalCache<T>(key, url, ttlMs)
  return { data, fromCache: false }
}
