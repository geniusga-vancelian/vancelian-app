/** Base mainnet — seule chaîne supportée en v1 Ledgity / Vancelian vaults. */
export const LEDGITY_CHAIN_ID = 8453

/** USDC officiel Circle sur Base. */
export const LEDGITY_USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

/** EURC officiel Circle sur Base. */
export const LEDGITY_EURC_ADDRESS = '0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42'

/** Vault Ledgity lyUSDC sur Base. */
export const LEDGITY_LYUSDC_VAULT = '0x916f179D5D9B7d8Ad815AC2f8570aabF0C6a6e38'

/** Vault Ledgity lyEURC sur Base. */
export const LEDGITY_LYEURC_VAULT = '0xFaA1e3720e6Ef8cC76A800DB7B3dF8944833b134'

/** Vancelian Flexible Vault EURC (vfEUR) — mainnet Base. */
export const VANCELIAN_VFEUR_VAULT = '0x46dB81F232DF1884081368cD2aacc9E6Ec6489a2'

/** Arquantix Dubai — offre exclusive RWA (axDUBAI) — mainnet Base. */
export const VANCELIAN_AXDUBAI_VAULT = '0x273ff92cc955ef76ACeeC7206163C732185CeEBe'

/** Arquantix Bali — offre exclusive RWA (axBALI) — mainnet Base. */
export const VANCELIAN_AXBALI_VAULT = '0x9A7d4da8aab422a48744791A5f086612A219ea4d'

/** Arquantix Yield USDC (axUSD) — mainnet Base. */
export const VANCELIAN_AXUSD_VAULT = '0xEF3fbcEEA9d0A1F343433b3d5F2FF2dc28946BdC'

export type LedgityVaultAsset = {
  address: string
  symbol: string
  decimals: number
}

const USDC_ASSET: LedgityVaultAsset = {
  address: LEDGITY_USDC_ADDRESS,
  symbol: 'USDC',
  decimals: 6,
}

const EURC_ASSET: LedgityVaultAsset = {
  address: LEDGITY_EURC_ADDRESS,
  symbol: 'EURC',
  decimals: 6,
}

export type PortalLedgityIntegrationMode = 'ledgity_vault'

export function getPortalLedgityIntegrationLabel(_mode: PortalLedgityIntegrationMode): string {
  return 'Vault ERC-4626'
}

export function isValidEvmAddress(value: string): value is `0x${string}` {
  return /^0x[a-fA-F0-9]{40}$/.test(value.trim())
}

export function normalizeVaultAddress(value: string): string {
  return value.trim().toLowerCase()
}

/** Registre connu des vaults ERC-4626 (Ledgity natifs + Vancelian/Arquantix). */
export const KNOWN_LEDGITY_VAULT_REGISTRY: Record<
  string,
  { shareSymbol: string; asset: LedgityVaultAsset }
> = {
  [normalizeVaultAddress(LEDGITY_LYUSDC_VAULT)]: { shareSymbol: 'lyUSDC', asset: USDC_ASSET },
  [normalizeVaultAddress(LEDGITY_LYEURC_VAULT)]: { shareSymbol: 'lyEURC', asset: EURC_ASSET },
  [normalizeVaultAddress(VANCELIAN_VFEUR_VAULT)]: { shareSymbol: 'vfEUR', asset: EURC_ASSET },
  [normalizeVaultAddress(VANCELIAN_AXDUBAI_VAULT)]: { shareSymbol: 'axDUBAI', asset: EURC_ASSET },
  [normalizeVaultAddress(VANCELIAN_AXBALI_VAULT)]: { shareSymbol: 'axBALI', asset: EURC_ASSET },
  [normalizeVaultAddress(VANCELIAN_AXUSD_VAULT)]: { shareSymbol: 'axUSD', asset: USDC_ASSET },
}

export function resolveLedgityShareSymbol(vaultAddress: string, assetSymbol?: string): string {
  const known = KNOWN_LEDGITY_VAULT_REGISTRY[normalizeVaultAddress(vaultAddress)]
  if (known) return known.shareSymbol
  return assetSymbol ? `ly${assetSymbol}` : 'lyToken'
}

export function resolveKnownLedgityVaultAsset(vaultAddress: string): LedgityVaultAsset | null {
  return KNOWN_LEDGITY_VAULT_REGISTRY[normalizeVaultAddress(vaultAddress)]?.asset ?? null
}
