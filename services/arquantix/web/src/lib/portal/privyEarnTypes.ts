export type PortalEarnAsset = {
  address: string
  symbol: string
  decimals: number
}

export type PortalEarnVaultDetails = {
  id: string
  name: string
  provider: string
  vaultAddress: string
  asset: PortalEarnAsset
  caip2: string
  userApyBps: number | null
  tvlUsd: number | null
  availableLiquidityUsd: number | null
  label?: string
  description?: string
}

export type PortalEarnVaultPosition = {
  vaultId: string
  asset: PortalEarnAsset
  assetsInVault: string
  assetsInVaultDisplay: string
  totalDeposited: string
  totalWithdrawn: string
  earnedYieldDisplay: string
  sharesInVault: string
}

export type PortalEarnWalletAction = {
  id: string
  status: string
  type: string
  walletId: string
  vaultId?: string
  amount?: string
  rawAmount?: string
  asset?: string
  transactionHash?: string | null
  failureMessage?: string | null
}

export type PortalEarnVaultsPayload = {
  vaults: PortalEarnVaultDetails[]
  configured: boolean
}

export type PortalEarnOperationPayload = {
  action: PortalEarnWalletAction
}
