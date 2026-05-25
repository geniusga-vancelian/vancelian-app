'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { ArrowLeft, ArrowUpRight, Plus, TrendingUp } from 'lucide-react'
import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalSavingsWalletPositionsCard } from '@/components/portal/wallet/PortalSavingsWalletPositionsCard'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  formatSavingsMoney,
  resolveSavingsCountLabel,
  resolveSavingsHubTotalValue,
} from '@/lib/portal/portalSavingsFormat'
import type { PortalSavingsWalletHubPayload } from '@/lib/portal/portalSavingsTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { usePortalWalletScopeContext } from '@/lib/portal/portalWalletScopeContext'
import { isPortalChainDeFiEnabled, portalChainContextLabel } from '@/lib/portal/portalChainFilter'
import { portalWalletScopeContextLabel } from '@/lib/portal/portalWalletScopeFilter'

const CACHE_KEY = 'portal:savings-wallet'

export function PortalSavingsWalletScreen() {
  const { chain } = usePortalChainContext()
  const { walletScope } = usePortalWalletScopeContext()
  const chainLabel = portalChainContextLabel(chain)
  const walletLabel = portalWalletScopeContextLabel(walletScope)
  const deFiEnabled = isPortalChainDeFiEnabled(chain)

  const { data, loading, refreshing, error, refresh } =
    usePortalCachedScreen<PortalSavingsWalletHubPayload>({
      cacheKey: CACHE_KEY,
      url: '/api/portal/savings-wallet',
      ttlMs: 45_000,
      errorMessage: 'Impossible de charger vos positions épargne.',
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

  if (!deFiEnabled) {
    return (
      <PortalPageContainer>
        <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-3 py-10 text-center">
          <p className="m-0 font-ui text-[15px] text-v-fg">
            L&apos;épargne DeFi est disponible sur Base uniquement.
          </p>
          <p className="m-0 font-ui text-[14px] text-v-fg-muted">
            Réseau actuel : {chainLabel}. Basculez sur Base dans la navbar.
          </p>
        </Container>
      </PortalPageContainer>
    )
  }

  const positions = data.savings?.positions ?? []
  const totalLabel = formatSavingsMoney(
    resolveSavingsHubTotalValue(data.savings, data.currency),
    data.currency,
  )
  const countLabel = `${resolveSavingsCountLabel(data.savings)} · ${walletLabel}`

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

            <section className="overflow-hidden rounded-v-card border border-[#14532D]/20 bg-[#14532D] p-4 text-white shadow-v-subtle sm:p-5">
              <VEyebrow className="text-white/70">Wallet</VEyebrow>
              <h1 className="m-0 font-ui text-[22px] font-semibold leading-tight">Épargne</h1>
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
              <Button type="button" size="sm" className="gap-1.5" asChild>
                <PortalNavLink href={`${PORTAL_ROUTES.invest}#earn-vaults`}>
                  <Plus className="h-4 w-4" />
                  Déposer
                </PortalNavLink>
              </Button>
              <Button type="button" variant="outline" size="sm" className="gap-1.5" asChild>
                <PortalNavLink href={`${PORTAL_ROUTES.invest}#earn-vaults`}>
                  <ArrowUpRight className="h-4 w-4" />
                  Retirer
                </PortalNavLink>
              </Button>
              <Button type="button" variant="outline" size="sm" className="gap-1.5" asChild>
                <PortalNavLink href={`${PORTAL_ROUTES.invest}#earn-vaults`}>
                  <TrendingUp className="h-4 w-4" />
                  Vaults DeFi
                </PortalNavLink>
              </Button>
            </div>
          </div>
        </PortalReveal>

        <PortalReveal index={1}>
          <PortalSavingsWalletPositionsCard positions={positions} currency={data.currency} />
        </PortalReveal>

        {data.partial ? (
          <p className="m-0 font-ui text-[12px] text-v-fg-muted">
            Certaines données épargne n&apos;ont pas pu être chargées.
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
