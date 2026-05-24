/** Base mainnet — seule chaîne supportée en v1. */
export const MORPHO_CHAIN_ID = 8453

export const MORPHO_GRAPHQL_URL = 'https://api.morpho.org/graphql'

/** @deprecated Préférer `createBasePublicClient()` — conservé pour compat imports legacy. */
export function getMorphoDefaultBaseRpcUrl(): string {
  const primary =
    process.env.BASE_RPC_URL_PRIMARY?.trim() ||
    process.env.BASE_RPC_URL?.trim() ||
    process.env.NEXT_PUBLIC_BASE_RPC_URL?.trim()
  return primary || 'https://mainnet.base.org'
}

/** Steakhouse Prime USDC — vault par défaut (Privy Earn). */
export const MORPHO_DEFAULT_VAULT_ADDRESS = '0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2'

export const MORPHO_DEFAULT_PRIVY_VAULT_ID = 'svbeyhtpw8317205byhv04ns'

export type PortalMorphoIntegrationMode = 'direct_morpho' | 'privy_earn'

export type MorphoVaultVersion = 'v1' | 'v2'

export function getPortalMorphoIntegrationLabel(mode: PortalMorphoIntegrationMode): string {
  return mode === 'direct_morpho' ? 'Direct vault' : 'Privy Earn'
}

export function isValidEvmAddress(value: string): value is `0x${string}` {
  return /^0x[a-fA-F0-9]{40}$/.test(value.trim())
}

export function normalizeVaultAddress(value: string): string {
  return value.trim().toLowerCase()
}
