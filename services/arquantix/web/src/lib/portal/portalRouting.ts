/** Préfixe canonique des routes portail client web (équivalent mobile). */
export const PORTAL_PATH_PREFIX = '/app' as const

export const PORTAL_ROUTES = {
  login: `${PORTAL_PATH_PREFIX}/login`,
  loginVerify: `${PORTAL_PATH_PREFIX}/login/verify`,
  loggedOut: `${PORTAL_PATH_PREFIX}/logged-out`,
  registration: `${PORTAL_PATH_PREFIX}/registration`,
  dashboard: `${PORTAL_PATH_PREFIX}/dashboard`,
  cryptoWallet: `${PORTAL_PATH_PREFIX}/wallet/crypto`,
  savingsWallet: `${PORTAL_PATH_PREFIX}/wallet/savings`,
  walletDeposit: `${PORTAL_PATH_PREFIX}/wallet/deposit`,
  walletDepositSol: `${PORTAL_PATH_PREFIX}/wallet/deposit/sol`,
  walletSwap: `${PORTAL_PATH_PREFIX}/wallet/swap`,
  walletCreate: `${PORTAL_PATH_PREFIX}/wallet/create`,
  myWallets: `${PORTAL_PATH_PREFIX}/wallets`,
  invest: `${PORTAL_PATH_PREFIX}/invest`,
  markets: `${PORTAL_PATH_PREFIX}/markets`,
  marketsAllCrypto: `${PORTAL_PATH_PREFIX}/markets/all-crypto`,
  academy: `${PORTAL_PATH_PREFIX}/academy`,
  design: `${PORTAL_PATH_PREFIX}/design`,
  search: `${PORTAL_PATH_PREFIX}/search`,
  profile: `${PORTAL_PATH_PREFIX}/profile`,
} as const

/** Ancienne route wallets — ancre profil. */
export function portalProfileWalletsRoute(): string {
  return `${PORTAL_ROUTES.profile}#wallets`
}

/** Flow swap LI.FI — destination optionnelle via query (`?to=ETH&toChain=ethereum`). */
export function portalSwapRoute(options?: { to?: string; toChain?: string }): string {
  const base = PORTAL_ROUTES.walletSwap
  const to = options?.to?.trim().toUpperCase()
  if (!to) return base
  const params = new URLSearchParams({ to })
  const chain = options?.toChain?.trim().toLowerCase()
  if (chain) params.set('toChain', chain)
  return `${base}?${params.toString()}`
}

/** Lien dashboard « My accounts » → hub wallet ou inscription EUR. */
export function resolveAccountsRowHref(rowId: string, locked?: boolean): string | undefined {
  if (locked) return PORTAL_ROUTES.registration
  if (rowId === 'crypto') return PORTAL_ROUTES.cryptoWallet
  if (rowId === 'savings') return PORTAL_ROUTES.savingsWallet
  return undefined
}

/** Détail crypto wallet — `/app/wallet/crypto/btc` (position détenue, pas marché seul). */
export function portalCryptoWalletAssetRoute(asset: string): string {
  const ticker = asset.trim().toLowerCase()
  return `${PORTAL_ROUTES.cryptoWallet}/${encodeURIComponent(ticker || 'btc')}`
}

/** Historique complet des transactions d'un actif crypto wallet. */
export function portalCryptoWalletTransactionsRoute(asset: string): string {
  const ticker = asset.trim().toLowerCase()
  return `${portalCryptoWalletAssetRoute(ticker)}/transactions`
}

/** Détail vault épargne — `/app/wallet/savings/0x…`. */
export function portalSavingsVaultRoute(vaultAddress: string): string {
  const normalized = vaultAddress.trim().toLowerCase()
  return `${PORTAL_ROUTES.savingsWallet}/${encodeURIComponent(normalized)}`
}

/** Deposit — adresse EVM si wallet lié, sinon création wallet. */
export function resolvePortalDepositHref(hasPrivyWallet: boolean): string {
  return hasPrivyWallet ? PORTAL_ROUTES.walletDeposit : PORTAL_ROUTES.walletCreate
}

/** Page création wallet Privy — EVM par défaut, Solana via query. */
export function portalWalletCreateRoute(chain: 'evm' | 'solana' = 'evm'): string {
  if (chain === 'solana') return `${PORTAL_ROUTES.walletCreate}?chain=solana`
  return PORTAL_ROUTES.walletCreate
}

/** Page dépôt pour wallets Privy dédiés (Solana, futurs BTC/XRP…). */
export function portalDedicatedDepositRoute(asset: string): string | null {
  const ticker = asset.trim().toUpperCase()
  if (ticker === 'SOL') return PORTAL_ROUTES.walletDepositSol
  return null
}

export function supportsDedicatedPrivyDeposit(asset: string): boolean {
  return portalDedicatedDepositRoute(asset) !== null
}

