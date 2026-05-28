'use client'

import { useMemo } from 'react'
import {
  SupportAsidePanel,
  hasSupportAsideContent,
} from '@/components/design-system/SupportAsidePanel'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { usePortalSupportContent } from '@/components/portal/PortalSupportContentProvider'
import { PortalCryptoWalletHeader } from '@/components/portal/wallet/PortalCryptoWalletHeader'
import { PortalCryptoWalletPositionsCard } from '@/components/portal/wallet/PortalCryptoWalletPositionsCard'
import { PortalLombardActiveLoansCard } from '@/components/portal/lombard/PortalLombardActiveLoansCard'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  buildUnifiedWalletRows,
  formatCryptoMoney,
  resolveHubTotalValue,
} from '@/lib/portal/cryptoWalletFormat'
import type { PortalCryptoWalletHubPayload } from '@/lib/portal/cryptoWalletTypes'
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
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { cn } from '@/lib/utils'

function resolveChainDepositHref(chain: PortalChain): string {
  if (chain === 'solana') return PORTAL_ROUTES.walletDepositSol
  return PORTAL_ROUTES.walletDeposit
}

const CACHE_KEY = 'portal:crypto-wallet'

const CRYPTO_POSITIONS_FOOTER =
  'Exposition crypto via paniers diversifiés ou actifs détenus en direct. Conservation Fireblocks (régulé NYDFS), couverture Aon 100 M $.'

export function PortalCryptoWalletScreen() {
  const { chain } = usePortalChainContext()
  const { walletScope } = usePortalWalletScopeContext()
  const cmsSupport = usePortalSupportContent()
  const showSupportAside = hasSupportAsideContent(cmsSupport)

  const { data, loading, refreshing, error, refresh } =
    usePortalCachedScreen<PortalCryptoWalletHubPayload>({
      cacheKey: CACHE_KEY,
      url: '/api/portal/crypto-wallet',
      ttlMs: 45_000,
      errorMessage: 'Unable to load crypto positions.',
      scopeAware: true,
    })

  const depositHref = useMemo(() => resolveChainDepositHref(chain), [chain])

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
  const positionsTitle =
    rows.length > 0 ? `Mes positions · ${rows.length}` : 'Mes positions'
  const emptyMessage = isPortalScopeExternal(walletScope)
    ? `Integrated wallet balances do not apply to ${walletLabel}. Use Invest for on-chain DeFi positions.`
    : `No positions on ${chainLabel}`

  return (
    <PortalPageContainer>
      <PortalPortfolioLayout
        main={
          <>
            <PortalReveal index={0}>
              <PortalCryptoWalletHeader
                balanceLabel={totalLabel}
                depositHref={depositHref}
                balancePending={refreshing}
                className="pt-0"
              />
            </PortalReveal>

            <PortalReveal index={1}>
              <PortalLombardActiveLoansCard walletPositions={filteredPositions.positions} />
            </PortalReveal>

            <PortalReveal index={2}>
              <PortalCryptoWalletPositionsCard
                rows={rows}
                currency={data.currency}
                title={positionsTitle}
                emptyMessage={emptyMessage}
                footerHint={rows.length > 0 ? CRYPTO_POSITIONS_FOOTER : undefined}
              />
            </PortalReveal>

            {data.partial ? (
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
