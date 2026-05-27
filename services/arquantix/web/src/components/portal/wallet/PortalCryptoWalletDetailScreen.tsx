'use client'

import { useMemo } from 'react'
import { ArrowLeft } from 'lucide-react'
import {
  AppBalanceCardVariantB,
  type AppBalanceCardFab,
  type AppBalanceCardTopAction,
} from '@/components/design-system/app/AppBalanceCardVariantB'
import { AppMetricsList } from '@/components/design-system/app/AppMetricsList'
import { AppMetricsRow } from '@/components/design-system/app/AppMetricsRow'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalTransactionHistory } from '@/components/portal/PortalTransactionHistory'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalCryptoAssetList } from '@/components/portal/markets/PortalCryptoAssetList'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import type { PortalChain } from '@/config/portalChains'
import {
  assetToMarketProviderSymbol,
  cryptoPositionHeaderTitle,
} from '@/lib/portal/instrumentDetailFormat'
import { formatCryptoPrice } from '@/lib/portal/marketsFormat'
import { mapCryptoTransactionToHistoryItem } from '@/lib/portal/cryptoTransactionHistoryFormat'
import {
  formatCryptoMoney,
  perfToneClass,
  selectMoneyValue,
} from '@/lib/portal/cryptoWalletFormat'
import {
  CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW,
  type PortalCryptoWalletDetailPayload,
} from '@/lib/portal/cryptoWalletTypes'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import {
  PORTAL_ROUTES,
  portalCryptoWalletTransactionsRoute,
  portalSwapBuyRoute,
  portalSwapSellRoute,
} from '@/lib/portal/portalRouting'
import { isPortalSwapTradeAsset } from '@/lib/portal/swapFlowTypes'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type Props = {
  asset: string
}

const MIN_TRADE_VALUE_USD = 1

function resolveSwapChainForAsset(asset: string, portalChain: PortalChain): string | undefined {
  if (asset === 'CBBTC') return 'base'
  if (portalChain === 'solana') return undefined
  return portalChain
}

