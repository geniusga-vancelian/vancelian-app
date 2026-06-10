export type PortalLombardWalletPositionOverlay = {
  lockedCollateralAmount: number
  lockedCollateralSymbol: string
  borrowedUsdcAmount: number
  /** true when local mock simulates USDC credit not yet reflected in Privy balances */
  simulatePrivyCredit: boolean
}

export type PortalCryptoPosition = {
  asset: string
  name: string
  balance: number
  availableBalance: number
  lombard?: PortalLombardWalletPositionOverlay
  priceEur?: number
  estimatedValueEur?: number
  priceUsd?: number
  estimatedValueUsd?: number
  performance1dPct?: number
  iconKey: string
  /** Symbole provider marché (ex. ETHUSDT) — logos alignés page Markets. */
  providerSymbol?: string
  logoUrl?: string | null
  portfolioScope?: string
  privyBalance?: number
  platformBalance?: number
  /** PE scope trading_available — max investissable vault (Phase 3A). */
  tradingAvailable?: number
  chainType?: string
  chainId?: number | null
  dedicatedWallet?: boolean
  walletAddress?: string
  /** Solde ERC-20 on-chain (Base) — min avec ledger pour swap spendable. */
  onChainBalance?: number
  /** MAX swap officiel — min(on-chain Base, ledger − collateral) via /portfolio/breakdown. */
  swappableBalance?: number
}

export type PortalCryptoPositionsSummary = {
  totalValueEur: number
  totalValueUsd?: number
  positionsCount: number
  positions: PortalCryptoPosition[]
}

export type PortalBundlePosition = {
  asset: string
  quantity: number
  costBasis: number
  costBasisUsd?: number
  positionType: string
  marketValue?: number
  marketValueUsd?: number
  priceEur?: number
  priceUsd?: number
  targetWeight?: number
}

export type PortalMyBundleSummary = {
  portfolioId: string
  portfolioName: string
  status: string
  assetsCount: number
  totalCostBasis: number
  totalCostBasisUsd?: number
  totalMarketValue?: number
  totalMarketValueUsd?: number
  performancePct?: number
  hasHoldings: boolean
  positions?: PortalBundlePosition[]
}

export type PortalCryptoWalletBundleDetailPayload = {
  currency: string
  bundle: PortalMyBundleSummary
  historyPoints: number[]
  transactions: PortalCryptoWalletTransaction[]
  partial?: boolean
}

export type PortalCryptoWalletRow =
  | {
      kind: 'position'
      value: number
      position: PortalCryptoPosition
    }
  | {
      kind: 'bundle'
      value: number
      bundle: PortalMyBundleSummary
    }

export type PortalCryptoWalletHubPayload = {
  currency: string
  positions: PortalCryptoPositionsSummary
  bundles: PortalMyBundleSummary[]
  historyPoints: number[]
  performance?: {
    totalPnl: number
    performancePct: number
  } | null
  /** Source des positions affichées (hub = direct_portfolio PE / Mon Trading). */
  source?: 'direct' | 'privy'
  /** PE trading_available USDC (avant overlay Lombard) — max déposable vault USDC. */
  tradingAvailableUsdc?: number
  /** PE trading_available EURC (avant overlay Lombard) — max déposable vault EURC. */
  tradingAvailableEurc?: number
  partial?: boolean
}

export type PortalCryptoWalletDetail = {
  asset: string
  name: string
  iconKey: string
  volume: string
  currentPriceEur?: number
  currentPriceUsd?: number
  totalValueEur: number
  totalValueUsd?: number
  avgBuyPriceEur?: number
  avgBuyPriceUsd?: number
  averagePurchasePrice?: number
  costBasis?: number
  unrealizedGainEur?: number
  unrealizedGainUsd?: number
  unrealizedGains?: number
  unrealizedGainsPct?: number
  realizedGainEur: number
  realizedGainUsd?: number
  realizedGains: number
  totalGainEur?: number
  totalGainUsd?: number
  totalGains?: number
  totalGainsPct?: number
  portfolioScope?: string
  privyBalance?: number
  platformBalance?: number
  lombard?: PortalLombardWalletPositionOverlay
  /** Human-readable available amount (detail screen). */
  availableVolume?: string
  /** Human-readable locked Lombard collateral (detail screen). */
  lockedVolume?: string
}

export type PortalCryptoWalletTransaction = {
  id: string
  side: string
  asset: string
  amountCrypto: string
  amountFiat: string
  price: string
  currency: string
  status: string
  createdAt: string
  title: string
  subtitle: string
  direction: string
  transactionKind?: string
  sourceSystem?: string
  fromAsset?: string
  toAsset?: string
  swapAmountFrom?: string
  swapAmountTo?: string
  txHash?: string
  portfolioScope?: string
  bundleBatchId?: string
  legsCount?: number
  successfulLegsCount?: number
  failedLegsCount?: number
  expandableLegs?: PortalBundleAllocationLeg[]
}

export type PortalBundleAllocationLeg = {
  fromAsset: string
  toAsset: string
  amountIn: string
  amountOut: string
  status: string
  legId?: string
  txHash?: string
}

/** Aperçu historique sur la page détail position crypto (preview/17). */
export const CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW = 10

import type { PortalMarketsNewsItem } from '@/lib/portal/marketsTypes'
import type { PortalCryptoPositionMarketQuote } from '@/lib/portal/cryptoPositionDetailFormat'

export type PortalCryptoWalletDetailPayload = {
  currency: string
  detail: PortalCryptoWalletDetail
  transactions: PortalCryptoWalletTransaction[]
  historyPoints: number[]
  performance?: {
    totalPnl: number
    performancePct: number
  } | null
  change24hPct?: number
  providerSymbol?: string
  logoUrl?: string | null
  marketQuote?: PortalCryptoPositionMarketQuote | null
  news?: PortalMarketsNewsItem[]
  partial?: boolean
}