/** Détail crypto marché — `/app/markets/btc` (aligné Flutter `/crypto/{slug}`). */
export function portalCryptoInstrumentRoute(ticker: string): string {
  const slug = ticker.trim().toLowerCase()
  return `${PORTAL_ROUTES.markets}/${encodeURIComponent(slug || 'btc')}`
}

export type PortalRouteKey = keyof typeof PORTAL_ROUTES

/** Hostname sans port (ex. `app.localhost`, `app.vancelian.com`). */
export function normalizeHost(hostHeader: string | null | undefined): string {
  return (hostHeader ?? '').split(':')[0]?.toLowerCase() ?? ''
}

/**
 * Détecte le sous-domaine portail (`app.*`).
 * En dev local : `app.localhost:3100` ou chemin `/app/*`.
 */
export function isPortalHost(hostHeader: string | null | undefined): boolean {
  const host = normalizeHost(hostHeader)
  if (!host) return false
  if (host.startsWith('app.')) return true
  if (host === 'app') return true
  return false
}

export function isPortalPathname(pathname: string): boolean {
  return pathname === PORTAL_PATH_PREFIX || pathname.startsWith(`${PORTAL_PATH_PREFIX}/`)
}

/**
 * Fichiers servis depuis `public/` — ne pas réécrire sous `/app/*` sur `app.*`.
 * Sans cela, `/crypto_svgs/btc.svg` devient `/app/crypto_svgs/btc.svg` (404).
 */
export function isPortalPublicStaticPathname(pathname: string): boolean {
  if (
    pathname.startsWith('/crypto_svgs/') ||
    pathname.startsWith('/brand/') ||
    pathname.startsWith('/icons/') ||
    pathname.startsWith('/images/') ||
    pathname.startsWith('/app-ds/') ||
    pathname.startsWith('/fonts/')
  ) {
    return true
  }
  return /\.[a-z0-9]{2,5}$/i.test(pathname)
}

/** Login / signup / verify OTP — jamais de topnav site publique. */
export function isPortalAuthPathname(pathname: string): boolean {
  const normalized = pathname.replace(/\/$/, '') || '/'
  return (
    normalized === PORTAL_ROUTES.login ||
    normalized.startsWith(`${PORTAL_ROUTES.login}/`)
  )
}

/** Préfixe canonique admin / CMS builder. */
export const CONSOLE_PATH_PREFIX = '/admin' as const

/** Préfixe des routes d’aperçu site (brouillon CMS), ex. `/preview/home`. */
export const PUBLIC_PREVIEW_PATH_PREFIX = '/preview' as const

/** Routes d’aperçu public CMS — ne doivent pas être réécrites sous `/admin/*` ou `/app/*`. */
export function isPublicPreviewPathname(pathname: string): boolean {
  return (
    pathname === PUBLIC_PREVIEW_PATH_PREFIX ||
    pathname.startsWith(`${PUBLIC_PREVIEW_PATH_PREFIX}/`)
  )
}

/** Aperçu page site complète (`/preview/home`) — exclut les previews isolées (section, email…). */
export function isFullSitePreviewPathname(pathname: string): boolean {
  if (!pathname.startsWith(`${PUBLIC_PREVIEW_PATH_PREFIX}/`)) return false
  const rest = pathname.slice(PUBLIC_PREVIEW_PATH_PREFIX.length + 1)
  if (!rest || rest.includes('/')) return false
  const isolated = new Set([
    'section',
    'section-demo',
    'common-module',
    'email',
    'article',
    'article-block-demo',
  ])
  const head = rest.split('/')[0]
  return head != null && !isolated.has(head)
}

/**
 * Détecte le sous-domaine back-office (`console.*`).
 * Ex. `console.vancelian.finance` → routes `/admin/*`.
 */
export function isConsoleHost(hostHeader: string | null | undefined): boolean {
  const host = normalizeHost(hostHeader)
  if (!host) return false
  if (host.startsWith('console.')) return true
  if (host === 'console') return true
  return false
}

export function isConsolePathname(pathname: string): boolean {
  return pathname === CONSOLE_PATH_PREFIX || pathname.startsWith(`${CONSOLE_PATH_PREFIX}/`)
}

/** Réécrit une URL publique sous-domaine console vers le chemin interne `/admin/…`. */
export function consolePathFromPublicRequest(pathname: string, onConsoleHost: boolean): string {
  if (!onConsoleHost || isConsolePathname(pathname)) {
    return pathname
  }
  if (pathname === '/' || pathname === '') {
    return `${CONSOLE_PATH_PREFIX}/pages`
  }
  return `${CONSOLE_PATH_PREFIX}${pathname}`
}

/** Réécrit une URL publique sous-domaine vers le chemin interne `/app/…`. */
export function portalPathFromPublicRequest(pathname: string, isAppHost: boolean): string {
  if (!isAppHost || isPortalPathname(pathname)) {
    return pathname
  }
  if (pathname === '/' || pathname === '') {
    return PORTAL_ROUTES.dashboard
  }
  return `${PORTAL_PATH_PREFIX}${pathname}`
}
