type CacheEntry<T> = { data: T; expiresAt: number }

const store = new Map<string, CacheEntry<unknown>>()

/** Timeout client BFF — doit couvrir les agrégations lourdes (crypto + épargne). */
const PORTAL_CLIENT_FETCH_TIMEOUT_MS = 55_000
const PORTAL_CLIENT_RETRY_DELAY_MS = 800
const RETRYABLE_PORTAL_STATUS = new Set([500, 502, 503, 504])

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

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isRetryablePortalError(err: unknown): boolean {
  if (err instanceof PortalFetchError) {
    return RETRYABLE_PORTAL_STATUS.has(err.status)
  }
  return true
}

async function portalClientFetch(url: string): Promise<Response> {
  return fetch(url, {
    credentials: 'include',
    signal: AbortSignal.timeout(PORTAL_CLIENT_FETCH_TIMEOUT_MS),
  })
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

/**
 * Invalidation hiérarchique : supprime la clé exacte ET toutes ses sous-clés
 * (`key:*`). Permet aux invalidations historiques (`portal:crypto-wallet`,
 * `portal:dashboard`, `portal:markets`) de couvrir les caches de section
 * progressifs (`portal:crypto-wallet:positions:v1:<scope>`, etc.).
 * Sans argument : vide tout le cache.
 */
export function invalidatePortalCache(key?: string): void {
  if (!key) {
    store.clear()
    return
  }
  store.delete(key)
  const childPrefix = `${key}:`
  for (const existingKey of store.keys()) {
    if (existingKey.startsWith(childPrefix)) store.delete(existingKey)
  }
}

/** GET réseau + mise à jour cache (revalidation explicite, 1 retry sur erreurs transitoires). */
export async function revalidatePortalCache<T>(
  key: string,
  url: string,
  ttlMs = 90_000,
): Promise<T> {
  let lastError: unknown

  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await portalClientFetch(url)
      if (res.status === 401) throw new PortalFetchError(401)
      if (!res.ok) {
        const err = new PortalFetchError(res.status)
        if (attempt === 0 && isRetryablePortalError(err)) {
          await sleep(PORTAL_CLIENT_RETRY_DELAY_MS)
          continue
        }
        throw err
      }

      const data = (await res.json()) as T
      writePortalCache(key, data, ttlMs)
      return data
    } catch (err) {
      lastError = err
      if (err instanceof PortalFetchError && err.status === 401) throw err
      if (attempt === 0 && isRetryablePortalError(err)) {
        await sleep(PORTAL_CLIENT_RETRY_DELAY_MS)
        continue
      }
      throw err
    }
  }

  throw lastError
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
