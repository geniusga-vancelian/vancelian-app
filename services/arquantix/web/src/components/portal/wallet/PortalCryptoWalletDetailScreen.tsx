'use client'

import { useMemo } from 'react'
import {
  ArrowDown,
  ArrowLeft,
  ArrowLeftRight,
  ArrowUp,
  BarChart3,
  Bell,
  ChevronRight,
  ListOrdered,
  Plus,
} from 'lucide-react'
import { AppEyebrow } from '@/components/design-system/app/AppEyebrow'
import { AppMetricsList } from '@/components/design-system/app/AppMetricsList'
import { AppMetricsRow } from '@/components/design-system/app/AppMetricsRow'
import { PortalTransactionHistory } from '@/components/portal/PortalTransactionHistory'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import { cryptoBrandColor } from '@/lib/portal/cryptoInstrumentAssets'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import { formatChangePct, formatCryptoPrice } from '@/lib/portal/marketsFormat'
import { mapCryptoTransactionToHistoryItem } from '@/lib/portal/cryptoTransactionHistoryFormat'
import {
  formatCryptoMoney,
  isPrivyOnlyScope,
  perfToneClass,
  selectMoneyValue,
} from '@/lib/portal/cryptoWalletFormat'
import type { PortalCryptoWalletDetailPayload } from '@/lib/portal/cryptoWalletTypes'
import {
  PORTAL_ROUTES,
  portalCryptoInstrumentRoute,
  portalCryptoWalletTransactionsRoute,
  portalDedicatedDepositRoute,
  portalSwapRoute,
} from '@/lib/portal/portalRouting'
import { isSwapV1Token } from '@/lib/portal/swapFlowTypes'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type Props = {
  asset: string
}

