const PROD_MARKET_DATA_BASE = 'https://api.arquantix.com'

/** Hostnames portail prod → API publique (WS + logos). Évite le fallback `:8000` sur app.*. */
function resolveProdMarketDataBase(hostname: string): string | null {
  const host = hostname.toLowerCase()
  if (host === 'app.vancelian.finance' || host === 'console.vancelian.finance') {
    return PROD_MARKET_DATA_BASE
  }
  if (host.endsWith('.vancelian.finance') || host.endsWith('.arquantix.com')) {
    return PROD_MARKET_DATA_BASE
  }
  return null
}

/**
 * Base URL market-data accessible depuis le navigateur (logos + WebSocket).
 * Aligné sur Flutter `Config.marketDataBaseUrl` / `resolveLogoUrl`.
 */
export function getMarketDataPublicBaseUrl(): string {
  const fromEnv =
    process.env.NEXT_PUBLIC_BACKEND_URL?.trim() ||
    process.env.NEXT_PUBLIC_MARKET_DATA_URL?.trim()
  if (fromEnv) return fromEnv.replace(/\/$/, '')

  if (typeof window !== 'undefined') {
    const { hostname } = window.location
    const prodBase = resolveProdMarketDataBase(hostname)
    if (prodBase) return prodBase
    const { protocol } = window.location
    return `${protocol}//${hostname}:8000`.replace(/\/$/, '')
  }

  return 'http://127.0.0.1:8000'
}

/** Préfixe une URL relative `/media/crypto_logos/...` avec la base FastAPI publique. */
export function resolveMarketDataLogoUrl(
  logoUrl: string | null | undefined,
  baseUrl = getMarketDataPublicBaseUrl(),
): string | null {
  if (!logoUrl?.trim()) return null
  const u = logoUrl.trim()
  if (/^https?:\/\//i.test(u)) return u
  const base = baseUrl.replace(/\/$/, '')
  return `${base}${u.startsWith('/') ? u : `/${u}`}`
}

export function buildMarketDataWsUrl(symbols: string[], baseUrl = getMarketDataPublicBaseUrl()): string {
  const normalized = symbols
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean)
    .join(',')
  const wsBase = baseUrl.replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://')
  return `${wsBase.replace(/\/$/, '')}/ws/market-data?symbols=${encodeURIComponent(normalized)}`
}
