import type { PortalMorphoBetaPortalFlags, PortalMorphoVaultDetails } from '@/lib/portal/morphoVaultTypes'

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
  position: PortalSavingsPosition
  averageApyBps: number | null
  averageApyDisplay: string
  historyPoints: number[]
  transactions: PortalSavingsVaultTransaction[]
  vault: PortalMorphoVaultDetails
  beta?: PortalMorphoBetaPortalFlags
  partial?: boolean
}
