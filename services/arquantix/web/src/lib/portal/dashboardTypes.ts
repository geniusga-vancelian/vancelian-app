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
  registration_missing_steps?: string[]
  registration_derived_progress_percent?: number
  activation_journey?: {
    show_module?: boolean
    stages?: Array<{
      key?: string
      ux_status?: string
    }>
  } | null
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
} | null

export type PortalPlacementsSummary = {
  total_earn_value_eur?: number | string
  positions_count?: number
} | null

export type PortalDashboardPayload = {
  bootstrap: PortalDashboardBootstrap
  profile: PortalDashboardProfile
  cash: PortalDashboardCash
  globalStatistics: PortalGlobalStatistics
  globalHistory: { points?: PortalGlobalHistoryPoint[] } | null
  crypto: PortalCryptoSummary
  placements: PortalPlacementsSummary
  notifications: { count?: number } | null
  newsWidget: PortalNewsWidgetData | null
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
}
