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
  walletWithdraw: `${PORTAL_PATH_PREFIX}/wallet/withdraw`,
  walletSwap: `${PORTAL_PATH_PREFIX}/wallet/swap`,
  walletCreate: `${PORTAL_PATH_PREFIX}/wallet/create`,
  myWallets: `${PORTAL_PATH_PREFIX}/wallets`,
  invest: `${PORTAL_PATH_PREFIX}/invest`,
  borrow: `${PORTAL_PATH_PREFIX}/borrow`,
  creditLine: `${PORTAL_PATH_PREFIX}/credit-line`,
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

export type PortalSwapRouteOptions = {
  /** Buy flow — destination asset already known. */
  to?: string
  toChain?: string
  /** Sell flow — source asset already known. */
  from?: string
  fromChain?: string
}

/** Flow swap LI.FI — query `to` (buy) or `from` (sell) pour sauter une étape de sélection. */
export function portalSwapRoute(options?: PortalSwapRouteOptions): string {
  const base = PORTAL_ROUTES.walletSwap
  if (!options) return base

  const params = new URLSearchParams()
  const to = options.to?.trim().toUpperCase()
  const from = options.from?.trim().toUpperCase()
  if (to) params.set('to', to)
  if (from) params.set('from', from)
  const toChain = options.toChain?.trim().toLowerCase()
  const fromChain = options.fromChain?.trim().toLowerCase()
  if (toChain) params.set('toChain', toChain)
  if (fromChain) params.set('fromChain', fromChain)

  const query = params.toString()
  return query ? `${base}?${query}` : base
}

export function portalSwapBuyRoute(asset: string, chain?: string): string {
  return portalSwapRoute({ to: asset, toChain: chain })
}

export function portalSwapSellRoute(asset: string, chain?: string): string {
  return portalSwapRoute({ from: asset, fromChain: chain })
}

export type PortalBorrowRouteOptions = {
  collateral: string
}

/** Flow Lombard — query `collateral=cbBTC|cbETH` pour pré-sélectionner la garantie. */
export function portalBorrowRoute(options?: PortalBorrowRouteOptions): string {
  const base = PORTAL_ROUTES.borrow
  if (!options?.collateral?.trim()) return base

  const params = new URLSearchParams()
  params.set('collateral', options.collateral.trim())
  return `${base}?${params.toString()}`
}

export type PortalLombardPositionRouteOptions = {
  marketId?: string
  collateral?: string
}

