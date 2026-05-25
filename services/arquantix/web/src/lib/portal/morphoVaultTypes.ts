import type { PortalMorphoIntegrationMode } from '@/lib/portal/morphoConstants'
import type { MorphoVaultVersion } from '@/lib/portal/morphoConstants'

export type PortalMorphoAsset = {
  address: string
  symbol: string
  decimals: number
}

export type PortalMorphoVaultDetails = {
  /** Identifiant stable côté portail (adresse vault normalisée). */
  id: string
  vaultAddress: string
  chainId: number
  integrationMode: PortalMorphoIntegrationMode
  /** Version Morpho on-chain (MetaMorpho V1 ou Vault V2). */
  morphoVaultVersion?: MorphoVaultVersion | null
  /** Legacy — conservé en lecture seule pour les lignes CMS historiques. */
  privyVaultId?: string | null
  name: string
  provider: string
  asset: PortalMorphoAsset
  userApyBps: number | null
  tvlUsd: number | null
  availableLiquidityUsd: number | null
  label?: string | null
  description?: string | null
  curator?: string | null
  listed?: boolean
}

export type PortalMorphoVaultPosition = {
  vaultAddress: string
  asset: PortalMorphoAsset
  assetsInVault: string
  assetsInVaultDisplay: string
  sharesInVault: string
  assetsUsd: number | null
  earnedYieldDisplay: string
  yieldSyncStatus?: 'synced' | 'pending'
}

export type PortalMorphoBetaPortalFlags = {
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

export type PortalMorphoVaultsPayload = {
  vaults: PortalMorphoVaultDetails[]
  configured: boolean
  beta?: PortalMorphoBetaPortalFlags
}

export type PortalMorphoPreparedTx = {
  to: string
  data: string
  value: string
  chainId: number
  operation?: 'approve' | 'deposit' | 'withdraw'
}

export type PortalMorphoLedgerEntryRef = {
  id: string
  operation: 'approve' | 'deposit' | 'withdraw'
  txIndex: number
}

export type PortalMorphoPreparePayload = {
  transactions: PortalMorphoPreparedTx[]
  ledgerEntries: PortalMorphoLedgerEntryRef[]
  groupKey: string
  idempotencyKey: string
  /** Présent uniquement quand l’opération est finalisée côté serveur (sandbox local). */
  serverCompleted?: boolean
}

export type PortalMorphoConfirmResult = {
  ledgerEntryId: string
  txHash: string
  status: 'success' | 'reverted' | 'failed'
  blockNumber?: string | null
}

export type PortalMorphoConfirmPayload = {
  results: PortalMorphoConfirmResult[]
  groupKey: string
}

export type PortalMorphoCatalogVault = {
  address: string
  name: string
  symbol: string
  listed: boolean
  version: MorphoVaultVersion
  asset: PortalMorphoAsset
  netApy: number | null
  tvlUsd: number | null
  liquidityUsd?: number | null
  curator?: string | null
  description?: string | null
}
