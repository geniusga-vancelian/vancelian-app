import { getChainId } from '@wagmi/core'
import type { Chain } from 'viem'

import { EXTERNAL_WALLET_CHAINS } from '@/lib/wallet/externalWalletConfig'
import { getExternalWalletWagmiConfig } from '@/lib/wallet/externalWalletConfig'

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function resolveExternalWalletChain(chainId: number): Chain | undefined {
  return EXTERNAL_WALLET_CHAINS.find((chain) => chain.id === chainId)
}

export function requireExternalWalletChain(chainId: number): Chain {
  const chain = resolveExternalWalletChain(chainId)
  if (!chain) {
    throw new Error(`Réseau EVM non supporté pour MetaMask (${chainId}).`)
  }
  return chain
}

/** Attend que wagmi reflète le réseau MetaMask après wallet_switchEthereumChain. */
export async function waitForWagmiChainId(
  expectedChainId: number,
  timeoutMs = 30_000,
): Promise<void> {
  const config = getExternalWalletWagmiConfig()
  const started = Date.now()

  while (Date.now() - started < timeoutMs) {
    if (getChainId(config) === expectedChainId) {
      return
    }
    await sleep(300)
  }

  throw new Error(
    `MetaMask n’est pas sur le réseau attendu (${expectedChainId}). Basculez sur Ethereum mainnet puis réessayez.`,
  )
}
