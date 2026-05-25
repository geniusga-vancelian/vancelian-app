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
import type { PortalSavingsPosition, PortalSavingsSummary } from '@/lib/portal/portalSavingsTypes'
import {
  buildPrivyWalletPositionsSummary,
  parseCryptoPositionsPayload,
} from '@/lib/portal/cryptoWalletFormat'
import type { PortalCryptoPositionsSummary } from '@/lib/portal/cryptoWalletTypes'

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
  const account = cash?.cash_account
  if (!account) return false
  const currency = (account.currency ?? 'EUR').trim().toUpperCase()
  return currency === 'EUR'
}

/**
 * Aligné sur `should_show_registration_resume` (API Python / Flutter).
 * True tant que l’inscription n’est pas terminée.
 */
export function shouldShowRegistrationResume(profile: PortalDashboardProfile): boolean {
  if (!profile) return true

  const status = (profile.client_status ?? '').trim().toUpperCase()
  const missing = profile.registration_missing_steps ?? []
  const nextKey = profile.registration_derived_next_step_key?.trim() ?? ''
  const macro = (profile.registration_macro_stage ?? '').trim().toLowerCase()
  const ratio = profile.registration_completion_ratio
  const progress = profile.registration_derived_progress_percent
  const total = profile.registration_derived_total_count
  const completed = profile.registration_derived_completed_count

  if (status === 'ACTIVE') {
    if (total != null && total > 0 && completed != null && completed < total) return true
    if (missing.length > 0) return true
    if (nextKey) {
      if (progress != null && progress >= 100 && missing.length === 0) {
        // fall through
      } else {
        return true
      }
    }
    if (macro && macro !== 'active_client') return true
    if (ratio != null && ratio < 0.999) return true
    if (progress != null && progress < 100) return true
    return false
  }

  if (total != null && total > 0 && completed != null && completed < total) return true
  if (status === 'PARTIAL') return true
  if (missing.length > 0) return true
  if (nextKey) return true
  if (macro && macro !== 'active_client') return true
  if (ratio != null && ratio < 0.999) return true
  if (progress != null && progress < 100) return true
  return false
}

export function isRegistrationComplete(profile: PortalDashboardProfile): boolean {
  return !shouldShowRegistrationResume(profile)
}

export function shouldShowUnlockEuroBanner(profile: PortalDashboardProfile): boolean {
  return shouldShowRegistrationResume(profile)
}

export function applyWalletRowAccess(
  rows: PortalWalletRow[],
  profile: PortalDashboardProfile,
  cash: PortalDashboardCash,
): PortalWalletRow[] {
  const hasEuro = hasEuroCashAccount(cash)
  const registrationComplete = isRegistrationComplete(profile)

  return rows.map((row) => {
    if (row.id !== 'euro') return row

    if (hasEuro || registrationComplete) {
      return { ...row, locked: false }
    }

    return {
      ...row,
      locked: true,
      subtitle: 'Complete registration to unlock',
      ctaLabel: 'Complete registration',
      balance: '—',
      numericBalance: 0,
    }
  })
}

/** Valeur d’une position crypto dans la devise de référence client. */
export function selectReferenceMoneyValue(
  currency: string,
  eur?: number | string,
  usd?: number | string,
): number {
  if (currency === 'USD') {
    return toNumber(usd, toNumber(eur))
  }
  return toNumber(eur, toNumber(usd))
}

/** Somme des valorisations positions crypto — aligné Flutter `pref.selectValue` sur le portefeuille. */
export function resolveCryptoPortfolioTotal(
  crypto: PortalCryptoSummary,
  currency: string,
): number {
  const positions = crypto?.positions ?? []
  if (positions.length > 0) {
    const sum = positions.reduce(
      (acc, position) =>
        acc +
        selectReferenceMoneyValue(
          currency,
          position.estimated_value_eur,
          position.estimated_value_usd,
        ),
      0,
    )
    return sum
  }

  return selectReferenceMoneyValue(
    currency,
    crypto?.summary?.total_value_eur,
    crypto?.summary?.total_value_usd,
  )
}

