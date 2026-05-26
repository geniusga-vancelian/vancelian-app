export type PortalCryptoPosition = {
  asset: string
  name: string
  balance: number
  availableBalance: number
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

export type PortalMyBundleSummary = {
  portfolioId: string
  portfolioName: string
  status: string
  assetsCount: number
  totalCostBasis: number
  totalMarketValue?: number
  performancePct?: number
  hasHoldings: boolean
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
