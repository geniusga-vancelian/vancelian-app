import { getDefaultConfig } from '@rainbow-me/rainbowkit'
import { http } from 'viem'
import { arbitrum, base, mainnet, optimism, polygon } from 'wagmi/chains'

import { MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'

/** Chaînes autorisées pour wallet externe (Morpho Base + LI.FI). */
export const EXTERNAL_WALLET_CHAINS = [base, mainnet, polygon, arbitrum, optimism] as const

export const EXTERNAL_WALLET_CHAIN_IDS = EXTERNAL_WALLET_CHAINS.map((chain) => chain.id)

export function isAllowedExternalWalletChainId(chainId: number): boolean {
  return (EXTERNAL_WALLET_CHAIN_IDS as readonly number[]).includes(chainId)
}

function readEnv(name: string): string | undefined {
  const value = process.env[name]?.trim()
  return value || undefined
}

export function getWalletConnectProjectId(): string {
  return readEnv('NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID') ?? '00000000000000000000000000000000'
}

export function isWalletConnectConfigured(): boolean {
  const id = readEnv('NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID')
  return Boolean(id && id !== '00000000000000000000000000000000')
}

function resolveBaseRpcUrl(): string {
  return (
    readEnv('NEXT_PUBLIC_BASE_RPC_URL') ??
    readEnv('NEXT_PUBLIC_BASE_RPC_URL_FALLBACK') ??
    'https://mainnet.base.org'
  )
}

function resolveMainnetRpcUrl(): string {
  return readEnv('NEXT_PUBLIC_ETHEREUM_RPC_URL') ?? 'https://ethereum.publicnode.com'
}

/** Config wagmi + RainbowKit (client-only). */
export function createExternalWalletWagmiConfig() {
  const baseRpc = resolveBaseRpcUrl()
  const mainnetRpc = resolveMainnetRpcUrl()

  return getDefaultConfig({
    appName: 'Vancelian',
    projectId: getWalletConnectProjectId(),
    chains: [...EXTERNAL_WALLET_CHAINS],
    ssr: true,
    transports: {
      [base.id]: http(baseRpc),
      [mainnet.id]: http(mainnetRpc),
      [polygon.id]: http('https://polygon-rpc.com'),
      [arbitrum.id]: http('https://arb1.arbitrum.io/rpc'),
      [optimism.id]: http('https://mainnet.optimism.io'),
    },
  })
}

export function getExternalWalletBaseChainId(): number {
  return MORPHO_CHAIN_ID
}
