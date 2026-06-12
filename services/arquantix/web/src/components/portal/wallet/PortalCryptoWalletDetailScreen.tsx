'use client'

import { useMemo } from 'react'
import {
  SupportAsidePanel,
  hasSupportAsideContent,
} from '@/components/design-system/SupportAsidePanel'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalLombardWalletAssetCta } from '@/components/portal/lombard/PortalLombardWalletAssetCta'
import { PortalLombardAssetDetailLoanSection } from '@/components/portal/lombard/PortalLombardAssetDetailLoanSection'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalAdvisorPortraitCard } from '@/components/portal/PortalAdvisorPortraitCard'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { usePortalSupportContent } from '@/components/portal/PortalSupportContentProvider'
import { PortalCryptoInstrumentLinkCard } from '@/components/portal/wallet/PortalCryptoInstrumentLinkCard'
import {
  PortalCryptoMarketStatsGrid,
} from '@/components/portal/wallet/PortalCryptoMarketStatsGrid'
import { PortalCryptoPositionNewsSection } from '@/components/portal/wallet/PortalCryptoPositionNewsSection'
import { PortalCryptoWalletDetailHeader } from '@/components/portal/wallet/PortalCryptoWalletDetailHeader'
import {
  PortalPositionActivityList,
  PortalPositionActivityListSkeleton,
} from '@/components/portal/wallet/PortalPositionActivityList'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import type { PortalChain } from '@/config/portalChains'
import { cryptoPositionHeaderTitle } from '@/lib/portal/instrumentDetailFormat'
import { mapCryptoTransactionToHistoryItem } from '@/lib/portal/cryptoTransactionHistoryFormat'
import { buildCryptoPositionMarketStats } from '@/lib/portal/cryptoPositionDetailFormat'
import {
  formatCryptoMoney,
  resolveCryptoHubChangeLabels,
  selectMoneyValue,
} from '@/lib/portal/cryptoWalletFormat'
import {
  CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW,
  type PortalCryptoWalletDetailActivityPayload,
  type PortalCryptoWalletDetailCorePayload,
  type PortalCryptoWalletDetailNewsPayload,
} from '@/lib/portal/cryptoWalletTypes'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import {
  PORTAL_ROUTES,
  portalCryptoWalletTransactionsRoute,
  portalSwapBuyRoute,
  portalSwapSellRoute,
} from '@/lib/portal/portalRouting'
import { isPortalSwapTradeAsset } from '@/lib/portal/swapFlowTypes'
import { usePortalProgressiveSections } from '@/lib/portal/usePortalProgressiveSections'
import { cn } from '@/lib/utils'

type Props = {
  asset: string
}

const MIN_TRADE_VALUE_USD = 1

function resolveSwapChainForAsset(asset: string, portalChain: PortalChain): string | undefined {
  if (asset === 'CBBTC' || asset === 'CBETH') return 'base'
  if (portalChain === 'solana') return undefined
  return portalChain
}

type DetailSections = {
  core: PortalCryptoWalletDetailCorePayload
  activity: PortalCryptoWalletDetailActivityPayload
  news: PortalCryptoWalletDetailNewsPayload
}

