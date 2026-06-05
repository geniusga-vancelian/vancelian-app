import type { PortalLedgityIntegrationMode } from '@/lib/portal/ledgity/ledgityConstants'
import type {
  LedgityVaultProfile,
  LedgityVaultWithdrawMode,
} from '@/lib/portal/ledgity/ledgityVaultProfiles'

export type PortalLedgityAsset = {
  address: string
  symbol: string
  decimals: number
}

export type PortalLedgityVaultDetails = {
  /** Identifiant stable côté portail (adresse vault normalisée). */
  id: string
  vaultAddress: string
  chainId: number
  integrationMode: PortalLedgityIntegrationMode
  name: string
  provider: string
  asset: PortalLedgityAsset
  userApyBps: number | null
  pricePerShare: number | null
  tvlUsd: number | null
  availableLiquidityUsd: number | null
  label?: string | null
  description?: string | null
  curator?: string | null
  listed?: boolean
  vaultProfile?: LedgityVaultProfile
  lockActive?: boolean
  operationEndAt?: string | null
  withdrawMode?: LedgityVaultWithdrawMode
  lockStatusLabel?: string | null
}

export type PortalLedgityVaultPosition = {
  vaultAddress: string
  asset: PortalLedgityAsset
  assetsInVault: string
  assetsInVaultDisplay: string
  sharesInVault: string
  assetsUsd: number | null
  earnedYieldDisplay: string
  yieldSyncStatus?: 'synced' | 'pending'
}

export type PortalLedgityBetaPortalFlags = {
  enabled: boolean
  allowed: boolean
  depositsDisabled: boolean
  withdrawsDisabled: boolean
  limits: {
    minDepositUsdc: number
    maxDepositUsdc: number
    maxUserExposureUsdc: number
    maxGlobalExposureUsdc: number
  } | null
  message: string | null
}

export type PortalLedgityVaultsPayload = {
  vaults: PortalLedgityVaultDetails[]
  configured: boolean
  beta?: PortalLedgityBetaPortalFlags
}

export type PortalLedgityPreparedTx = {
  to: string
  data: string
  value: string
  chainId: number
  operation?: 'approve' | 'deposit' | 'withdraw'
}

export type PortalLedgityLedgerEntryRef = {
  id: string
  operation: 'approve' | 'deposit' | 'withdraw'
  txIndex: number
}

export type PortalLedgityPreparePayload = {
  transactions: PortalLedgityPreparedTx[]
  ledgerEntries: PortalLedgityLedgerEntryRef[]
  groupKey: string
  idempotencyKey: string
  /** Présent uniquement quand l’opération est finalisée côté serveur (sandbox local). */
  serverCompleted?: boolean
}

export type PortalLedgityConfirmResult = {
  ledgerEntryId: string
  txHash: string
  status: 'success' | 'reverted' | 'failed'
  blockNumber?: string | null
}

export type PortalLedgityConfirmPayload = {
  results: PortalLedgityConfirmResult[]
  groupKey: string
}

export type PortalLedgityCatalogVault = {
  address: string
  name: string
  symbol: string
  listed: boolean
  asset: PortalLedgityAsset
  netApy: number | null
  pricePerShare: number | null
  tvlUsd: number | null
  liquidityUsd?: number | null
  curator?: string | null
  description?: string | null
  lockState?: {
    operationEndDateUnix?: string | null
    withdrawalRequestsEnabled?: boolean
  }
}

export type LedgityVaultPositionRow = {
  assets: string
  shares: string
  assetsUsd: number | null
  asset: PortalLedgityAsset
}

export type LedgityVaultMetrics = {
  totalAssetsRaw: bigint
  /** USDC/EURC idle dans le contrat vault (buffer retrait instantané). */
  idleAssetsRaw: bigint
  pricePerShare: number | null
  asset: PortalLedgityAsset
  tvlUsd: number | null
  liquidityUsd: number | null
}