/** Somme des valorisations vaults DeFi — aligné hub épargne. */
export function resolveSavingsPortfolioTotal(
  savings: PortalSavingsSummary,
  currency: string,
): number {
  if (!savings) return 0

  const positions = savings.positions ?? []
  if (positions.length > 0) {
    return positions.reduce(
      (acc: number, position: PortalSavingsPosition) =>
        acc +
        selectReferenceMoneyValue(
          currency,
          position.estimatedValueEur,
          position.estimatedValueUsd ?? position.assetsUsd ?? undefined,
        ),
      0,
    )
  }

  return selectReferenceMoneyValue(
    currency,
    savings.total_value_eur,
    savings.total_value_usd,
  )
}

function toPortalCryptoSummary(parsed: PortalCryptoPositionsSummary): PortalCryptoSummary {
  return {
    summary: {
      total_value_eur: parsed.totalValueEur,
      total_value_usd: parsed.totalValueUsd,
      positions_count: parsed.positionsCount,
    },
    positions: parsed.positions.map((position) => ({
      asset: position.asset,
      portfolio_scope: position.portfolioScope,
      estimated_value_eur: position.estimatedValueEur,
      estimated_value_usd: position.estimatedValueUsd,
      privy_balance: position.privyBalance,
      platform_balance: position.platformBalance,
      chain_type: position.chainType,
      chain_id: position.chainId,
      wallet_address: position.walletAddress,
    })),
  }
}

/** Agrège crypto-positions API + soldes Privy réels pour le dashboard. */
export function resolveDashboardCryptoSummary(
  cryptoPositionsRaw: unknown,
  privyRaw: unknown,
  marketRaw: unknown,
  currency: string,
): PortalCryptoSummary | null {
  let crypto: PortalCryptoSummary | null = null

  if (cryptoPositionsRaw) {
    crypto = toPortalCryptoSummary(parseCryptoPositionsPayload(cryptoPositionsRaw))
  }

  if (privyRaw) {
    const privyBuilt = buildPrivyWalletPositionsSummary(privyRaw, marketRaw, currency)
    if (privyBuilt.positions.length > 0) {
      const hasPlatform =
        crypto?.positions?.some(
          (position) =>
            position.portfolio_scope &&
            position.portfolio_scope !== 'privy' &&
            position.portfolio_scope !== 'merged',
        ) ?? false
      if (!hasPlatform) {
        crypto = toPortalCryptoSummary(privyBuilt)
      }
    }
  }

  return crypto
}

export function buildWalletRows(
  cash: PortalDashboardCash,
  crypto: PortalCryptoSummary | null,
  placements: PortalPlacementsSummary | null,
  savings: PortalSavingsSummary | null,
  currency: string,
): PortalWalletRow[] {
  const eurBalance = toNumber(cash?.cash_account?.available_balance)
  const cryptoCount = crypto?.summary?.positions_count ?? crypto?.positions?.length ?? 0
  const privyCount =
    crypto?.positions?.filter(
      (p) => p.portfolio_scope === 'privy' || p.portfolio_scope === 'merged',
    ).length ?? 0
  const cryptoValue = resolveCryptoPortfolioTotal(crypto, currency)
  const placementsCount = placements?.positions_count ?? 0
  const placementsValue = toNumber(placements?.total_earn_value_eur)
  const savingsCount = savings?.positions_count ?? savings?.positions?.length ?? 0
  const savingsValue = resolveSavingsPortfolioTotal(savings, currency)

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
      title: 'Épargne',
      subtitle:
        savingsCount > 0
          ? `${savingsCount} vault${savingsCount > 1 ? 's' : ''} DeFi`
          : 'Ouvrez votre premier vault !',
      balance: formatPortalMoney(savingsValue, currency),
      numericBalance: savingsValue,
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
      subtitle:
        privyCount > 0
          ? `${cryptoCount} crypto-actif${cryptoCount === 1 ? '' : 's'} · incl. Privy`
          : `${cryptoCount} crypto-actif${cryptoCount === 1 ? '' : 's'}`,
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
  options?: { scopedView?: boolean },
): string {
  if (!options?.scopedView) {
    const fromStats = toNumber(stats?.performance?.current_value, NaN)
    if (!Number.isNaN(fromStats)) {
      return formatPortalMoney(fromStats, stats?.currency?.toUpperCase() || currency)
    }
  }

  const sum = rows
    .filter((r) => !r.locked && (r.id === 'euro' || r.id === 'crypto' || r.id === 'savings'))
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
