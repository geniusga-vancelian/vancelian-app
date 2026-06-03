/**
 * Clés cache mémoire portail — source unique pour écrans + preview navigation.
 * Incrémenter le suffixe version (v3 → v4) lors d’un changement de forme payload.
 */
export const PORTAL_CACHE_KEYS = {
  markets: 'portal:markets:v3',
  invest: 'portal:invest:v3',
  /** Marchés chargés par le hub invest (paniers / coffres). */
  investMarkets: 'portal:invest-markets:v1',
  profile: 'portal:profile',
  cryptoWallet: 'portal:crypto-wallet',
  academy: 'portal:academy:v5',
} as const

export type PortalScreenCacheKey = (typeof PORTAL_CACHE_KEYS)[keyof typeof PORTAL_CACHE_KEYS]
