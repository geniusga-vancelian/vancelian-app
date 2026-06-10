'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, PieChart } from 'lucide-react'
import {
  AppBalanceCardVariantB,
  type AppBalanceCardFab,
} from '@/components/design-system/app/AppBalanceCardVariantB'
import {
  AppAccountSummaryList,
} from '@/components/design-system/app/AppAccountSummaryList'
import {
  AppAccountSummaryRow,
} from '@/components/design-system/app/AppAccountSummaryRow'
import { AppButton } from '@/components/design-system/app/AppButton'
import { AppMetricsList } from '@/components/design-system/app/AppMetricsList'
import { AppMetricsRow } from '@/components/design-system/app/AppMetricsRow'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalTransactionHistory } from '@/components/portal/PortalTransactionHistory'
import { PortalBundleAllocationReadOnlyPanel } from '@/components/portal/bundles/PortalBundleAllocationReadOnlyPanel'
import { PortalLazyBundleActiveOperation } from '@/components/portal/bundles/PortalLazyBundleActiveOperation'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import { cryptoPositionHeaderTitle } from '@/lib/portal/instrumentDetailFormat'
import {
  bundlePositionDisplayValue,
  bundleSummaryMarketValue,
  formatCryptoMoney,
  formatPerfPct,
  perfToneClass,
  selectMoneyValue,
} from '@/lib/portal/cryptoWalletFormat'
import { mapCryptoTransactionToHistoryItem } from '@/lib/portal/cryptoTransactionHistoryFormat'
import { splitBundleHoldings } from '@/lib/portal/bundleWithdrawFormat'
import type { PortalBundlePosition, PortalCryptoWalletBundleDetailPayload } from '@/lib/portal/cryptoWalletTypes'
import { CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW } from '@/lib/portal/cryptoWalletTypes'
import {
  PORTAL_ROUTES,
  portalBundleInvestRoute,
  portalCryptoWalletAssetRoute,
} from '@/lib/portal/portalRouting'
import { reconcileStaleBundlePortfolioState } from '@/lib/portal/bundleClient'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type Props = {
  portfolioId: string
}

function formatBundlePositionSubtitle(position: PortalBundlePosition): string {
  if (position.positionType === 'cash' && position.quantity > 0) {
    return `${position.quantity.toFixed(4)} ${position.asset}`
  }
  if (position.quantity > 0) {
    return `${position.quantity.toFixed(6)} ${position.asset}`
  }
  if (position.targetWeight != null && position.targetWeight > 0) {
    return `Target ${(position.targetWeight * 100).toFixed(1)}%`
  }
  return 'Pending allocation'
}

function bundlePositionValue(position: PortalBundlePosition, currency: string): number {
  return bundlePositionDisplayValue(position, currency)
}

