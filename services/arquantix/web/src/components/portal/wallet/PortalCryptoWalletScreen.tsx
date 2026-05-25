'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import {
  ArrowLeft,
  ArrowLeftRight,
  ArrowUpRight,
  BarChart3,
  Plus,
  Wallet,
} from 'lucide-react'
import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalCryptoWalletPositionsCard } from '@/components/portal/wallet/PortalCryptoWalletPositionsCard'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  buildUnifiedWalletRows,
  formatCryptoMoney,
  resolvePrivyHubTotalValue,
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
import {
  isPortalChainSwapEnabled,
  portalChainContextLabel,
} from '@/lib/portal/portalChainFilter'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

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
      errorMessage: 'Impossible de charger les positions crypto.',
      scopeAware: true,
    })

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
    resolvePrivyHubTotalValue(filteredPositions, data.currency),
    data.currency,
  )
  const countLabel =
    filteredPositions.positionsCount > 0
      ? `${filteredPositions.positionsCount} actif${filteredPositions.positionsCount === 1 ? '' : 's'} · ${chainLabel} · ${walletLabel}`
      : isPortalScopeExternal(walletScope)
        ? `Aucun solde Privy · ${walletLabel} (DeFi on-chain)`
        : `Aucun actif · ${chainLabel} · ${walletLabel}`
  const swapEnabled = isPortalChainSwapEnabled(chain)

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <div className="flex flex-col gap-4">
            <PortalNavLink
              href={PORTAL_ROUTES.dashboard}
              className="inline-flex w-fit items-center gap-1.5 font-ui text-[13px] text-v-fg-muted no-underline transition-colors hover:text-v-fg"
            >
              <ArrowLeft className="h-4 w-4" />
              Dashboard
            </PortalNavLink>

            <section className="overflow-hidden rounded-v-card border border-[#0D1B2A]/20 bg-[#0D1B2A] p-4 text-white shadow-v-subtle sm:p-5">
              <VEyebrow className="text-white/70">Wallet</VEyebrow>
              <h1 className="m-0 font-ui text-[22px] font-semibold leading-tight">Crypto</h1>
              <p className="mt-2 mb-0 font-ui text-[28px] font-bold leading-none sm:text-[32px]">
                {totalLabel}
              </p>
              <p className="mt-2 mb-0 font-ui text-[13px] text-white/70">{countLabel}</p>
              <div className="mt-4 border-t border-white/10 pt-4">
                <PortalPerformanceChart
                  values={data.historyPoints}
                  tone="dark"
                  height={88}
                  className="text-white"
                />
              </div>
            </section>

            <div className="flex flex-wrap gap-2">
              {swapEnabled ? (
                <Button type="button" size="sm" className="gap-1.5" asChild>
                  <PortalNavLink href={PORTAL_ROUTES.walletSwap}>
                    <ArrowLeftRight className="h-4 w-4" />
                    Échanger
                  </PortalNavLink>
                </Button>
              ) : (
                <Button
                  type="button"
                  size="sm"
                  className="gap-1.5"
                  variant="outline"
                  disabled
                  title={`Swap disponible sur Ethereum — réseau actuel : ${chainLabel}`}
                >
                  <ArrowLeftRight className="h-4 w-4" />
                  Échanger
                </Button>
              )}
              <Button type="button" variant="outline" size="sm" className="gap-1.5" asChild>
                <PortalNavLink href={resolveChainDepositHref(chain)}>
                  <Plus className="h-4 w-4" />
                  Déposer
                </PortalNavLink>
              </Button>
              <Button type="button" variant="outline" size="sm" className="gap-1.5" disabled>
                <ArrowUpRight className="h-4 w-4" />
                Transférer
              </Button>
              <Button type="button" variant="outline" size="sm" className="gap-1.5" disabled>
                <Wallet className="h-4 w-4" />
                Tout vendre
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                disabled
                title="Statistiques portefeuille — bientôt disponible"
              >
                <BarChart3 className="h-4 w-4" />
                Stats
              </Button>
            </div>
          </div>
        </PortalReveal>

        <PortalReveal index={1}>
          <PortalCryptoWalletPositionsCard
            rows={rows}
            currency={data.currency}
            emptyMessage={
              isPortalScopeExternal(walletScope)
                ? `Les soldes ledger Privy ne s’appliquent pas à ${walletLabel}. Utilisez Invest pour vos positions DeFi on-chain.`
                : `Aucune position sur ${chainLabel} · ${walletLabel}`
            }
          />
        </PortalReveal>

        {data.partial ? (
          <p className="m-0 font-ui text-[12px] text-v-fg-muted">
            Certaines données wallet n&apos;ont pas pu être chargées.
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
