/** Préfixe canonique des routes portail client web (équivalent mobile). */
export const PORTAL_PATH_PREFIX = '/app' as const

export const PORTAL_ROUTES = {
  login: `${PORTAL_PATH_PREFIX}/login`,
  loginVerify: `${PORTAL_PATH_PREFIX}/login/verify`,
  loggedOut: `${PORTAL_PATH_PREFIX}/logged-out`,
  registration: `${PORTAL_PATH_PREFIX}/registration`,
  dashboard: `${PORTAL_PATH_PREFIX}/dashboard`,
  cryptoWallet: `${PORTAL_PATH_PREFIX}/wallet/crypto`,
  walletDeposit: `${PORTAL_PATH_PREFIX}/wallet/deposit`,
  walletCreate: `${PORTAL_PATH_PREFIX}/wallet/create`,
  invest: `${PORTAL_PATH_PREFIX}/invest`,
  markets: `${PORTAL_PATH_PREFIX}/markets`,
  design: `${PORTAL_PATH_PREFIX}/design`,
  search: `${PORTAL_PATH_PREFIX}/search`,
  profile: `${PORTAL_PATH_PREFIX}/profile`,
} as const

/** Lien dashboard « My accounts » → hub wallet ou inscription EUR. */
export function resolveAccountsRowHref(rowId: string, locked?: boolean): string | undefined {
  if (locked) return PORTAL_ROUTES.registration
  if (rowId === 'crypto') return PORTAL_ROUTES.cryptoWallet
  return undefined
}

/** Détail crypto wallet — `/app/wallet/crypto/btc` (position détenue, pas marché seul). */
export function portalCryptoWalletAssetRoute(asset: string): string {
  const ticker = asset.trim().toLowerCase()
  return `${PORTAL_ROUTES.cryptoWallet}/${encodeURIComponent(ticker || 'btc')}`
}

/** Deposit — adresse EVM si wallet lié, sinon création wallet. */
export function resolvePortalDepositHref(hasPrivyWallet: boolean): string {
  return hasPrivyWallet ? PORTAL_ROUTES.walletDeposit : PORTAL_ROUTES.walletCreate
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
