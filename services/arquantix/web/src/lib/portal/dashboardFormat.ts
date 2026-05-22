import type {
  PortalCryptoSummary,
  PortalDashboardCash,
  PortalDashboardPayload,
  PortalDashboardProfile,
  PortalGlobalHistoryPoint,
  PortalGlobalStatistics,
  PortalPlacementsSummary,
  PortalWalletRow,
} from '@/lib/portal/dashboardTypes'

function toNumber(value: unknown, fallback = 0): number {
  if (value == null) return fallback
  if (typeof value === 'number' && !Number.isNaN(value)) return value
  const parsed = Number(String(value).replace(',', '.'))
  return Number.isNaN(parsed) ? fallback : parsed
}

export function resolveReferenceCurrency(payload: PortalDashboardPayload): string {
  return (
    payload.bootstrap?.client?.reference_currency?.trim().toUpperCase() ||
    payload.globalStatistics?.currency?.trim().toUpperCase() ||
    payload.cash?.cash_account?.currency?.trim().toUpperCase() ||
    'EUR'
  )
}

export function formatPortalMoney(amount: number, currency = 'EUR', locale = 'fr-FR'): string {
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return `${amount.toFixed(2)} ${currency}`
  }
}

export function formatPerformancePct(pct: number): string {
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

export function normalizeChartSeries(points: PortalGlobalHistoryPoint[]): number[] {
  if (points.length === 0) return []
  const values = points.map((p) => toNumber(p.performance_value))
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = Math.abs(max - min) < 0.01 ? 1 : max - min
  return values.map((v) => (v - min) / range)
}

export function hasEuroCashAccount(cash: PortalDashboardCash): boolean {
  return cash?.cash_account != null
}

export function isFirstDepositComplete(profile: PortalDashboardProfile): boolean {
  const stages = profile?.activation_journey?.stages ?? []
  const deposit = stages.find((s) => s.key === 'first_deposit')
  return deposit?.ux_status === 'completed'
}

export function shouldShowMyAccountsCard(
  profile: PortalDashboardProfile,
  hasEuroAccount: boolean,
): boolean {
  if (hasEuroAccount) return true
  if (!profile) return true
  const journey = profile.activation_journey
  if (journey) return isFirstDepositComplete(profile)
  return !shouldShowActivationModule(profile)
}

export function shouldShowActivationModule(profile: PortalDashboardProfile): boolean {
  if (!profile) return false
  const journey = profile.activation_journey
  if (journey) {
    if (!journey.show_module) return false
    return !isFirstDepositComplete(profile)
  }
  const status = (profile.client_status ?? '').trim().toUpperCase()
  if (status === 'PARTIAL') return true
  const missing = profile.registration_missing_steps ?? []
  if (missing.length > 0) return true
  const progress = profile.registration_derived_progress_percent
  if (progress != null && progress < 100) return true
  return false
}

export function buildWalletRows(
  cash: PortalDashboardCash,
  crypto: PortalCryptoSummary,
  placements: PortalPlacementsSummary,
  currency: string,
): PortalWalletRow[] {
  const eurBalance = toNumber(cash?.cash_account?.available_balance)
  const cryptoCount = crypto?.summary?.positions_count ?? 0
  const cryptoValue =
    currency === 'USD'
      ? toNumber(crypto?.summary?.total_value_usd, toNumber(crypto?.summary?.total_value_eur))
      : toNumber(crypto?.summary?.total_value_eur)
  const placementsCount = placements?.positions_count ?? 0
  const placementsValue = toNumber(placements?.total_earn_value_eur)

  return [
    {
      id: 'euro',
      title: 'Euro Account',
      subtitle: 'Consider investing!',
      balance: formatPortalMoney(eurBalance, 'EUR'),
      numericBalance: eurBalance,
      iconKey: 'euro',
      iconTone: 'blue',
    },
    {
      id: 'savings',
      title: 'Savings projects',
      subtitle: 'Open your first project!',
      balance: formatPortalMoney(0, 'EUR'),
      numericBalance: 0,
      iconKey: 'savings',
      iconTone: 'green',
    },
    {
      id: 'offers',
      title: 'Exclusive offers',
      subtitle:
        placementsCount > 0
          ? `${placementsCount} placement${placementsCount > 1 ? 's' : ''}`
          : 'Discover exclusive offers!',
      balance: formatPortalMoney(placementsValue, 'EUR'),
      numericBalance: placementsValue,
      iconKey: 'offers',
      iconTone: 'terracotta',
    },
    {
      id: 'portfolio',
      title: 'Managed Portfolio',
      subtitle: 'Build your portfolio',
      balance: formatPortalMoney(0, 'EUR'),
      numericBalance: 0,
      iconKey: 'portfolio',
      iconTone: 'fg',
    },
    {
      id: 'crypto',
      title: 'Crypto',
      subtitle: `${cryptoCount} crypto asset${cryptoCount === 1 ? '' : 's'}`,
      balance: formatPortalMoney(cryptoValue, currency),
      numericBalance: cryptoValue,
      iconKey: 'crypto',
      iconTone: 'fg-body',
    },
  ]
}

export function resolveHeaderBalance(
  stats: PortalGlobalStatistics,
  rows: PortalWalletRow[],
  currency: string,
): string {
  const fromStats = toNumber(stats?.performance?.current_value, NaN)
  if (!Number.isNaN(fromStats)) {
    return formatPortalMoney(fromStats, stats?.currency?.toUpperCase() || currency)
  }
  const sum = rows
    .filter((r) => r.id === 'euro' || r.id === 'crypto')
    .reduce((acc, r) => acc + r.numericBalance, 0)
  return formatPortalMoney(sum, currency)
}

export function resolvePerformancePct(stats: PortalGlobalStatistics): number {
  return toNumber(stats?.performance?.performance_pct)
}

export function resolveDisplayName(payload: PortalDashboardPayload): string {
  const p = payload.profile
  const first = p?.personal?.first_name?.trim()
  const last = p?.personal?.last_name?.trim()
  if (first) {
    return `${first}${last ? ` ${last.charAt(0)}.` : ''}`
  }
  return p?.email ?? 'Investor'
}

export function resolveInitials(payload: PortalDashboardPayload, displayName: string): string {
  const fromBootstrap = payload.bootstrap?.client?.initials?.trim()
  const fromProfile = payload.profile?.initials?.trim()
  if (fromBootstrap) return fromBootstrap.slice(0, 2).toUpperCase()
  if (fromProfile) return fromProfile.slice(0, 2).toUpperCase()
  return displayName
    .split(/\s+/)
    .map((part) => part.charAt(0))
    .join('')
    .slice(0, 2)
    .toUpperCase()
}
