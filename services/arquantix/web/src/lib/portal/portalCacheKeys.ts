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

/**
 * Clés cache des sections progressives (chargement indépendant par bloc).
 * Suffixe version à incrémenter en cas de changement de forme.
 */
export const PORTAL_SECTION_CACHE_KEYS = {
  marketsTop: 'portal:markets:top:v1',
  marketsBundles: 'portal:markets:bundles:v1',
  marketsDiscover: 'portal:markets:discover:v1',
  investOffers: 'portal:invest:offers:v1',
  investVaults: 'portal:invest:vaults:v1',
  cryptoWalletPositions: 'portal:crypto-wallet:positions:v1',
  cryptoWalletActivity: 'portal:crypto-wallet:activity:v1',
  academyEditorial: 'portal:academy:editorial:v1',
  academyLibrary: 'portal:academy:library:v1',
} as const
