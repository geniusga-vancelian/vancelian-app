/** Écosystèmes portail — séparateur navbar (Base / Ethereum / Solana). */
export const PORTAL_CHAINS = ['base', 'ethereum', 'solana'] as const

export type PortalChain = (typeof PORTAL_CHAINS)[number]

export const DEFAULT_PORTAL_CHAIN: PortalChain = 'base'

export const PORTAL_CHAIN_LABELS: Record<PortalChain, string> = {
  base: 'Base',
  ethereum: 'Ethereum',
  solana: 'Solana',
}

export const PORTAL_CHAIN_SHORT: Record<PortalChain, string> = {
  base: 'Base',
  ethereum: 'ETH',
  solana: 'SOL',
}

export function isValidPortalChain(value: string): value is PortalChain {
  return (PORTAL_CHAINS as readonly string[]).includes(value)
}
