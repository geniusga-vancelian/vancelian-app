'use client'

import {
  AppBalanceCardVariantB,
  type AppBalanceCardFab,
} from '@/components/design-system/app/AppBalanceCardVariantB'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalCryptoWalletPositionsCard } from '@/components/portal/wallet/PortalCryptoWalletPositionsCard'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  buildUnifiedWalletRows,
  formatCryptoMoney,
  resolveHubCountLabel,
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
import { useMemo } from 'react'

function resolveChainDepositHref(chain: PortalChain): string {
  if (chain === 'solana') return PORTAL_ROUTES.walletDepositSol
  return PORTAL_ROUTES.walletDeposit
}

const CACHE_KEY = 'portal:crypto-wallet'

export function PortalCryptoWalletScreen() {
  const { chain } = usePortalChainContext()
  const { walletScope } = usePortalWalletScopeContext()
  const { data, loading, refreshing, error, refresh } =
    usePortalCachedScreen<PortalCryptoWalletHubPayload>({
      cacheKey: CACHE_KEY,
      url: '/api/portal/crypto-wallet',
      ttlMs: 45_000,
      errorMessage: 'Unable to load crypto positions.',
      scopeAware: true,
    })

  const fabs = useMemo<AppBalanceCardFab[]>(
    () => [
      { id: 'swap', label: 'Swap', icon: 'exchange', href: PORTAL_ROUTES.walletSwap },
      { id: 'deposit', label: 'Deposit', icon: 'add', href: resolveChainDepositHref(chain) },
      { id: 'invest', label: 'Invest', icon: 'trending-up', href: PORTAL_ROUTES.invest },
      { id: 'more', label: 'More', icon: 'apps', href: PORTAL_ROUTES.profile },
    ],
    [chain],
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
  const countLabel =
    rows.length > 0
      ? `${resolveHubCountLabel(filteredPositions, data.bundles)} · ${chainLabel}${
          isPortalScopeExternal(walletScope) ? ` · ${walletLabel}` : ''
        }`
      : isPortalScopeExternal(walletScope)
        ? `No balance on ${walletLabel} (on-chain DeFi)`
        : `No assets · ${chainLabel}`

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <AppBalanceCardVariantB
            welcomeHi="Wallet"
            welcomeName="Crypto"
            showAvatar={false}
            showTopActions={false}
            balanceLabel={totalLabel}
            balanceLabelText="Crypto balance"
            metaLabel={countLabel}
            showChange={false}
            chartValues={data.historyPoints}
            showChart
            balancePending={refreshing}
            fabs={fabs}
            className="pt-0"
          />
        </PortalReveal>

        <PortalReveal index={1}>
          <PortalCryptoWalletPositionsCard
            rows={rows}
            currency={data.currency}
            title="Positions"
            emptyMessage={
              isPortalScopeExternal(walletScope)
                ? `Integrated wallet balances do not apply to ${walletLabel}. Use Invest for on-chain DeFi positions.`
                : `No positions on ${chainLabel}`
            }
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
          className="v-text-link w-fit border-0 bg-transparent p-0 font-ui text-[13px] disabled:opacity-50"
        >
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
