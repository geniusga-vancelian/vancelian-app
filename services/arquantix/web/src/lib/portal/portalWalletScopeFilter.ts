import type { PortalChain } from '@/config/portalChains'
import type { PortalCryptoPosition } from '@/lib/portal/cryptoWalletTypes'
import type { PortalCryptoSummary } from '@/lib/portal/dashboardTypes'
import {
  filterCryptoPositionsByPortalChain,
  filterCryptoSummaryByPortalChain,
} from '@/lib/portal/portalChainFilter'
import type { PortalWalletScope } from '@/lib/portal/portalWalletScopeTypes'

function normalizeAddress(value: string): string {
  const trimmed = value.trim()
  if (trimmed.startsWith('0x')) return trimmed.toLowerCase()
  return trimmed
}

function addressesEqual(a: string, b: string): boolean {
  return normalizeAddress(a) === normalizeAddress(b)
}

type WalletFilterable = {
  walletAddress?: string | null
  chainType?: string | null
  portfolioScope?: string | null
}

/** Filtre une position par wallet actif (Privy embedded vs externe). */
export function positionMatchesWalletScope(
  position: WalletFilterable,
  scope: PortalWalletScope | null,
): boolean {
  if (!scope) return true

  if (scope.kind === 'external_evm') {
    if (!position.walletAddress) return false
    return addressesEqual(position.walletAddress, scope.address)
  }

  if (scope.chainType === 'solana') {
    return (position.chainType ?? '').trim().toLowerCase() === 'solana'
  }

  if (position.walletAddress) {
    return addressesEqual(position.walletAddress, scope.address)
  }

  const scopeLabel = position.portfolioScope?.trim().toLowerCase()
  return scopeLabel === 'privy' || scopeLabel === 'merged' || !scopeLabel
}

export function filterCryptoPositionsByWalletScope(
  positions: PortalCryptoPosition[],
  scope: PortalWalletScope | null,
): PortalCryptoPosition[] {
  if (!scope) return positions
  return positions.filter((position) => positionMatchesWalletScope(position, scope))
}

function toNumber(value: unknown, fallback = 0): number {
  if (value == null) return fallback
  if (typeof value === 'number' && !Number.isNaN(value)) return value
  const parsed = Number(String(value).replace(',', '.'))
  return Number.isNaN(parsed) ? fallback : parsed
}

export function filterCryptoSummaryByWalletScope(
  crypto: PortalCryptoSummary | null | undefined,
  scope: PortalWalletScope | null,
): PortalCryptoSummary | null {
  if (!crypto) return null
  if (!scope) return crypto

  const positions = (crypto.positions ?? []).filter((position) =>
    positionMatchesWalletScope(
      {
        walletAddress:
          typeof position.wallet_address === 'string' ? position.wallet_address : undefined,
        chainType: typeof position.chain_type === 'string' ? position.chain_type : undefined,
        portfolioScope:
          typeof position.portfolio_scope === 'string' ? position.portfolio_scope : undefined,
      },
      scope,
    ),
  )

  const totalValueEur = positions.reduce(
    (sum, position) => sum + toNumber(position.estimated_value_eur),
    0,
  )
  const totalValueUsd = positions.reduce(
    (sum, position) => sum + toNumber(position.estimated_value_usd),
    0,
  )

  return {
    summary: {
      total_value_eur: totalValueEur,
      total_value_usd: totalValueUsd > 0 ? totalValueUsd : undefined,
      positions_count: positions.length,
    },
    positions,
  }
}

export function filterCryptoSummaryByPortalScope(
  crypto: PortalCryptoSummary | null | undefined,
  chain: PortalChain,
  scope: PortalWalletScope | null,
): PortalCryptoSummary | null {
  const chainFiltered = filterCryptoSummaryByPortalChain(crypto, chain)
  return filterCryptoSummaryByWalletScope(chainFiltered, scope)
}

export function filterCryptoPositionsSummaryByPortalScope(
  summary: {
    positions: PortalCryptoPosition[]
    totalValueEur: number
    totalValueUsd?: number
    positionsCount: number
  },
  chain: PortalChain,
  scope: PortalWalletScope | null,
): typeof summary {
  const chainPositions = filterCryptoPositionsByPortalChain(summary.positions, chain)
  const positions = scope
    ? chainPositions.filter((position) => positionMatchesWalletScope(position, scope))
    : chainPositions

  const totalValueEur = positions.reduce(
    (sum, position) => sum + (position.estimatedValueEur ?? 0),
    0,
  )
  const totalValueUsd = positions.reduce(
    (sum, position) => sum + (position.estimatedValueUsd ?? 0),
    0,
  )

  return {
    ...summary,
    positions,
    positionsCount: positions.length,
    totalValueEur,
    totalValueUsd: totalValueUsd > 0 ? totalValueUsd : undefined,
  }
}

export function portalWalletScopeContextLabel(scope: PortalWalletScope | null): string {
  if (!scope) return 'Aucun wallet'
  return scope.label
}

export function portalWalletScopeShortLabel(scope: PortalWalletScope | null): string {
  if (!scope) return 'Wallet'
  return scope.shortLabel
}

/** DeFi on-chain : wallet externe ou Privy selon sélection navbar. */
export function isPortalScopeExternal(scope: PortalWalletScope | null): boolean {
  return scope?.kind === 'external_evm'
}
