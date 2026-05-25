'use client'

import { useMemo, useState } from 'react'
import { ArrowDown, ArrowLeft, ArrowUp, TrendingUp } from 'lucide-react'
import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalSavingsVaultOperationPanel } from '@/components/portal/wallet/PortalSavingsVaultOperationPanel'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  formatSavingsApyLabel,
  formatSavingsMoney,
  formatSavingsTransactionAmount,
  resolveSavingsPositionValue,
} from '@/lib/portal/portalSavingsFormat'
import type { PortalSavingsVaultDetailPayload } from '@/lib/portal/portalSavingsTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { cn } from '@/lib/utils'

type Props = {
  vaultAddress: string
}

type OperationTab = 'deposit' | 'withdraw' | null

function InfoRow({ label, value, valueClassName }: { label: string; value: string; valueClassName?: string }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5">
      <span className="font-ui text-[14px] text-v-fg-muted">{label}</span>
      <span className={cn('text-right font-ui text-[14px] font-medium tabular-nums text-v-fg', valueClassName)}>
        {value}
      </span>
    </div>
  )
}

export function PortalSavingsVaultDetailScreen({ vaultAddress }: Props) {
  const normalizedVault = vaultAddress.trim().toLowerCase()
  const [operationTab, setOperationTab] = useState<OperationTab>(null)

  const { data, loading, refreshing, error, refresh } =
    usePortalCachedScreen<PortalSavingsVaultDetailPayload>({
      cacheKey: `portal:savings-vault:${normalizedVault}`,
      url: `/api/portal/savings-wallet/${encodeURIComponent(normalizedVault)}`,
      ttlMs: 45_000,
      errorMessage: 'Impossible de charger le détail du vault.',
    })

  const currency = data?.currency ?? 'EUR'
  const position = data?.position

  const totalValue = useMemo(() => {
    if (!position) return 0
    return resolveSavingsPositionValue(position, currency)
  }, [currency, position])

  const handleOperationSuccess = () => {
    void refresh()
  }

  if (loading && !data) {
    return <PortalDashboardSkeleton />
  }

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{error}</p>
        <Button type="button" onClick={() => void refresh()}>
          Réessayer
        </Button>
      </Container>
    )
  }

  if (!data || !position) return null

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
              Épargne
            </PortalNavLink>

            <section className="overflow-hidden rounded-v-card border border-[#14532D]/20 bg-[#14532D] p-4 text-white shadow-v-subtle sm:p-5">
              <VEyebrow className="text-white/70">Vault</VEyebrow>
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
              <Button
                type="button"
                size="sm"
                className={cn('gap-1.5', operationTab === 'deposit' && 'ring-2 ring-v-green ring-offset-2')}
                onClick={() => setOperationTab((current) => (current === 'deposit' ? null : 'deposit'))}
              >
                <ArrowDown className="h-4 w-4" />
                Déposer
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className={cn('gap-1.5', operationTab === 'withdraw' && 'ring-2 ring-v-green ring-offset-2')}
                onClick={() => setOperationTab((current) => (current === 'withdraw' ? null : 'withdraw'))}
              >
                <ArrowUp className="h-4 w-4" />
                Retirer
              </Button>
            </div>
          </div>
        </PortalReveal>

        {operationTab ? (
          <PortalReveal index={1}>
            <PortalSavingsVaultOperationPanel
              vault={data.vault}
              beta={data.beta}
              activeTab={operationTab}
              onSuccess={handleOperationSuccess}
            />
          </PortalReveal>
        ) : null}

        <PortalReveal index={operationTab ? 2 : 1}>
          <article className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle">
            <div className="border-b border-v-fg-10 px-4 py-3">
              <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">Ma position</h2>
            </div>
            <div className="divide-y divide-v-fg-05 px-4">
              <InfoRow label="Solde total" value={formatSavingsMoney(totalValue, currency)} />
              <InfoRow label="Montant dans le vault" value={position.assetsInVaultDisplay} />
              <InfoRow
                label="Rendement"
                value={position.earnedYieldDisplay}
                valueClassName={pendingYield ? 'text-v-fg-muted' : 'text-v-green'}
              />
              <InfoRow label="Taux d'intérêt (APY)" value={formatSavingsApyLabel(data.averageApyBps)} />
              <InfoRow label="Valorisation USD" value={formatSavingsMoney(position.estimatedValueUsd, 'USD')} />
              <InfoRow
                label="Valorisation EUR"
                value={formatSavingsMoney(position.estimatedValueEur, 'EUR')}
              />
            </div>
          </article>
        </PortalReveal>

        <PortalReveal index={operationTab ? 3 : 2}>
          <article className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle">
            <div className="flex items-center justify-between gap-3 border-b border-v-fg-10 px-4 py-3">
              <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">Historique des transactions</h2>
            </div>
            {data.transactions.length === 0 ? (
              <p className="m-0 px-4 py-6 font-ui text-[14px] text-v-fg-muted">
                Aucune transaction pour le moment.
              </p>
            ) : (
              <ul className="m-0 list-none p-0">
                {data.transactions.map((tx) => (
                  <li
                    key={tx.id}
                    className="flex items-center gap-3 border-t border-v-fg-05 px-4 py-3.5 first:border-t-0"
                  >
                    <span
                      className={cn(
                        'inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[13px] font-semibold',
                        tx.incoming ? 'bg-v-green-bg text-v-green' : 'bg-v-error-bg text-v-error',
                      )}
                    >
                      {tx.incoming ? '↓' : '↑'}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-ui text-[14px] font-medium text-v-fg">
                        {tx.title}
                      </span>
                      <span className="mt-0.5 block truncate font-ui text-[12px] text-v-fg-muted">
                        {tx.subtitle}
                      </span>
                    </span>
                    <span className="text-right font-ui text-[14px] font-semibold tabular-nums text-v-fg">
                      {formatSavingsTransactionAmount(tx)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </article>
        </PortalReveal>

        {data.partial ? (
          <p className="m-0 font-ui text-[12px] text-v-fg-muted">
            Certaines données du vault n&apos;ont pas pu être chargées.
          </p>
        ) : null}

        <button
          type="button"
          disabled={refreshing}
          onClick={() => void refresh()}
          className="v-text-link w-fit border-0 bg-transparent p-0 font-ui text-[13px] disabled:opacity-50"
        >
          {refreshing ? 'Actualisation…' : 'Actualiser'}
        </button>
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
