/** Types moteur VAULT_ENGINE — sans dépendances serveur (safe import client / types). */

export type VaultEngineSnapshot = {
  status: string
  investable: boolean
  provider: 'morpho' | 'ledgity'
  integration_mode: string
  portal_config_id: string
  vault_address: string
  chain_id: number
  name: string
  asset: string
  asset_symbol: string
  user_apy_bps: number | null
  supply_apr: number | null
  tvl_usd: number | null
  available_liquidity_usd: number | null
  liquidity_pct: number | null
  curator: string | null
  /** Profil ERC-4626 : flexible ou offre exclusive lock-up (club deal). */
  vault_profile?: 'flexible' | 'exclusive_offer_locked'
  lock_active?: boolean
  operation_end_at?: string | null
  withdraw_mode?: 'instant' | 'async_request' | 'blocked'
  lock_status_label?: string | null
}
