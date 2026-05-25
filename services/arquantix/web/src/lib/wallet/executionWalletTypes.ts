export type ExternalWalletConnector = 'metamask' | 'walletconnect' | 'injected' | 'local_mock'

export type ExecutionWalletSource = 'privy_embedded' | 'external_evm'

export type ExecutionWallet =
  | {
      type: 'privy_embedded'
      address: `0x${string}`
      privyWalletId?: string | null
    }
  | {
      type: 'external_evm'
      address: `0x${string}`
      externalWalletId: string
      connector: ExternalWalletConnector
    }

export type VerifiedExternalWallet = {
  id: string
  address: `0x${string}`
  walletProvider: ExternalWalletConnector
  isVerified: boolean
  verifiedAt: string | null
  createdAt: string
}

export type WalletSourceMetadata = {
  wallet_source: ExecutionWalletSource
  external_wallet_id?: string | null
  wallet_provider?: ExternalWalletConnector | null
}

export function readExecutionWalletSource(metadata: unknown): ExecutionWalletSource | null {
  if (!metadata || typeof metadata !== 'object') return null
  const source = (metadata as Record<string, unknown>).wallet_source
  if (source === 'privy_embedded' || source === 'external_evm') return source
  return null
}

export function buildWalletSourceMetadata(wallet: ExecutionWallet): WalletSourceMetadata {
  if (wallet.type === 'external_evm') {
    return {
      wallet_source: 'external_evm',
      external_wallet_id: wallet.externalWalletId,
      wallet_provider: wallet.connector,
    }
  }
  return { wallet_source: 'privy_embedded' }
}