export function PortalCryptoWalletDetailScreen({ asset }: Props) {
  const ticker = asset.trim().toUpperCase()
  const { chain } = usePortalChainContext()
  const { data, loading, refreshing, error, refresh } =
    usePortalCachedScreen<PortalCryptoWalletDetailPayload>({
      cacheKey: `portal:crypto-wallet:${ticker}`,
      url: `/api/portal/crypto-wallet/${encodeURIComponent(ticker)}`,
      ttlMs: 45_000,
      errorMessage: 'Unable to load position details.',
      scopeAware: true,
    })

  const detail = data?.detail
  const currency = data?.currency ?? 'EUR'

  const totalValue = useMemo(() => {
    if (!detail) return 0
    return selectMoneyValue(currency, detail.totalValueEur, detail.totalValueUsd) ?? 0
  }, [currency, detail])

  const valueUsd = useMemo(() => {
    if (!detail) return 0
    return selectMoneyValue('USD', detail.totalValueEur, detail.totalValueUsd) ?? 0
  }, [detail])

  const avatarSymbol = data?.providerSymbol ?? assetToMarketProviderSymbol(ticker)
  const avatarLogoUrl = data?.logoUrl

  const canTrade = valueUsd > MIN_TRADE_VALUE_USD && isPortalSwapTradeAsset(ticker)
  const swapChainKey = resolveSwapChainForAsset(ticker, chain)

  const headerTopActions = useMemo(
    (): AppBalanceCardTopAction[] => [
      { id: 'alerts', icon: 'bell', label: 'Alerts', disabled: true },
      { id: 'stats', icon: 'pie-chart', label: 'Stats', disabled: true },
    ],
    [],
  )

  const headerFabs = useMemo((): AppBalanceCardFab[] => {
    const buyHref =
      canTrade && swapChainKey ? portalSwapBuyRoute(ticker, swapChainKey) : undefined
    const sellHref =
      canTrade && swapChainKey ? portalSwapSellRoute(ticker, swapChainKey) : undefined

    return [
      {
        id: 'buy',
        label: 'Buy',
        icon: 'add',
        href: buyHref,
        disabled: !buyHref,
      },
      {
        id: 'sell',
        label: 'Sell',
        icon: 'arrow-up-right',
        href: sellHref,
        disabled: !sellHref,
      },
      {
        id: 'swap',
        label: 'Swap',
        icon: 'exchange',
        href: PORTAL_ROUTES.walletSwap,
      },
    ]
  }, [canTrade, swapChainKey, ticker])

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

  if (!detail || !data) return null

  const livePrice =
    selectMoneyValue(currency, detail.currentPriceEur, detail.currentPriceUsd) ?? undefined
  const changePct = data.change24hPct ?? 0
  const unrealized =
    selectMoneyValue(currency, detail.unrealizedGainEur, detail.unrealizedGainUsd) ??
    detail.unrealizedGains
  const realized =
    selectMoneyValue(currency, detail.realizedGainEur, detail.realizedGainUsd) ?? detail.realizedGains
  const totalGain =
    selectMoneyValue(currency, detail.totalGainEur, detail.totalGainUsd) ?? detail.totalGains
  const transactions = data.transactions
  const hasMoreTransactions =
    transactions.length > CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW
  const previewTransactions = transactions.slice(0, CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW)

  const scopeMeta = detail.portfolioScope === 'merged' ? ' · incl. wallet intégré' : ''

  const instrumentPriceLabel =
    livePrice != null
      ? formatCryptoPrice(livePrice, currency === 'USD' ? 'USD' : 'EUR')
      : '—'
  const instrumentMarketRow = {
    id: ticker,
    name: cryptoPositionHeaderTitle(ticker, detail.name),
    ticker,
    symbol: avatarSymbol,
    priceLabel: instrumentPriceLabel,
    priceUsd: livePrice ?? 0,
    changePct,
    logoUrl: avatarLogoUrl ?? null,
  }

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
                <PortalCryptoAvatar
                  ticker={ticker}
                  symbol={avatarSymbol}
                  apiLogoUrl={avatarLogoUrl}
                  size="lg"
                />
              }
              welcomeHi={cryptoPositionHeaderTitle(ticker, detail.name).toUpperCase()}
              welcomeName={ticker}
              showAvatar={false}
              topActions={headerTopActions}
              balanceLabel={formatCryptoMoney(totalValue, currency)}
              balanceLabelText="Estimated value"
              metaLabel={`${detail.volume} ${ticker}${scopeMeta}`}
              showChange={false}
              chartValues={data.historyPoints}
              showChart
              balancePending={refreshing}
              fabs={headerFabs}
              className="pt-0"
            />
          </div>
        </PortalReveal>

        <PortalReveal index={1}>
          <section className="flex w-full flex-col gap-3">
            <AppSectionHeader title="Instrument" />
            <PortalCryptoAssetList assets={[instrumentMarketRow]} />
          </section>
        </PortalReveal>

        <PortalReveal index={2}>
          <section className="flex w-full flex-col gap-3">
            <AppSectionHeader title="My position" />
            <AppMetricsList variant="plain">
              <AppMetricsRow label="Volume" value={`${detail.volume} ${ticker}`} />
              <AppMetricsRow label="Total balance" value={formatCryptoMoney(totalValue, currency)} />
              <AppMetricsRow
                label="Unrealized P&L"
                value={unrealized != null ? formatCryptoMoney(unrealized, currency) : '—'}
                valueClassName={perfToneClass(detail.unrealizedGainsPct ?? unrealized)}
              />
              <AppMetricsRow
                label="Avg. buy price"
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
                label="Current price"
                value={livePrice != null ? formatCryptoMoney(livePrice, currency) : '—'}
              />
              <AppMetricsRow
                label="Realized P&L"
                value={realized != null ? formatCryptoMoney(realized, currency) : '—'}
                valueClassName={perfToneClass(realized)}
              />
              <AppMetricsRow
                label="Total P&L"
                value={totalGain != null ? formatCryptoMoney(totalGain, currency) : '—'}
                valueClassName={perfToneClass(detail.totalGainsPct ?? totalGain)}
              />
            </AppMetricsList>
          </section>
        </PortalReveal>

        <PortalReveal index={3}>
          <section className="flex w-full flex-col gap-3">
            <AppSectionHeader
              title="Transaction history"
              moreHref={
                hasMoreTransactions ? portalCryptoWalletTransactionsRoute(ticker) : undefined
              }
              moreLabel="All transactions"
            />
            <PortalTransactionHistory
              title=""
              seamless
              items={previewTransactions.map((tx) =>
                mapCryptoTransactionToHistoryItem(tx, currency),
              )}
            />
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