export function PortalCryptoWalletDetailScreen({ asset }: Props) {
  const ticker = asset.trim().toUpperCase()
  const { data, loading, refreshing, error, refresh } =
    usePortalCachedScreen<PortalCryptoWalletDetailPayload>({
      cacheKey: `portal:crypto-wallet:${ticker}`,
      url: `/api/portal/crypto-wallet/${encodeURIComponent(ticker)}`,
      ttlMs: 45_000,
      errorMessage: 'Impossible de charger les détails.',
      scopeAware: true,
    })

  const detail = data?.detail
  const currency = data?.currency ?? 'EUR'

  const totalValue = useMemo(() => {
    if (!detail) return 0
    return selectMoneyValue(currency, detail.totalValueEur, detail.totalValueUsd) ?? 0
  }, [currency, detail])

  const heroColor = cryptoBrandColor(ticker)
  const avatarSymbol = data?.providerSymbol ?? tickerToProviderSymbol(ticker)
  const avatarLogoUrl = data?.logoUrl

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

  if (!detail || !data) return null

  const privyOnly = isPrivyOnlyScope(detail.portfolioScope)
  const dedicatedDepositHref = portalDedicatedDepositRoute(ticker)
  const canDeposit = Boolean(dedicatedDepositHref)
  const livePrice =
    selectMoneyValue(currency, detail.currentPriceEur, detail.currentPriceUsd) ?? undefined
  const changePct = data.change24hPct
  const changeLabel = changePct != null ? formatChangePct(changePct) : null
  const changePositive = changePct != null && changePct >= 0
  const unrealized =
    selectMoneyValue(currency, detail.unrealizedGainEur, detail.unrealizedGainUsd) ??
    detail.unrealizedGains
  const realized =
    selectMoneyValue(currency, detail.realizedGainEur, detail.realizedGainUsd) ?? detail.realizedGains
  const totalGain =
    selectMoneyValue(currency, detail.totalGainEur, detail.totalGainUsd) ?? detail.totalGains
  const swapHref = isSwapV1Token(ticker) ? portalSwapRoute({ to: ticker }) : PORTAL_ROUTES.walletSwap

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

            <section
              className="overflow-hidden rounded-v-card border border-black/10 p-4 text-white shadow-v-subtle sm:p-5"
              style={{ backgroundColor: heroColor }}
            >
              <AppEyebrow tone="inverse">Position</AppEyebrow>
              <div className="mt-1 flex items-center gap-3">
                <PortalCryptoAvatar
                  ticker={ticker}
                  symbol={avatarSymbol}
                  apiLogoUrl={avatarLogoUrl}
                  size="lg"
                />
                <div>
                  <h1 className="m-0 font-ui text-[22px] font-semibold leading-tight">{detail.name}</h1>
                  <p className="mt-1 mb-0 font-ui text-[28px] font-bold leading-none sm:text-[32px]">
                    {formatCryptoMoney(totalValue, currency)}
                  </p>
                </div>
              </div>
              <p className="mt-2 mb-0 font-ui text-[13px] text-white/80">
                {detail.volume} {ticker}
                {detail.portfolioScope === 'merged'
                  ? ' · incl. wallet Privy'
                  : privyOnly
                    ? ' · wallet Privy'
                    : ''}
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
              {canDeposit && dedicatedDepositHref ? (
                <Button type="button" size="sm" className="gap-1.5" asChild>
                  <PortalNavLink href={dedicatedDepositHref}>
                    <Plus className="h-4 w-4" />
                    Dépôt
                  </PortalNavLink>
                </Button>
              ) : (
                <>
                  <Button type="button" size="sm" className="gap-1.5" disabled>
                    <ArrowUp className="h-4 w-4" />
                    Acheter
                  </Button>
                  <Button type="button" variant="outline" size="sm" className="gap-1.5" disabled>
                    <ArrowDown className="h-4 w-4" />
                    Vendre
                  </Button>
                </>
              )}
              <Button type="button" variant="outline" size="sm" className="gap-1.5" asChild>
                <PortalNavLink href={swapHref}>
                  <ArrowLeftRight className="h-4 w-4" />
                  Échanger
                </PortalNavLink>
              </Button>
              <Button type="button" variant="outline" size="sm" className="gap-1.5" disabled>
                <ListOrdered className="h-4 w-4" />
                Ordres
              </Button>
              <Button type="button" variant="outline" size="sm" className="gap-1.5" disabled>
                <Bell className="h-4 w-4" />
                Alertes
              </Button>
              <Button type="button" variant="outline" size="sm" className="gap-1.5" disabled>
                <BarChart3 className="h-4 w-4" />
                Stats
              </Button>
            </div>
          </div>
        </PortalReveal>

        <PortalReveal index={1}>
          <article className="card-simple overflow-hidden !w-full">
            <div className="border-b border-v-fg-10 px-4 py-3">
              <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">Instrument</h2>
            </div>
            <PortalNavLink
              href={portalCryptoInstrumentRoute(ticker)}
              className="flex items-center gap-3 px-4 py-3.5 no-underline transition-colors hover:bg-v-card-hover"
            >
              <PortalCryptoAvatar
                ticker={ticker}
                symbol={avatarSymbol}
                apiLogoUrl={avatarLogoUrl}
                size="md"
              />
              <span className="min-w-0 flex-1">
                <span className="block font-ui text-[15px] font-semibold text-v-fg">{detail.name}</span>
                <span className="mt-0.5 block font-ui text-[13px] text-v-fg-muted">
                  {livePrice != null
                    ? formatCryptoPrice(livePrice, currency === 'USD' ? 'USD' : 'EUR')
                    : '—'}
                  {changeLabel ? (
                    <>
                      {' · '}
                      <span className={changePositive ? 'text-v-green' : 'text-v-error'}>
                        {changeLabel}
                      </span>
                    </>
                  ) : null}
                </span>
              </span>
              <ChevronRight className="h-4 w-4 text-v-fg-muted" />
            </PortalNavLink>
          </article>
        </PortalReveal>

        <PortalReveal index={2}>
          <section className="flex w-full flex-col gap-3">
            <header>
              <h2 className="module-head__title">My position</h2>
            </header>
            <AppMetricsList variant="plain">
              <AppMetricsRow label="Volume" value={`${detail.volume} ${ticker}`} />
              <AppMetricsRow label="Solde total" value={formatCryptoMoney(totalValue, currency)} />
              <AppMetricsRow
                label="Gains en cours"
                value={unrealized != null ? formatCryptoMoney(unrealized, currency) : '—'}
                valueClassName={perfToneClass(detail.unrealizedGainsPct ?? unrealized)}
              />
              <AppMetricsRow
                label="Prix moyen d'achat"
                value={
                  selectMoneyValue(currency, detail.avgBuyPriceEur, detail.avgBuyPriceUsd) != null
                    ? formatCryptoMoney(
                        selectMoneyValue(currency, detail.avgBuyPriceEur, detail.avgBuyPriceUsd)!,
                        currency,
                      )
                    : '—'
                }
              />
              <AppMetricsRow
                label="Prix actuel"
                value={livePrice != null ? formatCryptoMoney(livePrice, currency) : '—'}
              />
              <AppMetricsRow
                label="Gains encaissés"
                value={realized != null ? formatCryptoMoney(realized, currency) : '—'}
                valueClassName={perfToneClass(realized)}
              />
              <AppMetricsRow
                label="Total des gains"
                value={totalGain != null ? formatCryptoMoney(totalGain, currency) : '—'}
                valueClassName={perfToneClass(detail.totalGainsPct ?? totalGain)}
              />
            </AppMetricsList>
          </section>
        </PortalReveal>

        <PortalReveal index={3}>
          <PortalTransactionHistory
            title="Transactions history"
            seamless
            moreHref={portalCryptoWalletTransactionsRoute(ticker)}
            moreLabel="All transactions"
            items={data.transactions.slice(0, 12).map((tx) =>
              mapCryptoTransactionToHistoryItem(tx, currency),
            )}
          />
        </PortalReveal>

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
