import type {
  PortalDashboardCorePayload,
  PortalDashboardPayload,
  PortalDashboardPortfolioPayload,
} from '@/lib/portal/dashboardTypes'

export function resolveDashboardReferenceCurrency(bootstrap: unknown): string {
  if (!bootstrap || typeof bootstrap !== 'object') return 'EUR'
  const client = (bootstrap as Record<string, unknown>).client
  if (!client || typeof client !== 'object') return 'EUR'
  return String((client as Record<string, unknown>).reference_currency ?? 'EUR')
    .trim()
    .toUpperCase()
}

/** Agrège core + portfolio (news chargé côté client). Safe client + server. */
export function mergePortalDashboardPayload(
  core: PortalDashboardCorePayload | null | undefined,
  portfolio: PortalDashboardPortfolioPayload | null | undefined,
  newsWidget: PortalDashboardPayload['newsWidget'] = null,
): PortalDashboardPayload | null {
  if (!core && !portfolio) return null

  return {
    bootstrap: core?.bootstrap ?? null,
    profile: core?.profile ?? null,
    cash: core?.cash ?? null,
    globalStatistics: core?.globalStatistics ?? null,
    globalHistory: core?.globalHistory ?? null,
    notifications: core?.notifications ?? null,
    privyPersonWallets: core?.privyPersonWallets ?? null,
    crypto: portfolio?.crypto ?? null,
    placements: portfolio?.placements ?? null,
    savings: portfolio?.savings ?? null,
    newsWidget,
    partial: Boolean(core?.partial || portfolio?.partial),
  }
}
