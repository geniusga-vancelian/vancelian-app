'use client'

import { useMemo } from 'react'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalPageSidebar } from '@/components/portal/PortalPageSidebar'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalCryptoWalletHeader } from '@/components/portal/wallet/PortalCryptoWalletHeader'
import { PortalCryptoWalletPositionsCard } from '@/components/portal/wallet/PortalCryptoWalletPositionsCard'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  buildUnifiedWalletRows,
  formatCryptoMoney,
  resolveCryptoHubChangeLabels,
  resolveHubTotalValue,
} from '@/lib/portal/cryptoWalletFormat'
import type {
  PortalCryptoWalletHistoryPayload,
  PortalCryptoWalletPositionsPayload,
} from '@/lib/portal/cryptoWalletTypes'
import type { PortalChain } from '@/config/portalChains'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { usePortalWalletScopeContext } from '@/lib/portal/portalWalletScopeContext'
import {
  filterCryptoPositionsSummaryByPortalScope,
  isPortalScopeExternal,
  portalWalletScopeContextLabel,
} from '@/lib/portal/portalWalletScopeFilter'
import { portalChainContextLabel } from '@/lib/portal/portalChainFilter'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { PORTAL_SECTION_CACHE_KEYS } from '@/lib/portal/portalCacheKeys'
import { usePortalProgressiveSections } from '@/lib/portal/usePortalProgressiveSections'
import { cn } from '@/lib/utils'

function resolveChainDepositHref(chain: PortalChain): string {
  if (chain === 'solana') return PORTAL_ROUTES.walletDepositSol
  return PORTAL_ROUTES.walletDeposit
}

const CRYPTO_POSITIONS_FOOTER =
  'Your crypto, your keys. Your assets are secured in a personal non-custodial wallet under your control. Vancelian never stores, controls, or accesses your private keys, ensuring that only you can manage your funds.'

type CryptoWalletSections = {
  positions: PortalCryptoWalletPositionsPayload
  history: PortalCryptoWalletHistoryPayload
}

export function PortalCryptoWalletScreen() {
  const { chain } = usePortalChainContext()
  const { walletScope } = usePortalWalletScopeContext()

  const { sections, refreshing, refresh } = usePortalProgressiveSections<CryptoWalletSections>({
    positions: {
      cacheKey: PORTAL_SECTION_CACHE_KEYS.cryptoWalletPositions,
      url: '/api/portal/crypto-wallet/positions',
      ttlMs: 45_000,
      scopeAware: true,
      errorMessage: 'Unable to load crypto positions.',
    },
    history: {
      cacheKey: PORTAL_SECTION_CACHE_KEYS.cryptoWalletActivity,
      url: '/api/portal/crypto-wallet/history',
      ttlMs: 45_000,
    },
  })

  const positions = sections.positions
  const history = sections.history

  const depositHref = useMemo(() => resolveChainDepositHref(chain), [chain])

  const derived = useMemo(() => {
    const data = positions.data
    if (!data) return null

    const chainLabel = portalChainContextLabel(chain)
    const walletLabel = portalWalletScopeContextLabel(walletScope)
    const filteredPositions = filterCryptoPositionsSummaryByPortalScope(
      data.positions,
      chain,
      walletScope,
    )
    const rows = buildUnifiedWalletRows(filteredPositions.positions, data.bundles, data.currency)
    const totalLabel = formatCryptoMoney(
      resolveHubTotalValue(filteredPositions, data.bundles, data.currency),
      data.currency,
    )
    const performance = resolveCryptoHubChangeLabels(history.data?.performance, data.currency)
    const emptyMessage = isPortalScopeExternal(walletScope)
      ? `Integrated wallet balances do not apply to ${walletLabel}. Use Invest for on-chain DeFi positions.`
      : `No positions on ${chainLabel}`

    return {
      rows,
      totalLabel,
      performance,
      emptyMessage,
    }
  }, [chain, history.data, positions.data, walletScope])

  if (positions.loading && !positions.data) {
    return <PortalDashboardSkeleton />
  }

  if (positions.error && !positions.data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{positions.error}</p>
        <Button type="button" onClick={() => void refresh()}>
          Try again
        </Button>
      </Container>
    )
  }

  const data = positions.data
  if (!data || !derived) return null

  const historyPending = history.loading && !history.data
  const anyPartial = Boolean(data.partial || history.data?.partial)

  return (
    <PortalPageContainer>
      <PortalDetailBackLink href={PORTAL_ROUTES.dashboard} label="Back to portfolio" />

      <PortalPortfolioLayout
        main={
          <>
            <PortalReveal index={0}>
              <PortalCryptoWalletHeader
                balanceLabel={derived.totalLabel}
                balancePending={refreshing || historyPending}
                changeAmountLabel={derived.performance.amountLabel}
                changePercentLabel={derived.performance.percentLabel}
                changePositive={derived.performance.positive}
                chartValues={history.data?.historyPoints ?? []}
                depositHref={depositHref}
              />
            </PortalReveal>

            <PortalReveal index={1}>
              <PortalCryptoWalletPositionsCard
                rows={derived.rows}
                currency={data.currency}
                count={derived.rows.length}
                emptyMessage={derived.emptyMessage}
                footerHint={derived.rows.length > 0 ? CRYPTO_POSITIONS_FOOTER : undefined}
              />
            </PortalReveal>

            {anyPartial ? (
              <p className="m-0 font-ui text-[12px] text-v-fg-muted">
                Some wallet data could not be loaded.
              </p>
            ) : null}

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
        side={<PortalPageSidebar showPortrait showFeatured />}
      />
    </PortalPageContainer>
  )
}
