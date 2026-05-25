import {
  DEFAULT_PORTAL_CHAIN,
  PORTAL_CHAIN_LABELS,
  type PortalChain,
} from '@/config/portalChains'
import type { PortalCryptoPosition } from '@/lib/portal/cryptoWalletTypes'
import type { PortalCryptoSummary } from '@/lib/portal/dashboardTypes'

const CHAIN_ID_TO_PORTAL: Record<number, PortalChain> = {
  1: 'ethereum',
  8453: 'base',
}

type ChainResolvable = {
  chainType?: string | null
  chainId?: number | null
}

/** Résout l’écosystème portail d’une position (soldes Privy, dépôts, etc.). */
export function resolvePositionPortalChain(position: ChainResolvable): PortalChain | null {
  const chainType = (position.chainType ?? '').trim().toLowerCase()
  if (chainType === 'solana') return 'solana'

  if (position.chainId != null && CHAIN_ID_TO_PORTAL[position.chainId]) {
    return CHAIN_ID_TO_PORTAL[position.chainId]
  }

  if (chainType === 'evm' || chainType === 'ethereum') {
    return 'ethereum'
  }

  return null
}

/** Positions sans réseau explicite — visibles sur Ethereum (mainnet par défaut). */
export function positionMatchesPortalChain(position: ChainResolvable, chain: PortalChain): boolean {
  const resolved = resolvePositionPortalChain(position)
  if (resolved == null) return chain === 'ethereum'
  return resolved === chain
}

export function filterCryptoPositionsByPortalChain(
  positions: PortalCryptoPosition[],
  chain: PortalChain,
): PortalCryptoPosition[] {
  return positions.filter((position) => positionMatchesPortalChain(position, chain))
}

export function filterDashboardCryptoPositions<
  T extends ChainResolvable & {
    asset?: string
    estimated_value_eur?: number | string
    estimated_value_usd?: number | string
  },
>(positions: T[] | undefined, chain: PortalChain): T[] {
  if (!positions?.length) return []
  return positions.filter((position) => positionMatchesPortalChain(position, chain))
}

function toNumber(value: unknown, fallback = 0): number {
  if (value == null) return fallback
  if (typeof value === 'number' && !Number.isNaN(value)) return value
  const parsed = Number(String(value).replace(',', '.'))
  return Number.isNaN(parsed) ? fallback : parsed
}

/** Recalcule le résumé crypto dashboard pour l’écosystème sélectionné. */
export function filterCryptoSummaryByPortalChain(
  crypto: PortalCryptoSummary | null | undefined,
  chain: PortalChain,
): PortalCryptoSummary | null {
  if (!crypto) return null

  const positions = filterDashboardCryptoPositions(crypto.positions, chain)
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

export function filterCryptoPositionsSummaryByPortalChain(
  summary: { positions: PortalCryptoPosition[]; totalValueEur: number; totalValueUsd?: number; positionsCount: number },
  chain: PortalChain,
): typeof summary {
  const positions = filterCryptoPositionsByPortalChain(summary.positions, chain)
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

export function portalChainContextLabel(chain: PortalChain = DEFAULT_PORTAL_CHAIN): string {
  return PORTAL_CHAIN_LABELS[chain]
}

/** Vaults Morpho / Ledgity — Base uniquement. */
export function isPortalChainDeFiEnabled(chain: PortalChain): boolean {
  return chain === 'base'
}

/** Swap LI.FI pilote — Ethereum mainnet uniquement. */
export function isPortalChainSwapEnabled(chain: PortalChain): boolean {
  return chain === 'ethereum'
}

/** Wallet Solana dédié. */
export function isPortalChainSolanaEnabled(chain: PortalChain): boolean {
  return chain === 'solana'
}
