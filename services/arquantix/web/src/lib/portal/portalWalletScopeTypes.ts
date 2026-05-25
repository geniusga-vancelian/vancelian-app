import type { ExecutionWalletSource } from '@/lib/wallet/executionWalletTypes'

/** Identifiant stable — `privy:{uuid}` ou `external:{uuid}`. */
export type PortalWalletScopeId = string

export type PortalWalletScope = {
  id: PortalWalletScopeId
  kind: ExecutionWalletSource
  label: string
  shortLabel: string
  address: string
  personWalletId?: string
  externalWalletId?: string
  chainType: 'evm' | 'solana'
}
