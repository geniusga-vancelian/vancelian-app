import type { PortalDashboardPayload } from '@/lib/portal/dashboardTypes'

/** Données critiques affichables (solde / perf header) — core ou composite stale. */
export function hasDashboardCriticalDisplayData(
  data: PortalDashboardPayload | null | undefined,
): boolean {
  if (!data) return false
  return Boolean(data.globalStatistics ?? data.bootstrap ?? data.cash)
}

/** Allocation portefeuille (crypto, placements, savings) — section portfolio. */
export function hasDashboardPortfolioDisplayData(
  data: PortalDashboardPayload | null | undefined,
): boolean {
  if (!data) return false
  return Boolean(data.crypto ?? data.placements ?? data.savings)
}

/** Skeleton plein écran uniquement sans aucune donnée critique (y compris cache stale). */
export function shouldShowDashboardFullSkeleton(
  loading: boolean,
  data: PortalDashboardPayload | null,
): boolean {
  return loading && !hasDashboardCriticalDisplayData(data)
}

export type DashboardBalancePendingInput = {
  portfolioLoading: boolean
  refreshing: boolean
  data: PortalDashboardPayload | null
}

/** Stale-first : pas de pulse header si globalStatistics déjà affichables. */
export function shouldShowDashboardBalancePending(input: DashboardBalancePendingInput): boolean {
  if (hasDashboardCriticalDisplayData(input.data)) {
    if (input.refreshing && !input.portfolioLoading) return false
    if (input.portfolioLoading && hasDashboardPortfolioDisplayData(input.data)) return false
    if (!input.portfolioLoading && !input.refreshing) return false
    return input.portfolioLoading && !hasDashboardPortfolioDisplayData(input.data)
  }
  return input.portfolioLoading || input.refreshing
}

/** Comptes / allocation : pending seulement si portfolio absent et en chargement. */
export function shouldShowDashboardAccountsPending(input: DashboardBalancePendingInput): boolean {
  if (!input.portfolioLoading && !input.refreshing) return false
  if (hasDashboardPortfolioDisplayData(input.data)) return false
  return input.portfolioLoading
}
