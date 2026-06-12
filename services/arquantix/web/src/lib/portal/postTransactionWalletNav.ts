import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime'

import { PortalFetchError } from '@/lib/portal/portalClientCache'
import { PORTAL_SECTION_CACHE_KEYS } from '@/lib/portal/portalCacheKeys'
import { appendPortalScopeQuery, buildPortalScopeCacheSuffix } from '@/lib/portal/portalScopeQuery'
import type { PortalWalletScope } from '@/lib/portal/portalWalletScopeTypes'
import {
  PORTAL_ROUTES,
  portalCryptoWalletAssetRoute,
  portalCryptoWalletBundleRoute,
  portalSavingsVaultRoute,
} from '@/lib/portal/portalRouting'
import type { PortalChain } from '@/config/portalChains'

const DEFAULT_PREFETCH_ATTEMPTS = 4
const PREFETCH_RETRY_DELAY_MS = 700

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Ticker canonique pour routes wallet (CBETH, USDC, cbETH → CBETH). */
export function normalizePostTransactionWalletAsset(asset: string): string {
  return asset.trim().toUpperCase()
}

async function fetchAssetDetailOk(
  asset: string,
  options: { chain: PortalChain; walletScope: PortalWalletScope | null },
): Promise<boolean> {
  const ticker = normalizePostTransactionWalletAsset(asset)
  const url = appendPortalScopeQuery(
    `/api/portal/crypto-wallet/${encodeURIComponent(ticker)}`,
    options.chain,
    options.walletScope,
  )
  const res = await fetch(url, { credentials: 'include', cache: 'no-store' })
  return res.ok
}

/**
 * Attend que le BFF détail actif soit prêt (settlement / indexation hub).
 * Évite l’écran d’erreur immédiat après une tx réussie.
 */
export async function prefetchCryptoWalletAssetAfterTransaction(
  asset: string,
  options: {
    chain: PortalChain
    walletScope: PortalWalletScope | null
    maxAttempts?: number
  },
): Promise<boolean> {
  const attempts = options.maxAttempts ?? DEFAULT_PREFETCH_ATTEMPTS
  for (let i = 0; i < attempts; i += 1) {
    try {
      if (await fetchAssetDetailOk(asset, options)) return true
    } catch {
      /* retry */
    }
    if (i < attempts - 1) {
      await sleep(PREFETCH_RETRY_DELAY_MS * (i + 1))
    }
  }
  return false
}

export type PostTransactionWalletTarget =
  | { kind: 'crypto_asset'; asset: string }
  | { kind: 'crypto_bundle'; portfolioId: string }
  | { kind: 'savings_vault'; vaultAddress: string }
  | { kind: 'crypto_hub' }

/**
 * Navigation post-succès transaction — prefetch + fallback hub si lag API.
 */
export async function navigateAfterTransactionSuccess(
  router: AppRouterInstance,
  target: PostTransactionWalletTarget,
  options?: {
    chain?: PortalChain
    walletScope?: PortalWalletScope | null
    walletScopeId?: string | null
    invalidateCaches?: boolean
  },
): Promise<void> {
  const chain = options?.chain ?? 'ethereum'
  const walletScope = options?.walletScope ?? null
  const scopeSuffix = buildPortalScopeCacheSuffix(chain, options?.walletScopeId ?? null)

  if (target.kind === 'crypto_asset') {
    const ticker = normalizePostTransactionWalletAsset(target.asset)
    const ready = await prefetchCryptoWalletAssetAfterTransaction(ticker, {
      chain,
      walletScope,
    })
    const href = ready
      ? portalCryptoWalletAssetRoute(ticker)
      : PORTAL_ROUTES.cryptoWallet

    if (options?.invalidateCaches !== false) {
      const { invalidatePortalCache } = await import('@/lib/portal/portalClientCache')
      invalidatePortalCache(`portal:crypto-wallet:${scopeSuffix}`)
      invalidatePortalCache(`${PORTAL_SECTION_CACHE_KEYS.cryptoWalletPositions}:${scopeSuffix}`)
      invalidatePortalCache(PORTAL_SECTION_CACHE_KEYS.cryptoWalletActivity)
      if (ready) {
        invalidatePortalCache(`portal:crypto-wallet:${ticker}:${scopeSuffix}`)
        invalidatePortalCache(`portal:crypto-wallet:${ticker}:core:${scopeSuffix}`)
        invalidatePortalCache(`portal:crypto-wallet:${ticker}:activity:${scopeSuffix}`)
      }
    }

    router.push(href)
    return
  }

  if (target.kind === 'crypto_bundle') {
    const { invalidatePortalCache } = await import('@/lib/portal/portalClientCache')
    invalidatePortalCache(`portal:crypto-wallet:${scopeSuffix}`)
    invalidatePortalCache(`${PORTAL_SECTION_CACHE_KEYS.cryptoWalletPositions}:${scopeSuffix}`)
    invalidatePortalCache(PORTAL_SECTION_CACHE_KEYS.cryptoWalletActivity)
    invalidatePortalCache(`portal:crypto-wallet:bundle:${target.portfolioId}:${scopeSuffix}`)
    router.push(portalCryptoWalletBundleRoute(target.portfolioId))
    return
  }

  if (target.kind === 'savings_vault') {
    router.push(portalSavingsVaultRoute(target.vaultAddress))
    return
  }

  router.push(PORTAL_ROUTES.cryptoWallet)
}

/** Erreur fetch portail exploitable pour fallback UI. */
export function isPortalWalletNotFoundError(err: unknown): boolean {
  return err instanceof PortalFetchError && err.status === 404
}
