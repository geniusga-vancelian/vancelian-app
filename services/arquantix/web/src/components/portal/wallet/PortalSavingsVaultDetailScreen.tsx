'use client'

import { useMemo } from 'react'

import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalAdvisorPortraitCard } from '@/components/portal/PortalAdvisorPortraitCard'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import type { PortalTransactionHistoryItem } from '@/components/portal/PortalTransactionHistory'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalSavingsVaultDetailHero } from '@/components/portal/wallet/PortalSavingsVaultDetailHero'
import { PortalSavingsVaultPositionStats } from '@/components/portal/wallet/PortalSavingsVaultPositionStats'
import { PortalSavingsVaultProductLink } from '@/components/portal/wallet/PortalSavingsVaultProductLink'
import { PortalPositionActivityList } from '@/components/portal/wallet/PortalPositionActivityList'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import { resolveCatalogVaultSlugByAddress } from '@/lib/catalog/catalogVaultSlugMap'
import {
  buildSavingsPositionStats,
  formatSavingsApyLabel,
  formatSavingsTransactionAmount,
} from '@/lib/portal/portalSavingsFormat'
import type { PortalLedgityVaultDetails } from '@/lib/portal/ledgity/ledgityVaultTypes'
import type { PortalSavingsVaultDetailPayload } from '@/lib/portal/portalSavingsTypes'
import { PORTAL_ROUTES, resolvePortalDefiVaultFlowRoute } from '@/lib/portal/portalRouting'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { cn } from '@/lib/utils'

type Props = {
  vaultAddress: string
}

function isLedgityVaultDetails(
  vault: PortalSavingsVaultDetailPayload['vault'],
): vault is PortalLedgityVaultDetails {
  return vault.integrationMode === 'ledgity_vault'
}

export function PortalSavingsVaultDetailScreen({ vaultAddress }: Props) {
  const normalizedVault = vaultAddress.trim().toLowerCase()

  const { data, loading, refreshing, error, refresh } =
    usePortalCachedScreen<PortalSavingsVaultDetailPayload>({
      cacheKey: `portal:savings-vault:${normalizedVault}`,
      url: `/api/portal/savings-wallet/${encodeURIComponent(normalizedVault)}`,
      ttlMs: 45_000,
      errorMessage: 'Impossible de charger la position.',
      scopeAware: true,
    })

  const flowRoutes = useMemo(() => {
    if (!data?.vault) return null
    const target = {
      integrationMode: data.integrationMode,
      vaultAddress: data.vault.vaultAddress,
      vaultId: data.vault.id,
    }
    return {
      deposit: resolvePortalDefiVaultFlowRoute(target, 'invest', { returnTo: 'savings' }),
      withdraw: resolvePortalDefiVaultFlowRoute(target, 'withdraw', { returnTo: 'savings' }),
    }
  }, [data?.integrationMode, data?.vault])

  const activityItems = useMemo((): PortalTransactionHistoryItem[] => {
    if (!data?.transactions?.length) return []
    return data.transactions.map((tx) => ({
      id: tx.id,
      title: tx.title,
      subtitle: tx.subtitle,
      amount: formatSavingsTransactionAmount(tx),
      incoming: tx.incoming,
      amountTone: tx.incoming ? 'in' : 'out',
      flowDirection: tx.incoming ? 'in' : 'out',
    }))
  }, [data?.transactions])

  const positionStats = useMemo(() => {
    if (!data?.position) return []
    return buildSavingsPositionStats({
      position: data.position,
      referenceCurrency: data.currency,
      apyDisplay: formatSavingsApyLabel(data.averageApyBps),
    })
  }, [data?.averageApyBps, data?.currency, data?.position])

  const productSlug = useMemo(
    () => resolveCatalogVaultSlugByAddress(normalizedVault),
    [normalizedVault],
  )

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

  if (!data || !data.position || !flowRoutes) return null

  const ledgityVault = isLedgityVaultDetails(data.vault) ? data.vault : null

  return (
    <PortalPageContainer className="pos-page">
      <PortalPortfolioLayout
        main={
          <>
            <PortalReveal index={0}>
              <PortalDetailBackLink href={PORTAL_ROUTES.savingsWallet} label="Épargne" />
              <PortalSavingsVaultDetailHero
                vaultName={data.vaultName}
                position={data.position}
                referenceCurrency={data.currency}
                apyDisplay={data.averageApyDisplay}
                averageApyBps={data.averageApyBps}
                chartValues={data.historyPoints}
                depositHref={flowRoutes.deposit}
                withdrawHref={flowRoutes.withdraw}
                vault={ledgityVault}
                balancePending={refreshing}
              />
            </PortalReveal>

            <PortalReveal index={1}>
              <PortalSavingsVaultPositionStats stats={positionStats} />
            </PortalReveal>

            <PortalReveal index={2}>
              <section className="flex w-full flex-col gap-3">
                <AppSectionHeader
                  title="Activité"
                  size="sm"
                  count={activityItems.length > 0 ? activityItems.length : undefined}
                />
                <PortalPositionActivityList
                  items={activityItems}
                  emptyMessage="Aucune transaction pour le moment."
                />
              </section>
            </PortalReveal>

            {productSlug ? (
              <PortalReveal index={3}>
                <PortalSavingsVaultProductLink slug={productSlug} vaultName={data.vaultName} />
              </PortalReveal>
            ) : null}

            {data.partial ? (
              <p className="m-0 font-ui text-[12px] text-v-fg-muted">
                Certaines données du coffre n&apos;ont pas pu être chargées.
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
              {refreshing ? 'Actualisation…' : 'Actualiser'}
            </button>
          </>
        }
        side={
          <>
            <PortalAdvisorPortraitCard />
            <PortalAdvisorBanner />
          </>
        }
      />
    </PortalPageContainer>
  )
}
