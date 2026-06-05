'use client'

import { useMemo } from 'react'
import { ArrowDown, ArrowLeft, ArrowUp, TrendingUp } from 'lucide-react'
import { AppEyebrow } from '@/components/design-system/app/AppEyebrow'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalTransactionHistory } from '@/components/portal/PortalTransactionHistory'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  formatSavingsApyLabel,
  formatSavingsMoney,
  formatSavingsTransactionAmount,
  resolveSavingsPositionValue,
} from '@/lib/portal/portalSavingsFormat'
import type { PortalSavingsVaultDetailPayload } from '@/lib/portal/portalSavingsTypes'
import { PORTAL_ROUTES, resolvePortalDefiVaultFlowRoute } from '@/lib/portal/portalRouting'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type Props = {
  vaultAddress: string
}

function InfoRow({ label, value, valueClassName }: { label: string; value: string; valueClassName?: string }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5">
      <span className="font-ui text-[14px] text-v-fg-muted">{label}</span>
      <span className={`text-right font-ui text-[14px] font-medium tabular-nums text-v-fg ${valueClassName ?? ''}`}>
        {value}
      </span>
    </div>
  )
}

export function PortalSavingsVaultDetailScreen({ vaultAddress }: Props) {
  const normalizedVault = vaultAddress.trim().toLowerCase()

  const { data, loading, refreshing, error, refresh } =
    usePortalCachedScreen<PortalSavingsVaultDetailPayload>({
      cacheKey: `portal:savings-vault:${normalizedVault}`,
      url: `/api/portal/savings-wallet/${encodeURIComponent(normalizedVault)}`,
      ttlMs: 45_000,
      errorMessage: 'Unable to load vault details.',
      scopeAware: true,
    })

  const currency = data?.currency ?? 'EUR'
  const position = data?.position

  const flowRoutes = useMemo(() => {
    if (!data?.vault) return null
    const target = {
      integrationMode: data.integrationMode,
      vaultAddress: data.vault.vaultAddress,
      vaultId: data.vault.id,
    }
    return {
      deposit: resolvePortalDefiVaultFlowRoute(target, 'invest', { returnTo: 'savings' }),
      withdraw: resolvePortalDefiVaultFlowRoute(target, 'withdraw', { returnTo: 'savings' }),
    }
  }, [data?.integrationMode, data?.vault])

  const totalValue = useMemo(() => {
    if (!position) return 0
    return resolveSavingsPositionValue(position, currency)
  }, [currency, position])

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

  if (!data || !position || !flowRoutes) return null

  const pendingYield = position.yieldSyncStatus === 'pending'

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <div className="flex flex-col gap-4">
            <PortalNavLink
              href={PORTAL_ROUTES.savingsWallet}
              className="inline-flex w-fit items-center gap-1.5 font-ui text-[13px] text-v-fg-muted no-underline transition-colors hover:text-v-fg"
            >
              <ArrowLeft className="h-4 w-4" />
              Savings
            </PortalNavLink>

            <section className="overflow-hidden rounded-v-card border border-[#14532D]/20 bg-[#14532D] p-4 text-white shadow-v-subtle sm:p-5">
              <AppEyebrow className="text-white/70">Vault</AppEyebrow>
              <div className="mt-1 flex items-center gap-3">
                <span className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-v-input bg-white/15 text-white">
                  <TrendingUp className="h-6 w-6" strokeWidth={1.75} />
                </span>
                <div>
                  <h1 className="m-0 font-ui text-[22px] font-semibold leading-tight">{data.vaultName}</h1>
                  <p className="mt-1 mb-0 font-ui text-[28px] font-bold leading-none sm:text-[32px]">
                    {formatSavingsMoney(totalValue, currency)}
                  </p>
                </div>
              </div>
              <p className="mt-2 mb-0 font-ui text-[13px] text-white/80">
                {position.assetsInVaultDisplay} · APY {data.averageApyDisplay}
              </p>
              <div className="mt-4 border-t border-white/15 pt-4">
                <PortalPerformanceChart
                  values={data.historyPoints}
                  tone="dark"
                  height={88}
                  className="text-white"
                />
              </div>
            </section>

            <div className="flex flex-wrap gap-2">
              <Button type="button" size="sm" className="gap-1.5" asChild>
                <PortalNavLink href={flowRoutes.deposit}>
                  <ArrowDown className="h-4 w-4" />
                  Deposit
                </PortalNavLink>
              </Button>
              <Button type="button" variant="outline" size="sm" className="gap-1.5" asChild>
                <PortalNavLink href={flowRoutes.withdraw}>
                  <ArrowUp className="h-4 w-4" />
                  Withdraw
                </PortalNavLink>
              </Button>
            </div>
          </div>
        </PortalReveal>

        <PortalReveal index={1}>
          <article className="card-simple overflow-hidden !w-full">
            <div className="border-b border-v-fg-10 px-4 py-3">
              <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">My position</h2>
            </div>
            <div className="divide-y divide-v-fg-05 px-4">
              <InfoRow label="Total balance" value={formatSavingsMoney(totalValue, currency)} />
              <InfoRow label="Amount in vault" value={position.assetsInVaultDisplay} />
              <InfoRow
                label="Yield"
                value={position.earnedYieldDisplay}
                valueClassName={pendingYield ? 'text-v-fg-muted' : 'text-v-green'}
              />
              <InfoRow label="Interest rate (APY)" value={formatSavingsApyLabel(data.averageApyBps)} />
              <InfoRow label="USD valuation" value={formatSavingsMoney(position.estimatedValueUsd, 'USD')} />
              <InfoRow label="EUR valuation" value={formatSavingsMoney(position.estimatedValueEur, 'EUR')} />
            </div>
          </article>
        </PortalReveal>

        <PortalReveal index={2}>
          <PortalTransactionHistory
            title="Transaction history"
            items={data.transactions.map((tx) => ({
              id: tx.id,
              title: tx.title,
              subtitle: tx.subtitle,
              amount: formatSavingsTransactionAmount(tx),
              incoming: tx.incoming,
              amountTone: tx.incoming ? 'in' : 'out',
            }))}
          />
        </PortalReveal>

        {data.partial ? (
          <p className="m-0 font-ui text-[12px] text-v-fg-muted">
            Some vault data could not be loaded.
          </p>
        ) : null}

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
