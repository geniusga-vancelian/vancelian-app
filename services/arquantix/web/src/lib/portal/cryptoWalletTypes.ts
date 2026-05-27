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
  chainType?: string
  chainId?: number | null
  dedicatedWallet?: boolean
  walletAddress?: string
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
  positionType: string
  marketValue?: number
  priceEur?: number
  targetWeight?: number
}

export type PortalMyBundleSummary = {
  portfolioId: string
  portfolioName: string
  status: string
  assetsCount: number
  totalCostBasis: number
  totalMarketValue?: number
  performancePct?: number
  hasHoldings: boolean
  positions?: PortalBundlePosition[]
}

export type PortalCryptoWalletBundleDetailPayload = {
  currency: string
  bundle: PortalMyBundleSummary
  historyPoints: number[]
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
  /** Source des positions affichées (hub = soldes wallet Privy). */
  source?: 'privy'
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
}

/** Aperçu historique sur la page détail position crypto (preview/17). */
export const CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW = 10

export type PortalCryptoWalletDetailPayload = {
  currency: string
  detail: PortalCryptoWalletDetail
  transactions: PortalCryptoWalletTransaction[]
  historyPoints: number[]
  change24hPct?: number
  providerSymbol?: string
  logoUrl?: string | null
  partial?: boolean
}
