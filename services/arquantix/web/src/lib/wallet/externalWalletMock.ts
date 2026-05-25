import { MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'
import type { ExecutionWallet, VerifiedExternalWallet } from '@/lib/wallet/executionWalletTypes'

export const LOCAL_MOCK_EXTERNAL_WALLET_ADDRESS =
  '0x1111111111111111111111111111111111111111' as const

export const LOCAL_MOCK_EXTERNAL_WALLET = {
  address: LOCAL_MOCK_EXTERNAL_WALLET_ADDRESS,
  chainId: MORPHO_CHAIN_ID,
  connector: 'local_mock' as const,
  walletProvider: 'local_mock' as const,
  isVerified: true,
}

export function isLocalMockExternalWalletAddress(address: string | null | undefined): boolean {
  if (!address) return false
  return address.trim().toLowerCase() === LOCAL_MOCK_EXTERNAL_WALLET_ADDRESS.toLowerCase()
}

export function isLocalMockExternalWallet(wallet: ExecutionWallet): boolean {
  return wallet.type === 'external_evm' && wallet.connector === 'local_mock'
}

export function isLocalMockVerifiedExternalWallet(wallet: VerifiedExternalWallet): boolean {
  return wallet.walletProvider === 'local_mock'
}

export function generateMockExternalWalletTxHash(): `0x${string}` {
  const suffix =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID().replace(/-/g, '')
      : `${Date.now()}${Math.random().toString(16).slice(2)}`
  return `0xmocked${suffix}` as `0x${string}`
}

export function buildLocalMockExternalWalletMetadata(): Record<string, unknown> {
  return {
    wallet_provider: LOCAL_MOCK_EXTERNAL_WALLET.walletProvider,
    is_verified: true,
    verified_at: new Date().toISOString(),
    sync_source: 'external_wallet_local_mock',
    morpho_sandbox: true,
    lifi_sandbox: true,
  }
}
