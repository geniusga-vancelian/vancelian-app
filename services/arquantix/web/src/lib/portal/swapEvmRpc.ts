import { createPublicClient, http, type Chain, type PublicClient } from 'viem'
import { arbitrum, base, mainnet, polygon } from 'viem/chains'

const CHAIN_BY_ID: Record<number, Chain> = {
  [mainnet.id]: mainnet,
  [base.id]: base,
  [polygon.id]: polygon,
  [arbitrum.id]: arbitrum,
}

function readPublicEnv(name: string): string | undefined {
  const value = process.env[name]?.trim()
  return value || undefined
}

function rpcUrlForChain(chainId: number): string {
  switch (chainId) {
    case mainnet.id:
      return readPublicEnv('NEXT_PUBLIC_ETHEREUM_RPC_URL') ?? 'https://ethereum.publicnode.com'
    case base.id:
      return (
        readPublicEnv('NEXT_PUBLIC_BASE_RPC_URL') ??
        readPublicEnv('NEXT_PUBLIC_BASE_RPC_URL_FALLBACK') ??
        'https://mainnet.base.org'
      )
    case polygon.id:
      return 'https://polygon-rpc.com'
    case arbitrum.id:
      return 'https://arb1.arbitrum.io/rpc'
    default:
      return 'https://ethereum.publicnode.com'
  }
}

export function createSwapPublicClient(chainId: number): PublicClient {
  const chain = CHAIN_BY_ID[chainId] ?? mainnet
  const primary = rpcUrlForChain(chainId)
  return createPublicClient({
    chain,
    transport: http(primary),
  })
}
