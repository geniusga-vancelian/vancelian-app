/** Base mainnet — seule chaîne supportée en v1 Ledgity. */
export const LEDGITY_CHAIN_ID = 8453

/** USDC officiel Circle sur Base. */
export const LEDGITY_USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

/** EURC officiel Circle sur Base. */
export const LEDGITY_EURC_ADDRESS = '0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42'

/** Vault Ledgity lyUSDC sur Base. */
export const LEDGITY_LYUSDC_VAULT = '0x916f179D5D9B7d8Ad815AC2f8570aabF0C6a6e38'

/** Vault Ledgity lyEURC sur Base. */
export const LEDGITY_LYEURC_VAULT = '0xFaA1e3720e6Ef8cC76A800DB7B3dF8944833b134'

export type PortalLedgityIntegrationMode = 'ledgity_vault'

export function getPortalLedgityIntegrationLabel(_mode: PortalLedgityIntegrationMode): string {
  return 'Ledgity vault'
}

export function isValidEvmAddress(value: string): value is `0x${string}` {
  return /^0x[a-fA-F0-9]{40}$/.test(value.trim())
}

export function normalizeVaultAddress(value: string): string {
  return value.trim().toLowerCase()
}

export function resolveLedgityShareSymbol(vaultAddress: string, assetSymbol?: string): string {
  const normalized = normalizeVaultAddress(vaultAddress)
  if (normalized === normalizeVaultAddress(LEDGITY_LYUSDC_VAULT)) return 'lyUSDC'
  if (normalized === normalizeVaultAddress(LEDGITY_LYEURC_VAULT)) return 'lyEURC'
  return assetSymbol ? `ly${assetSymbol}` : 'lyToken'
}
