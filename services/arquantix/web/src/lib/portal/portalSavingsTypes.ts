import type { PortalLedgityBetaPortalFlags, PortalLedgityVaultDetails } from '@/lib/portal/ledgity/ledgityVaultTypes'
import type { PortalMorphoBetaPortalFlags, PortalMorphoVaultDetails } from '@/lib/portal/morphoVaultTypes'

export type PortalDefiVaultDetails = PortalMorphoVaultDetails | PortalLedgityVaultDetails
export type PortalDefiBetaPortalFlags = PortalMorphoBetaPortalFlags | PortalLedgityBetaPortalFlags
export type PortalDefiIntegrationMode = 'direct_morpho' | 'ledgity_vault'

export type PortalSavingsPosition = {
  vaultAddress: string
  vaultName: string
  assetSymbol: string
  assetsInVaultDisplay: string
  assetsUsd: number | null
  estimatedValueEur?: number
  estimatedValueUsd?: number
  earnedYieldDisplay: string
  yieldSyncStatus?: 'synced' | 'pending'
  userApyBps: number | null
  provider: string
  integrationMode?: PortalDefiIntegrationMode
}

export type PortalSavingsSummary = {
  total_value_eur?: number | string
  total_value_usd?: number | string
  positions_count: number
  positions: PortalSavingsPosition[]
} | null

export type PortalSavingsWalletHubPayload = {
  currency: string
  savings: PortalSavingsSummary
  historyPoints: number[]
  partial?: boolean
}

export type PortalSavingsVaultTransaction = {
  id: string
  operation: 'deposit' | 'withdraw' | 'approve'
  amountDisplay: string
  assetSymbol: string
  status: string
  txHash: string | null
  walletAddress: string
  createdAt: string
  title: string
  subtitle: string
  incoming: boolean
}

export type PortalSavingsVaultDetailPayload = {
  currency: string
  vaultAddress: string
  vaultName: string
  assetSymbol: string
  integrationMode: PortalDefiIntegrationMode
  position: PortalSavingsPosition
  averageApyBps: number | null
  averageApyDisplay: string
  historyPoints: number[]
  transactions: PortalSavingsVaultTransaction[]
  vault: PortalDefiVaultDetails
  beta?: PortalDefiBetaPortalFlags
  partial?: boolean
}
