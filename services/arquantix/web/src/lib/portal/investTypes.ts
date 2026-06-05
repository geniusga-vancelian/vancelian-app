export type PortalExclusiveOffer = {
  id: string
  slug: string
  title: string
  subtitle: string
  coverUrl: string
  category: string
  categorySlug: string
  description: string
  progressPct: number
  raisedLabel: string
  targetLabel: string
  investorsCount: number
  apyLabel: string
  durationMonths: number | null
  isFunded: boolean
  href: string
  /** Offre exclusive lock-up (club deal / vesting) — retraits bloqués jusqu'à maturité. */
  lockActive?: boolean
  lockStatusLabel?: string | null
  operationEndAt?: string | null
  withdrawMode?: 'instant' | 'async_request' | 'blocked' | null
}

/** Produit coffre catalogue (`vault_simple`) — présentation carte Invest, moteur = vault plateforme. */
export type PortalVaultProduct = PortalExclusiveOffer & {
  productType: 'vault_simple'
  /** Référence `portal_morpho_vault_configs.id` quand `engine.type = vault_engine`. */
  vaultEngineConfigId: string | null
  vaultAddress: string | null
  integrationMode: string | null
}

export type PortalInvestPayload = {
  offers: PortalExclusiveOffer[]
  /** Coffres catalogue (Flex Vault, Morpho USDC, etc.) — remplace l’affichage direct Morpho/Ledgity. */
  vaults: PortalVaultProduct[]
}
