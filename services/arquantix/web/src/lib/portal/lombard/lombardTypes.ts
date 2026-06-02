import type { LombardCollateralSymbol } from '@/lib/portal/lombard/lombardConfig'

export type LombardSafetyLevel = 'comfortable' | 'monitor' | 'risky' | 'blocked'

export type LombardMarketSummary = {
  marketId: string
  collateral: LombardCollateralSymbol
  collateralName: string
  borrowAsset: 'USDC'
  chain: 'base'
  chainId: number
  borrowApyPercent: number | null
  liquidationLltvPercent: number | null
  maxUserLtvPercent: number
  poweredBy: 'Morpho'
  collateralTokenAddress: string
  loanTokenAddress: string
  collateralDecimals: number
  loanDecimals: number
}

export type LombardBorrowCapacity = {
  marketId: string
  collateral: LombardCollateralSymbol
  collateralName: string
  targetLtvPercent: number
  maxBorrowAmount: string
  maxBorrowAmountRaw: string
  absoluteMaxBorrowAmount: string
  recommendedBorrowAmount: string
  walletGuaranteeBalance: string
  borrowApyPercent: number | null
  liquidationLltvPercent: number | null
  maxUserLtvPercent: number
  poweredBy: 'Morpho'
}

export type LombardQuoteResult = {
  marketId: string
  collateral: LombardCollateralSymbol
  collateralName: string
  targetLtvPercent: number
  borrowAmount: string
  borrowAmountRaw: string
  guaranteeAmount: string
  guaranteeAmountRaw: string
  projectedLtvPercent: number
  safetyLevel: LombardSafetyLevel
  safetyLabel: string
  safetyMessage: string
  maxBorrowAmount: string
  recommendedBorrowAmount: string
  borrowApyPercent: number | null
  liquidationLltvPercent: number | null
  walletGuaranteeBalance: string
  poweredBy: 'Morpho'
  warnings?: LombardSafetyWarning[]
}

export type LombardSafetyWarning = {
  code: 'lombard.high_ltv_warning'
  message: string
  projectedLtvPercent: number
}

export type LombardPreparedTx = {
  to: string
  data: string
  value: string
  chainId: number
  operation: 'approve' | 'authorize' | 'open_loan'
}

export type LombardPreparePayload = {
  transactions: LombardPreparedTx[]
  ledgerEntries: Array<{ id: string; operation: string; txIndex: number }>
  groupKey: string
  idempotencyKey: string
  quote: LombardQuoteResult
  logicalBorrowId?: string
  serverCompleted?: boolean
  mockExecution?: boolean
}

export type LombardConfirmPayload = {
  groupKey: string
  results: Array<{ ledgerEntryId: string; txHash: string }>
}

export type LombardMarketsPayload = {
  enabled: boolean
  markets: LombardMarketSummary[]
  maxUserLtvPercent: number
  poweredBy: 'Morpho'
  mock?: boolean
  beta?: {
    limitsEnabled: boolean
    allowlistConfigured: boolean
    limits: { maxBorrowUsdcPerWallet: number; maxTotalBorrowUsdcGlobal: number } | null
  }
}

export type LombardExecutionPhase =
  | 'idle'
  | 'preparing'
  | 'authorizing'
  | 'locking'
  | 'sending'
  | 'confirming'
  | 'confirmed'
  | 'failed'