/** Détail read-only d'un emprunt Lombard actif. */
export function portalLombardPositionRoute(options?: PortalLombardPositionRouteOptions): string {
  const base = `${PORTAL_ROUTES.borrow}/position`
  if (!options) return base

  const params = new URLSearchParams()
  if (options.marketId?.trim()) params.set('marketId', options.marketId.trim())
  if (options.collateral?.trim()) params.set('collateral', options.collateral.trim())
  const query = params.toString()
  return query ? `${base}?${query}` : base
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

/** Détail bundle wallet — `/app/wallet/crypto/bundle/{portfolioId}`. */
export function portalCryptoWalletBundleRoute(portfolioId: string): string {
  const id = portfolioId.trim()
  return `${PORTAL_ROUTES.cryptoWallet}/bundle/${encodeURIComponent(id)}`
}

/** Historique complet des transactions d'un actif crypto wallet. */
export function portalCryptoWalletTransactionsRoute(asset: string): string {
  const ticker = asset.trim().toLowerCase()
  return `${portalCryptoWalletAssetRoute(ticker)}/transactions`
}

/** Détail d'une transaction crypto wallet — handoff Transaction.html. */
export function portalCryptoWalletTransactionRoute(asset: string, txId: string): string {
  const ticker = asset.trim().toLowerCase()
  const id = encodeURIComponent(txId.trim())
  return `${portalCryptoWalletTransactionsRoute(ticker)}/${id}`
}

/** Détail d'une transaction bundle wallet. */
export function portalCryptoWalletBundleTransactionRoute(
  portfolioId: string,
  txId: string,
): string {
  const id = portfolioId.trim()
  const tx = encodeURIComponent(txId.trim())
  return `${portalCryptoWalletBundleRoute(id)}/transactions/${tx}`
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

/** Détail offre exclusive — `/app/invest/{slug}`. */
export function portalExclusiveOfferRoute(slug: string): string {
  const normalized = slug.trim()
  return normalized
    ? `${PORTAL_ROUTES.invest}/${encodeURIComponent(normalized)}`
    : PORTAL_ROUTES.invest
}

/** Flow investissement vault — `/app/invest/{slug}/invest` (comme wallet/swap pour le buy). */
export function portalVaultInvestRoute(
  slug: string,
  mode: PortalVaultFlowMode = 'invest',
): string {
  const base = `${portalExclusiveOfferRoute(slug)}/invest`
  return mode === 'withdraw' ? `${base}?mode=withdraw` : base
}

/** Investissement DeFi Morpho — page dédiée (Privy stable via layout vault). */
export function portalMorphoVaultInvestRoute(
  vaultAddress: string,
  mode: PortalVaultFlowMode = 'invest',
): string {
  const address = vaultAddress.trim().toLowerCase()
  const base = `${PORTAL_ROUTES.invest}/vault/morpho/${encodeURIComponent(address)}`
  return mode === 'withdraw' ? `${base}?mode=withdraw` : base
}

/** Investissement DeFi Ledgity — page dédiée. */
export function portalLedgityVaultInvestRoute(
  vaultId: string,
  mode: PortalVaultFlowMode = 'invest',
): string {
  const id = vaultId.trim()
  const base = `${PORTAL_ROUTES.invest}/vault/ledgity/${encodeURIComponent(id)}`
  return mode === 'withdraw' ? `${base}?mode=withdraw` : base
}

export type PortalVaultFlowMode = 'invest' | 'withdraw'

export function parsePortalVaultFlowMode(value: string | null | undefined): PortalVaultFlowMode {
  return value === 'withdraw' ? 'withdraw' : 'invest'
}

type PortalDefiVaultFlowTarget = {
  integrationMode: 'direct_morpho' | 'ledgity_vault'
  vaultAddress: string
  /** Identifiant portail (Morpho/Ledgity). */
  vaultId: string
}

/** Route invest/retrait DeFi (Morpho ou Ledgity) depuis n’importe quel écran portail. */
export function resolvePortalDefiVaultFlowRoute(
  vault: PortalDefiVaultFlowTarget,
  mode: PortalVaultFlowMode = 'invest',
  options?: { returnTo?: 'savings' },
): string {
  const base =
    vault.integrationMode === 'ledgity_vault'
      ? portalLedgityVaultInvestRoute(vault.vaultAddress, mode)
      : portalMorphoVaultInvestRoute(vault.vaultAddress, mode)
  if (options?.returnTo === 'savings') {
    return `${base}${base.includes('?') ? '&' : '?'}from=savings`
  }
  return base
}

type PortalVaultEngineRouteInput = {
  portal_config_id?: string | null
  integration_mode?: string | null
  vault_address?: string | null
}

function normalizePortalVaultIntegrationMode(
  value: string | null | undefined,
): 'direct_morpho' | 'ledgity_vault' | null {
  const mode = value?.trim()
  if (mode === 'ledgity_vault' || mode === 'direct_morpho') return mode
  return null
}

/** Route invest catalogue depuis un snapshot moteur VAULT_ENGINE. */
export function resolvePortalVaultEngineInvestRoute(
  engine: PortalVaultEngineRouteInput | null | undefined,
  slug: string,
  mode: PortalVaultFlowMode = 'invest',
): string {
  const vaultAddress = engine?.vault_address?.trim().toLowerCase()
  const integrationMode = normalizePortalVaultIntegrationMode(engine?.integration_mode)

  if (integrationMode === 'ledgity_vault' && vaultAddress) {
    return portalLedgityVaultInvestRoute(vaultAddress, mode)
  }
  if (integrationMode === 'direct_morpho' && vaultAddress) {
    return portalMorphoVaultInvestRoute(vaultAddress, mode)
  }
  return portalVaultInvestRoute(slug, mode)
}

type PortalVaultProductRouteInput = {
  slug: string
  vaultEngineConfigId: string | null
  vaultAddress: string | null
  integrationMode: string | null
}

/** Route invest pour un produit catalogue `vault_simple` (moteur plateforme ou fallback lending). */
export function resolvePortalVaultProductInvestRoute(
  vault: PortalVaultProductRouteInput,
  mode: PortalVaultFlowMode = 'invest',
): string {
  const vaultAddress = vault.vaultAddress?.trim().toLowerCase()
  const integrationMode = normalizePortalVaultIntegrationMode(vault.integrationMode)

  if (integrationMode === 'ledgity_vault' && vaultAddress) {
    return portalLedgityVaultInvestRoute(vaultAddress, mode)
  }
  if (integrationMode === 'direct_morpho' && vaultAddress) {
    return portalMorphoVaultInvestRoute(vaultAddress, mode)
  }
  return portalVaultInvestRoute(vault.slug, mode)
}

export type PortalBundleInvestFrom = 'markets' | 'invest'

/** Invest / retrait bundle crypto (portfolio PE provisionné). */
export function portalBundleInvestRoute(
  portfolioId: string,
  mode: PortalVaultFlowMode = 'invest',
  options?: { from?: PortalBundleInvestFrom },
): string {
  const id = portfolioId.trim()
  const base = `${PORTAL_ROUTES.invest}/bundle/${encodeURIComponent(id)}`
  const params = new URLSearchParams()
  if (mode === 'withdraw') params.set('mode', 'withdraw')
  if (options?.from === 'markets') params.set('from', 'markets')
  const query = params.toString()
  return query ? `${base}?${query}` : base
}

/** Invest bundle depuis le catalogue produit (fallback si pas encore de portfolio). */
export function portalBundleProductInvestRoute(
  productCode: string,
  mode: PortalVaultFlowMode = 'invest',
  options?: { portfolioId?: string | null },
): string {
  const code = productCode.trim().toUpperCase()
  const portfolioId = options?.portfolioId?.trim()
  if (portfolioId) {
    return portalBundleInvestRoute(portfolioId, mode)
  }
  const base = `${PORTAL_ROUTES.invest}/bundle/product/${encodeURIComponent(code)}`
  return mode === 'withdraw' ? `${base}?mode=withdraw` : base
}

/** Détail produit crypto bundle (catalogue Markets / Placer) — layout Panier.html. */
export function portalCryptoBundleProductRoute(
  productCode: string,
  options?: { back?: 'invest' },
): string {
  const code = productCode.trim().toUpperCase()
  const base = `${PORTAL_ROUTES.markets}/bundle/${encodeURIComponent(code)}`
  if (options?.back === 'invest') {
    return `${base}?back=invest`
  }
  return base
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
