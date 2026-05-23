/** Libellés réseau EVM pour l’écran dépôt (aligné mobile + concurrence type Binance/Coinbase). */
const EVM_CHAIN_LABELS: Record<number, string> = {
  1: 'Ethereum (Mainnet)',
  11155111: 'Sepolia (testnet)',
  5: 'Goerli (testnet)',
  137: 'Polygon',
  42161: 'Arbitrum One',
  10: 'Optimism',
  8453: 'Base',
}

export function formatEvmNetworkLabel(chainId: number | null | undefined): string {
  if (chainId != null && EVM_CHAIN_LABELS[chainId]) {
    return EVM_CHAIN_LABELS[chainId]
  }
  if (chainId != null) {
    return `EVM · chain ID ${chainId}`
  }
  return 'Ethereum (EVM)'
}

export function formatEvmNetworkShort(chainId: number | null | undefined): string {
  if (chainId === 1 || chainId == null) return 'ERC-20 · Ethereum'
  const label = formatEvmNetworkLabel(chainId)
  return label.includes('testnet') ? label : `EVM · ${label}`
}

export function resolveEvmExplorerAddressUrl(
  address: string,
  chainId: number | null | undefined,
): string | null {
  const trimmed = address.trim()
  if (!trimmed) return null
  if (chainId === 1 || chainId == null) {
    return `https://etherscan.io/address/${trimmed}`
  }
  if (chainId === 11155111) {
    return `https://sepolia.etherscan.io/address/${trimmed}`
  }
  if (chainId === 137) {
    return `https://polygonscan.com/address/${trimmed}`
  }
  if (chainId === 42161) {
    return `https://arbiscan.io/address/${trimmed}`
  }
  if (chainId === 10) {
    return `https://optimistic.etherscan.io/address/${trimmed}`
  }
  if (chainId === 8453) {
    return `https://basescan.org/address/${trimmed}`
  }
  return null
}