export function PortalCryptoWalletDetailScreen({ asset }: Props) {
  const ticker = asset.trim().toUpperCase()
  const { chain } = usePortalChainContext()
  const cmsSupport = usePortalSupportContent()
  const showSupportAside = hasSupportAsideContent(cmsSupport)

  const encoded = encodeURIComponent(ticker)
  const { sections, refreshing, refresh } = usePortalProgressiveSections<DetailSections>({
    core: {
      cacheKey: `portal:crypto-wallet:${ticker}:core`,
      url: `/api/portal/crypto-wallet/${encoded}/core`,
      ttlMs: 45_000,
      scopeAware: true,
      errorMessage: 'Unable to load position details.',
    },
    activity: {
      cacheKey: `portal:crypto-wallet:${ticker}:activity`,
      url: `/api/portal/crypto-wallet/${encoded}/activity`,
      ttlMs: 45_000,
      scopeAware: true,
    },
    news: {
      cacheKey: `portal:crypto-wallet:${ticker}:news`,
      url: `/api/portal/crypto-wallet/${encoded}/news`,
      ttlMs: 300_000,
    },
  })

  const core = sections.core
  const activity = sections.activity
  const newsSection = sections.news

  const data = core.data
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

  const canTrade = valueUsd > MIN_TRADE_VALUE_USD && isPortalSwapTradeAsset(ticker)
  const swapChainKey = resolveSwapChainForAsset(ticker, chain)
  const buyHref = canTrade && swapChainKey ? portalSwapBuyRoute(ticker, swapChainKey) : undefined
  const sellHref = canTrade && swapChainKey ? portalSwapSellRoute(ticker, swapChainKey) : undefined

  const performanceLabels = useMemo(() => {
    if (activity.data?.performance) {
      return resolveCryptoHubChangeLabels(activity.data.performance, currency, 'YTD')
    }
    const totalGain =
      detail != null
        ? selectMoneyValue(currency, detail.totalGainEur, detail.totalGainUsd) ?? detail.totalGains
        : undefined
    if (totalGain != null || detail?.totalGainsPct != null) {
      return resolveCryptoHubChangeLabels(
        {
          totalPnl: totalGain ?? 0,
          performancePct: detail?.totalGainsPct ?? 0,
        },
        currency,
        'YTD',
      )
    }
    return { positive: true }
  }, [activity.data?.performance, currency, detail])

  const marketStats = useMemo(() => {
    if (!detail) return []
    const livePrice =
      selectMoneyValue(currency, detail.currentPriceEur, detail.currentPriceUsd) ?? undefined
    return buildCryptoPositionMarketStats({
      ticker,
      currency,
      livePrice,
      change24hPct: data?.change24hPct,
      quote: data?.marketQuote,
    })
  }, [currency, data?.change24hPct, data?.marketQuote, detail, ticker])

  const activityItems = useMemo(() => {
    const txs = activity.data?.transactions ?? []
    return txs
      .slice(0, CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW)
      .map((tx) =>
        mapCryptoTransactionToHistoryItem(tx, currency, {
          assetTicker: ticker,
          projectionContext: 'self_trading',
        }),
      )
  }, [activity.data?.transactions, currency, ticker])

  if (core.loading && !data) {
    return <PortalDashboardSkeleton />
  }

  if (core.error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{core.error}</p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button type="button" onClick={() => void refresh()}>
            Réessayer
          </Button>
          <PortalDetailBackLink href={PORTAL_ROUTES.cryptoWallet} label="Retour au wallet crypto" />
        </div>
      </Container>
    )
  }

  if (!detail || !data) return null

  const activityPending = activity.loading && !activity.data
  const transactions = activity.data?.transactions ?? []
  const hasMoreTransactions = transactions.length > CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW
  const walletBalance = Number.parseFloat(String(detail.volume).replace(',', '.')) || 0
  const assetTitle = cryptoPositionHeaderTitle(ticker, detail.name)
  const news = newsSection.data?.news ?? []

  return (
    <PortalPageContainer>
      <PortalPortfolioLayout
        main={
          <>
            <PortalReveal index={0}>
              <PortalDetailBackLink href={PORTAL_ROUTES.cryptoWallet} label="Back to crypto wallet" />
              <PortalCryptoWalletDetailHeader
                ticker={ticker}
                title={assetTitle}
                balanceLabel={formatCryptoMoney(totalValue, currency)}
                changeAmountLabel={performanceLabels.amountLabel}
                changePercentLabel={performanceLabels.percentLabel}
                changePositive={performanceLabels.positive}
                chartValues={activity.data?.historyPoints ?? []}
                buyHref={buyHref}
                sellHref={sellHref}
                balancePending={refreshing || activityPending}
              />
            </PortalReveal>

            <PortalReveal index={1}>
              <PortalLombardWalletAssetCta asset={ticker} chain={chain} balance={walletBalance} />
            </PortalReveal>

            <PortalReveal index={2}>
              <PortalLombardAssetDetailLoanSection asset={ticker} chain={chain} />
            </PortalReveal>

            <PortalReveal index={3}>
              <section className="flex w-full flex-col gap-3">
                <AppSectionHeader title="Market" size="sm" />
                <PortalCryptoMarketStatsGrid stats={marketStats} />
              </section>
            </PortalReveal>

            <PortalReveal index={4}>
              <section className="flex w-full flex-col gap-3">
                <AppSectionHeader
                  title="Activity"
                  size="sm"
                  count={transactions.length > 0 ? transactions.length : undefined}
                  moreHref={
                    hasMoreTransactions ? portalCryptoWalletTransactionsRoute(ticker) : undefined
                  }
                  moreLabel="All transactions"
                />
                {activityPending ? (
                  <PortalPositionActivityListSkeleton />
                ) : (
                  <PortalPositionActivityList items={activityItems} />
                )}
              </section>
            </PortalReveal>

            {news.length > 0 ? (
              <PortalReveal index={5}>
                <PortalCryptoPositionNewsSection items={news} />
              </PortalReveal>
            ) : null}

            <PortalReveal index={news.length > 0 ? 6 : 5}>
              <PortalCryptoInstrumentLinkCard ticker={ticker} assetName={assetTitle} />
            </PortalReveal>

            <button
              type="button"
              disabled={refreshing}
              onClick={() => void refresh()}
              className={cn(
                'v-text-link w-fit border-0 bg-transparent p-0 font-ui text-[13px] disabled:opacity-50',
              )}
            >
              {refreshing ? 'Refreshing…' : 'Refresh'}
            </button>
          </>
        }
        side={
          <>
            <PortalAdvisorPortraitCard />
            <PortalAdvisorBanner />
            {showSupportAside ? (
              <SupportAsidePanel support={cmsSupport} stickyTopClassName="static" className="static" />
            ) : null}
          </>
        }
      />
    </PortalPageContainer>
  )
}
