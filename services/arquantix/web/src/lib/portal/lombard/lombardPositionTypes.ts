import type { LombardCollateralSymbol } from '@/lib/portal/lombard/lombardConfig'
import type { LombardSafetyLevel } from '@/lib/portal/lombard/lombardTypes'

export type LombardActivePosition = {
  marketId: string
  collateralSymbol: LombardCollateralSymbol
  collateralDisplayName: string
  collateralAmount: string
  collateralAmountRaw: string
  collateralUsdValue: string | null
  borrowSymbol: 'USDC'
  borrowAmount: string
  borrowAmountRaw: string
  currentLtvPercent: number | null
  maxUserLtvPercent: number
  morphoLltvPercent: number
  healthStatus: LombardSafetyLevel
  healthLabel: string
  healthMessage: string
  borrowApyPercent: number | null
  borrowApyLabel: string
  liquidationPrice: string | null
  protocolLabel: 'Powered by Morpho'
  chainId: number
}

export type LombardPositionsPayload = {
  enabled: boolean
  walletAddress: string
  positions: LombardActivePosition[]
  hasActiveLoan: boolean
  maxUserLtvPercent: number
  protocolLabel: 'Powered by Morpho'
}

export type LombardPositionDetailPayload = {
  position: LombardActivePosition
}
