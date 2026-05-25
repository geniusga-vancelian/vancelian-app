import { SWAP_V1_PILOT_CHAINS, SWAP_V1_SAME_CHAIN_ONLY } from '@/lib/portal/swapFlowTypes'

export function formatSwapCryptoAmount(value: number | string): string {
  const n = typeof value === 'string' ? Number(value.replace(',', '.')) : value
  if (!Number.isFinite(n) || n === 0) return '0'
  if (n < 0.0001) return n.toExponential(2)
  if (n < 1) return trimTrailingZeros(n.toFixed(8))
  return trimTrailingZeros(n.toFixed(6))
}

function trimTrailingZeros(raw: string): string {
  if (!raw.includes('.')) return raw
  return raw.replace(/0+$/, '').replace(/\.$/, '') || '0'
}

export function defaultChainForAsset(
  asset: string,
  chains: string[],
): string {
  if (chains.length === 0) return ''
  if (SWAP_V1_SAME_CHAIN_ONLY) {
    const pilot = SWAP_V1_PILOT_CHAINS.find((chain) => chains.includes(chain))
    if (pilot) return pilot
  }
  const sym = asset.toUpperCase()
  const preferred: Record<string, string> = {
    USDC: 'ethereum',
    USDT: 'ethereum',
    ETH: 'ethereum',
  }
  const pick = preferred[sym]
  if (pick && chains.includes(pick)) return pick
  return chains[0]!
}

/** Chaîne source alignée sur la destination en mode same-chain. */
export function resolveSwapSourceChain(
  asset: string,
  chains: string[],
  destinationChain: string,
): string {
  if (SWAP_V1_SAME_CHAIN_ONLY && destinationChain && chains.includes(destinationChain)) {
    return destinationChain
  }
  return defaultChainForAsset(asset, chains)
}