export function PortalCryptoWalletBundleDetailScreen({ portfolioId }: Props) {
  const id = portfolioId.trim()
  const [hasActiveBundleOperation, setHasActiveBundleOperation] = useState(false)
  const [staleReconciled, setStaleReconciled] = useState(false)
  const activeOpStableRef = useRef({ value: false, streak: 0 })

  const handleActiveOperationChange = useCallback((active: boolean) => {
    const prev = activeOpStableRef.current
    if (prev.value === active) {
      prev.streak += 1
    } else {
      activeOpStableRef.current = { value: active, streak: 1 }
    }
    if (activeOpStableRef.current.streak >= 2) {
      setHasActiveBundleOperation(active)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    activeOpStableRef.current = { value: false, streak: 0 }
    setStaleReconciled(false)
    setHasActiveBundleOperation(false)

    void reconcileStaleBundlePortfolioState(id)
      .then((result) => {
        if (cancelled) return
        const active = result.active_operation?.status === 'active'
        activeOpStableRef.current = { value: active, streak: 2 }
        setHasActiveBundleOperation(active)
        setStaleReconciled(true)
      })
      .catch(() => {
        if (!cancelled) setStaleReconciled(true)
      })

    return () => {
      cancelled = true
    }
  }, [id])
  const { data, loading, refreshing, error, refresh } =
    usePortalCachedScreen<PortalCryptoWalletBundleDetailPayload>({
      cacheKey: `portal:crypto-wallet:bundle:${id}`,
      url: `/api/portal/crypto-wallet/bundle/${encodeURIComponent(id)}`,
      ttlMs: 45_000,
      errorMessage: 'Unable to load bundle details.',
    })

  const bundle = data?.bundle
  const currency = data?.currency ?? 'EUR'

  const totalValue = useMemo(() => {
    if (!bundle) return 0
    return bundleSummaryMarketValue(bundle, currency)
  }, [bundle, currency])

  const unrealizedGain = useMemo(() => {
    if (!bundle) return undefined
    const market = bundleSummaryMarketValue(bundle, currency)
    const invested =
      selectMoneyValue(currency, bundle.totalCostBasis, bundle.totalCostBasisUsd) ?? 0
    if (invested <= 0) return undefined
    return market - invested
  }, [bundle, currency])

  const allocationRows = useMemo(() => {
    if (!bundle?.positions?.length) return []
    return [...bundle.positions]
      .filter((p) => p.positionType !== 'cash' || p.quantity > 0.001)
      .sort((a, b) => bundlePositionValue(b, currency) - bundlePositionValue(a, currency))
  }, [bundle?.positions, currency])

  const holdingsSplit = useMemo(
    () => splitBundleHoldings(bundle?.positions, currency),
    [bundle?.positions, currency],
  )

  const transactionPreview = useMemo(() => {
    const txs = data?.transactions ?? []
    return txs
      .slice(0, CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW)
      .map((tx) =>
        mapCryptoTransactionToHistoryItem(tx, currency, {
          projectionContext: 'bundle',
          bundlePortfolioId: id,
        }),
      )
  }, [currency, data?.transactions])

  const hasMoreTransactions =
    (data?.transactions?.length ?? 0) > CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW

  const canWithdraw = holdingsSplit.totalWithdrawableEstimate > 0.001

  const bundleFabs = useMemo((): AppBalanceCardFab[] => {
    return [
      {
        id: 'deposit',
        label: 'Deposit',
        icon: 'add',
        href: portalBundleInvestRoute(id, 'invest'),
      },
      {
        id: 'withdraw',
        label: 'Withdraw',
        icon: 'send-1',
        disabled: !canWithdraw || refreshing,
        href: canWithdraw ? portalBundleInvestRoute(id, 'withdraw') : undefined,
      },
      { id: 'swap', label: 'Swap', icon: 'exchange', disabled: true },
      { id: 'invest', label: 'Invest', icon: 'trending-up', href: PORTAL_ROUTES.invest },
    ]
  }, [canWithdraw, id, refreshing])

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

  if (!bundle || !data) return null

  const perfLabel = formatPerfPct(bundle.performancePct)
  const countLabel = `${bundle.assetsCount} asset${bundle.assetsCount === 1 ? '' : 's'}`

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <div className="flex flex-col gap-4">
            <PortalNavLink
              href={PORTAL_ROUTES.cryptoWallet}
              className="inline-flex w-fit items-center gap-1.5 font-ui text-[13px] text-v-fg-muted no-underline transition-colors hover:text-v-fg"
            >
              <ArrowLeft className="h-4 w-4" />
              Crypto wallet
            </PortalNavLink>

            <AppBalanceCardVariantB
              welcomeLeading={
                <span className="inline-flex h-[46px] w-[46px] shrink-0 items-center justify-center rounded-full bg-v-blue text-white">
                  <PieChart className="h-6 w-6" strokeWidth={1.75} aria-hidden />
                </span>
              }
              welcomeHi="Bundle"
              welcomeName={bundle.portfolioName}
              showAvatar={false}
              balanceLabel={formatCryptoMoney(totalValue, currency)}
              balanceLabelText="Market value"
              metaLabel={countLabel}
              showChange={false}
              chartValues={data.historyPoints}
              showChart
              balancePending={refreshing}
              fabs={bundleFabs}
              className="pt-0"
            />
          </div>
        </PortalReveal>

        <PortalReveal index={1}>
          <section className="flex w-full flex-col gap-3">
            <AppSectionHeader title="My investment" />
            <AppMetricsList variant="plain">
              <AppMetricsRow
                label="Market value"
                value={formatCryptoMoney(bundleSummaryMarketValue(bundle, currency), currency)}
              />
              <AppMetricsRow
                label="Cash leg (USDC)"
                value={formatCryptoMoney(holdingsSplit.cashLegDisplayValue, currency)}
              />
              <AppMetricsRow
                label="Allocated assets"
                value={formatCryptoMoney(holdingsSplit.spotNotional, currency)}
              />
              <AppMetricsRow
                label="Total invested"
                value={formatCryptoMoney(
                  selectMoneyValue(currency, bundle.totalCostBasis, bundle.totalCostBasisUsd) ??
                    bundle.totalCostBasis,
                  currency,
                )}
              />
              <AppMetricsRow
                label="Unrealized P&L"
                value={
                  unrealizedGain != null ? formatCryptoMoney(unrealizedGain, currency) : '—'
                }
                valueClassName={perfToneClass(unrealizedGain)}
              />
              <AppMetricsRow
                label="Performance"
                value={perfLabel ?? '—'}
                valueClassName={perfToneClass(bundle.performancePct)}
              />
              <AppMetricsRow label="Assets in portfolio" value={String(bundle.assetsCount)} />
            </AppMetricsList>
          </section>
        </PortalReveal>

        {allocationRows.length > 0 ? (
          <PortalReveal index={2}>
            <section className="flex w-full flex-col gap-3">
              <AppSectionHeader title="Allocation" />
              <AppAccountSummaryList>
                {allocationRows.map((position) => {
                  const valueLabel = formatCryptoMoney(
                    bundlePositionValue(position, currency),
                    currency,
                  )
                  const href =
                    position.positionType === 'spot' && position.quantity > 0
                      ? portalCryptoWalletAssetRoute(position.asset)
                      : undefined

                  return (
                    <AppAccountSummaryRow
                      key={`${position.asset}-${position.positionType}`}
                      href={href}
                      LinkComponent={href ? PortalNavLink : undefined}
                      leading={
                        position.positionType === 'cash' ? (
                          <span className="inline-flex h-[46px] w-[46px] shrink-0 items-center justify-center rounded-full bg-v-fg-10 font-ui text-[13px] font-semibold text-v-fg-muted">
                            $
                          </span>
                        ) : (
                          <PortalCryptoAvatar ticker={position.asset} size="lg" />
                        )
                      }
                      title={cryptoPositionHeaderTitle(position.asset, position.asset)}
                      subtitle={formatBundlePositionSubtitle(position)}
                      amount={valueLabel}
                      showChevron={Boolean(href)}
                    />
                  )
                })}
              </AppAccountSummaryList>
            </section>
          </PortalReveal>
        ) : null}

        {staleReconciled ? (
          <PortalReveal index={3}>
            <PortalLazyBundleActiveOperation
              portfolioId={id}
              portfolioName={bundle.portfolioName}
              onRefresh={() => void refresh()}
              onActiveChange={handleActiveOperationChange}
            />
          </PortalReveal>
        ) : null}

        {staleReconciled && !hasActiveBundleOperation ? (
          <PortalReveal index={4}>
            <PortalBundleAllocationReadOnlyPanel
              portfolioId={id}
              portfolioName={bundle.portfolioName}
              positions={bundle.positions}
              currency={currency}
              cashLegDisplayValue={holdingsSplit.cashLegDisplayValue}
              onRefresh={() => void refresh()}
            />
          </PortalReveal>
        ) : null}

        <PortalReveal index={5}>
          <section className="flex w-full flex-col gap-3">
            <AppSectionHeader title="Withdraw" />
            <p className="m-0 font-ui text-[13px] text-v-fg-muted">
              Transfer bundle value to Self Trading. Funds are credited only after accounting release
              (RELEASED).
            </p>
            {canWithdraw ? (
              <Button type="button" variant="secondary" asChild>
                <PortalNavLink href={portalBundleInvestRoute(id, 'withdraw')}>
                  Withdraw to Self Trading
                </PortalNavLink>
              </Button>
            ) : (
              <AppButton type="button" variant="secondary" disabled>
                Withdraw to Self Trading
              </AppButton>
            )}
          </section>
        </PortalReveal>

        <PortalReveal index={6}>
          <section className="flex w-full flex-col gap-3">
            <AppSectionHeader title="Activity" size="sm" />
            {transactionPreview.length > 0 ? (
              <PortalTransactionHistory title="" seamless items={transactionPreview} />
            ) : (
              <p className="m-0 font-ui text-[13px] text-v-fg-muted">
                No activity recorded for this bundle yet.
              </p>
            )}
            {hasMoreTransactions ? (
              <p className="m-0 font-ui text-[12px] text-v-fg-muted">
                {data?.transactions?.length ?? 0} operations in total — refresh to see the full list.
              </p>
            ) : null}
          </section>
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
