/** Base mainnet — seule chaîne supportée en v1. */
export const MORPHO_CHAIN_ID = 8453

export const MORPHO_GRAPHQL_URL =
  process.env.MORPHO_GRAPHQL_URL?.trim() || 'https://api.morpho.org/graphql'

/** @deprecated Préférer `createBasePublicClient()` — conservé pour compat imports legacy. */
export function getMorphoDefaultBaseRpcUrl(): string {
  const primary =
    process.env.BASE_RPC_URL_PRIMARY?.trim() ||
    process.env.BASE_RPC_URL?.trim() ||
    process.env.NEXT_PUBLIC_BASE_RPC_URL?.trim()
  return primary || 'https://mainnet.base.org'
}

/** Steakhouse Prime USDC — vault Morpho par défaut (direct on-chain). */
export const MORPHO_DEFAULT_VAULT_ADDRESS = '0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2'

export type PortalMorphoIntegrationMode = 'direct_morpho'

export type MorphoVaultVersion = 'v1' | 'v2'

export function getPortalMorphoIntegrationLabel(_mode: PortalMorphoIntegrationMode): string {
  return 'Direct vault'
}

export type PortalDefiIntegrationMode = PortalMorphoIntegrationMode | 'ledgity_vault'

export function getPortalDefiIntegrationLabel(mode: PortalDefiIntegrationMode): string {
  if (mode === 'ledgity_vault') return 'Ledgity vault'
  return getPortalMorphoIntegrationLabel(mode)
}

export function isValidEvmAddress(value: string): value is `0x${string}` {
  return /^0x[a-fA-F0-9]{40}$/.test(value.trim())
}

export function normalizeVaultAddress(value: string): string {
  return value.trim().toLowerCase()
}
