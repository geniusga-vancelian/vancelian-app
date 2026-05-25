import type { PortalNewsWidgetData } from '@/lib/portal/parseTop10NewsWidget'

export type PortalDashboardBootstrap = {
  client?: {
    id?: string
    reference_currency?: string
    initials?: string
  }
} | null

export type PortalDashboardProfile = {
  email?: string
  initials?: string
  reference_currency?: string
  personal?: {
    first_name?: string
    last_name?: string
  } | null
  account_status?: string
  kyc_status?: string
  client_status?: string
  registration_completion_ratio?: number
  registration_macro_stage?: string
  registration_missing_steps?: string[]
  registration_derived_progress_percent?: number
  registration_derived_completed_count?: number
  registration_derived_total_count?: number
  registration_derived_next_step_key?: string
} | null

export type PortalDashboardCash = {
  cash_account?: {
    available_balance?: number | string
    currency?: string
    currency_symbol?: string
  } | null
  client?: {
    email?: string
  }
} | null

export type PortalGlobalStatistics = {
  currency?: string
  performance?: {
    current_value?: number | string
    performance_pct?: number | string
    total_pnl?: number | string
  }
} | null

export type PortalGlobalHistoryPoint = {
  timestamp?: string
  total_value?: number | string
  performance_value?: number | string
}

export type PortalCryptoSummary = {
  summary?: {
    total_value_eur?: number | string
    total_value_usd?: number | string
    positions_count?: number
  }
  positions?: Array<{
    asset?: string
    portfolio_scope?: string
    estimated_value_eur?: number | string
    estimated_value_usd?: number | string
    privy_balance?: number | string
    platform_balance?: number | string
    chain_type?: string
    chain_id?: number | null
    wallet_address?: string
  }>
} | null

export type PortalPlacementsSummary = {
  total_earn_value_eur?: number | string
  positions_count?: number
} | null

import type { PortalSavingsSummary } from '@/lib/portal/portalSavingsTypes'

export type { PortalSavingsSummary } from '@/lib/portal/portalSavingsTypes'

export type PortalPrivyPersonWallets = {
  wallets?: Array<{
    id?: string
    address?: string
    chain_type?: string
    chain_id?: number | null
    wallet_type?: string
    provider?: string
    is_primary?: boolean
  }>
} | null

export type PortalDashboardPayload = {
  bootstrap: PortalDashboardBootstrap
  profile: PortalDashboardProfile
  cash: PortalDashboardCash
  globalStatistics: PortalGlobalStatistics
  globalHistory: { points?: PortalGlobalHistoryPoint[] } | null
  crypto: PortalCryptoSummary | null
  placements: PortalPlacementsSummary | null
  savings: PortalSavingsSummary
  notifications: { count?: number } | null
  newsWidget: PortalNewsWidgetData | null
  privyPersonWallets?: PortalPrivyPersonWallets
  partial?: boolean
}

/** Section rapide — header + comptes EUR + Privy metadata. */
export type PortalDashboardCorePayload = {
  bootstrap: PortalDashboardBootstrap
  profile: PortalDashboardProfile
  cash: PortalDashboardCash
  globalStatistics: PortalGlobalStatistics
  globalHistory: { points?: PortalGlobalHistoryPoint[] } | null
  notifications: { count?: number } | null
  privyPersonWallets?: PortalPrivyPersonWallets
  partial?: boolean
}

/** Section portfolio — crypto + placements + épargne DeFi (plus lourd). */
export type PortalDashboardPortfolioPayload = {
  crypto: PortalCryptoSummary | null
  placements: PortalPlacementsSummary
  savings: PortalSavingsSummary
  partial?: boolean
}

export type PortalWalletRow = {
  id: string
  title: string
  subtitle: string
  balance: string
  numericBalance: number
  iconKey: 'euro' | 'savings' | 'offers' | 'portfolio' | 'crypto'
  /** Teinte DS (`--v-blue`, `--v-green`, etc.) pour l’icône compte. */
  iconTone: 'blue' | 'green' | 'terracotta' | 'fg' | 'fg-body'
  /** Ligne désactivée (ex. compte Euro avant fin d’inscription). */
  locked?: boolean
  ctaLabel?: string
}
