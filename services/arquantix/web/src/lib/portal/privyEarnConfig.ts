/** Vault Privy Earn configurés pour le portail (Morpho / Steakhouse, etc.). */

export type PortalEarnVaultConfig = {
  vaultId: string
  /** Surcharge affichage — sinon nom renvoyé par l’API Privy. */
  label?: string
  description?: string
}

const DEFAULT_VAULT_ID = 'svbeyhtpw8317205byhv04ns'

/** IDs depuis env (CSV) ou vault Morpho Steakhouse USDC par défaut. */
export function getPortalEarnVaultConfigs(): PortalEarnVaultConfig[] {
  const raw =
    process.env.PRIVY_EARN_VAULT_IDS?.trim() ||
    process.env.NEXT_PUBLIC_PRIVY_EARN_VAULT_IDS?.trim() ||
    DEFAULT_VAULT_ID
  return raw
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((vaultId) => ({
      vaultId,
      label: vaultId === DEFAULT_VAULT_ID ? 'Steakhouse Prime USDC' : undefined,
      description:
        vaultId === DEFAULT_VAULT_ID
          ? 'Vault Morpho USDC — rendement on-chain via Privy Earn.'
          : undefined,
    }))
}

export const PRIVY_EARN_API_BASE = 'https://api.privy.io'
