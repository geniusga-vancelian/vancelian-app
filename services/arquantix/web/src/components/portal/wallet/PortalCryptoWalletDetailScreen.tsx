'use client'

import { useMemo } from 'react'
import {
  SupportAsidePanel,
  hasSupportAsideContent,
} from '@/components/design-system/SupportAsidePanel'
import { AppMetricsList } from '@/components/design-system/app/AppMetricsList'
import { AppMetricsRow } from '@/components/design-system/app/AppMetricsRow'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalLombardWalletAssetCta } from '@/components/portal/lombard/PortalLombardWalletAssetCta'
import { PortalLombardAssetDetailLoanSection } from '@/components/portal/lombard/PortalLombardAssetDetailLoanSection'
import { PortalTransactionHistory } from '@/components/portal/PortalTransactionHistory'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { usePortalSupportContent } from '@/components/portal/PortalSupportContentProvider'
import {
  PortalCryptoMarketStatsGrid,
  type PortalCryptoMarketStat,
} from '@/components/portal/wallet/PortalCryptoMarketStatsGrid'
import { PortalCryptoWalletDetailHeader } from '@/components/portal/wallet/PortalCryptoWalletDetailHeader'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import type { PortalChain } from '@/config/portalChains'
import {
  assetToMarketProviderSymbol,
  cryptoPositionHeaderTitle,
} from '@/lib/portal/instrumentDetailFormat'
import { formatCryptoPrice, formatChangePctIndicator } from '@/lib/portal/marketsFormat'
import { mapCryptoTransactionToHistoryItem } from '@/lib/portal/cryptoTransactionHistoryFormat'
import {
  formatCryptoMoney,
  formatPerfPct,
  perfToneClass,
  selectMoneyValue,
} from '@/lib/portal/cryptoWalletFormat'
import {
  CRYPTO_WALLET_DETAIL_TRANSACTIONS_PREVIEW,
  type PortalCryptoWalletDetailPayload,
} from '@/lib/portal/cryptoWalletTypes'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { normalizeLombardCollateralSymbol } from '@/lib/portal/lombard/lombardWalletAsset'
import { portalBorrowRoute, PORTAL_ROUTES, portalCryptoWalletTransactionsRoute, portalSwapBuyRoute, portalSwapSellRoute } from '@/lib/portal/portalRouting'
import { isPortalSwapTradeAsset } from '@/lib/portal/swapFlowTypes'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
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

function buildHoldingsPhrase(
  volume: string,
  ticker: string,
  totalGainsPct?: number,
): string {
  const perf = formatPerfPct(totalGainsPct)
  if (perf) return `${volume} ${ticker} détenus · ${perf} sur 1 an`
  return `${volume} ${ticker} détenus`
}

function buildMarketStats(args: {
  ticker: string
  currency: string
  livePrice?: number
  change24hPct?: number
  totalValue: number
  volume: string
}): PortalCryptoMarketStat[] {
  const { ticker, currency, livePrice, change24hPct, totalValue, volume } = args
  const changeLabel = formatChangePctIndicator(change24hPct ?? 0)
  const changeTone =
    change24hPct == null || change24hPct >= -0.005
      ? change24hPct != null && change24hPct > 0.005
        ? 'up'
        : undefined
      : 'down'

  return [
    {
      key: `Cours ${ticker}`,
      value:
        livePrice != null
          ? formatCryptoPrice(livePrice, currency === 'USD' ? 'USD' : 'EUR')
          : '—',
    },
    {
      key: 'Valorisation',
      value: formatCryptoMoney(totalValue, currency),
    },
    {
      key: 'Volume détenu',
      value: `${volume} ${ticker}`,
    },
    {
      key: 'Variation 24 h',
      value: changeLabel,
      tone: changeTone,
    },
  ]
}

export function PortalCryptoWalletDetailScreen({ asset }: Props) {
  const ticker = asset.trim().toUpperCase()
  const { chain } = usePortalChainContext()
  const cmsSupport = usePortalSupportContent()
  const showSupportAside = hasSupportAsideContent(cmsSupport)

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
  const buyHref = canTrade && swapChainKey ? portalSwapBuyRoute(ticker, swapChainKey) : undefined
  const sellHref = canTrade && swapChainKey ? portalSwapSellRoute(ticker, swapChainKey) : undefined
  const lombardCollateral = normalizeLombardCollateralSymbol(ticker)

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
  const walletBalance = Number.parseFloat(String(detail.volume).replace(',', '.')) || 0
  const assetTitle = cryptoPositionHeaderTitle(ticker, detail.name)
  const marketStats = buildMarketStats({
    ticker,
    currency,
    livePrice,
    change24hPct: changePct,
    totalValue,
    volume: detail.volume,
  })

  return (
    <PortalPageContainer>
      <PortalPortfolioLayout
        main={
          <>
            <PortalReveal index={0}>
              <PortalDetailBackLink href={PORTAL_ROUTES.cryptoWallet} label="Retour aux cryptos" />
              <PortalCryptoWalletDetailHeader
                ticker={ticker}
                title={assetTitle}
                balanceLabel={formatCryptoMoney(totalValue, currency)}
                holdingsPhrase={buildHoldingsPhrase(
                  detail.volume,
                  ticker,
                  detail.totalGainsPct,
                )}
                buyHref={buyHref}
                sellHref={sellHref}
                balancePending={refreshing}
                avatarSymbol={avatarSymbol}
                avatarLogoUrl={avatarLogoUrl}
                className="pt-0"
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
                <AppSectionHeader title="Marché" size="sm" />
                <PortalCryptoMarketStatsGrid stats={marketStats} />
              </section>
            </PortalReveal>

            <PortalReveal index={4}>
              <section className="flex w-full flex-col gap-3">
                <AppSectionHeader title="Ma position" size="sm" />
                <AppMetricsList variant="plain">
                  {detail.availableVolume && detail.lockedVolume ? (
                    <>
                      <AppMetricsRow label="Available" value={`${detail.availableVolume} ${ticker}`} />
                      <AppMetricsRow
                        label="Locked in Lombard"
                        value={`${detail.lockedVolume} ${ticker}`}
                      />
                    </>
                  ) : null}
                  {detail.lombard?.borrowedUsdcAmount && lombardCollateral ? (
                    <AppMetricsRow
                      label="USDC credit line"
                      value={`${detail.lombard.borrowedUsdcAmount} USDC`}
                    />
                  ) : null}
                  {detail.lombard?.borrowedUsdcAmount && ticker === 'USDC' ? (
                    <AppMetricsRow
                      label="From Lombard borrow"
                      value={`${detail.lombard.borrowedUsdcAmount} USDC`}
                    />
                  ) : null}
                  <AppMetricsRow label="Volume" value={`${detail.volume} ${ticker}`} />
                  <AppMetricsRow
                    label="Total balance"
                    value={formatCryptoMoney(totalValue, currency)}
                  />
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
                            selectMoneyValue(
                              currency,
                              detail.avgBuyPriceEur,
                              detail.avgBuyPriceUsd,
                            )!,
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

            <PortalReveal index={5}>
              <section className="flex w-full flex-col gap-3">
                <AppSectionHeader
                  title="Activité"
                  size="sm"
                  moreHref={
                    hasMoreTransactions ? portalCryptoWalletTransactionsRoute(ticker) : undefined
                  }
                  moreLabel="Toutes les transactions"
                />
                <PortalTransactionHistory
                  title=""
                  seamless
              items={previewTransactions.map((tx) =>
                mapCryptoTransactionToHistoryItem(tx, currency, { assetTicker: ticker }),
              )}
                />
              </section>
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
