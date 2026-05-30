'use client'

import { useMemo, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { AppFilterChip } from '@/components/design-system/app/AppFilterChip'
import { PortalTransactionHistoryRows } from '@/components/portal/PortalTransactionHistory'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  formatCryptoTransactionMonthChip,
  groupCryptoTransactionsByDay,
  listCryptoTransactionMonthKeys,
} from '@/lib/portal/cryptoTransactionHistoryFormat'
import type { PortalCryptoWalletDetailPayload } from '@/lib/portal/cryptoWalletTypes'
import { portalCryptoWalletAssetRoute } from '@/lib/portal/portalRouting'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type Props = {
  asset: string
}

export function PortalCryptoWalletTransactionsScreen({ asset }: Props) {
  const ticker = asset.trim().toUpperCase()
  const { data, loading, refreshing, error, refresh } =
    usePortalCachedScreen<PortalCryptoWalletDetailPayload>({
      cacheKey: `portal:crypto-wallet:${ticker}`,
      url: `/api/portal/crypto-wallet/${encodeURIComponent(ticker)}`,
      ttlMs: 45_000,
      errorMessage: 'Unable to load transactions.',
      scopeAware: true,
    })

  const [selectedMonth, setSelectedMonth] = useState<string | null>(null)
  const currency = data?.currency ?? 'EUR'
  const detail = data?.detail
  const transactions = data?.transactions ?? []

  const monthKeys = useMemo(() => listCryptoTransactionMonthKeys(transactions), [transactions])
  const sections = useMemo(
    () => groupCryptoTransactionsByDay(transactions, currency, selectedMonth, ticker),
    [transactions, currency, selectedMonth, ticker],
  )

  if (loading && !data) {
    return <PortalDashboardSkeleton />
  }

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{error}</p>
        <Button type="button" onClick={() => void refresh()}>
          Retry
        </Button>
      </Container>
    )
  }

  if (!data) return null

  const assetLabel = detail?.name?.trim() || ticker
  const backHref = portalCryptoWalletAssetRoute(ticker)
  const emptyMonth = selectedMonth != null && sections.length === 0

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <div className="flex flex-col gap-4">
            <PortalNavLink
              href={backHref}
              className="inline-flex w-fit items-center gap-1.5 font-ui text-[13px] text-v-fg-muted no-underline transition-colors hover:text-v-fg"
            >
              <ArrowLeft className="h-4 w-4" />
              {assetLabel}
            </PortalNavLink>
            <h1 className="module-head__title m-0">All transactions</h1>
          </div>
        </PortalReveal>

        {monthKeys.length > 1 ? (
          <PortalReveal index={1}>
            <div className="chips chips--scroll">
              <AppFilterChip
                label="All"
                selected={selectedMonth == null}
                onClick={() => setSelectedMonth(null)}
              />
              {monthKeys.map((monthKey) => (
                <AppFilterChip
                  key={monthKey}
                  label={formatCryptoTransactionMonthChip(monthKey)}
                  selected={selectedMonth === monthKey}
                  onClick={() => setSelectedMonth(monthKey)}
                />
              ))}
            </div>
          </PortalReveal>
        ) : null}

        <PortalReveal index={monthKeys.length > 1 ? 2 : 1}>
          {transactions.length === 0 ? (
            <PortalTransactionHistoryRows items={[]} />
          ) : emptyMonth ? (
            <p className="m-0 px-1 font-ui text-[14px] text-v-fg-muted">No transactions this month.</p>
          ) : (
            <div className="flex flex-col gap-6">
              {sections.map((section) => (
                <section key={section.dayLabel} className="flex flex-col gap-3">
                  <h2 className="m-0 px-1 font-ui text-[15px] font-semibold text-v-fg">
                    {section.dayLabel}
                  </h2>
                  <PortalTransactionHistoryRows items={section.items} seamless />
                </section>
              ))}
            </div>
          )}
        </PortalReveal>

        <button
          type="button"
          disabled={refreshing}
          onClick={() => void refresh()}
          className="v-text-link w-fit border-0 bg-transparent p-0 font-ui text-[13px] disabled:opacity-50"
        >
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
