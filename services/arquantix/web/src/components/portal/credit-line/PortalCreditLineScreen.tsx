'use client'

import { AppBorrowCategoryHero } from '@/components/design-system/app/AppBorrowCategoryHero'
import { AppBorrowExplainerSection } from '@/components/design-system/app/AppBorrowExplainerSection'
import { AppBorrowFaqSection } from '@/components/design-system/app/AppBorrowFaqSection'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalCreditLineLoansSection } from '@/components/portal/credit-line/PortalCreditLineLoansSection'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { Container } from '@/components/ui/Container'
import { resolveCreditLineSummary } from '@/lib/portal/lombard/lombardLoanCardFormat'
import { usePortalLombardPositions } from '@/lib/portal/lombard/usePortalLombardPositions'
import { useLombardV1PortalEnabled } from '@/lib/portal/lombard/useLombardV1PortalEnabled'
import { portalBorrowRoute, PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'

/** Hub Credit Line — handoff `Compte.html?id=emprunts`. */
export function PortalCreditLineScreen() {
  const { deFiEnabled } = usePortalExecutionScope()
  const { enabled: lombardEnabled, loading: featureLoading } = useLombardV1PortalEnabled()
  const { positions, loading, error, refresh } = usePortalLombardPositions()

  const summary = resolveCreditLineSummary(positions)
  const pageLoading = (loading || featureLoading) && positions.length === 0

  if (pageLoading) {
    return <PortalDashboardSkeleton />
  }

  if (error && positions.length === 0) {
    return (
      <PortalPageContainer>
        <PortalDetailBackLink href={PORTAL_ROUTES.dashboard} label="Retour au portefeuille" />
        <Container className="flex min-h-[40vh] flex-col items-start justify-center gap-4 py-10">
          <p className="m-0 font-ui text-[15px] text-v-error">{error}</p>
          <button type="button" className="btn btn--secondary btn--sm" onClick={() => void refresh()}>
            Réessayer
          </button>
        </Container>
      </PortalPageContainer>
    )
  }

  const main = (
    <>
      <PortalReveal index={0}>
        <AppBorrowCategoryHero
          totalBorrowedLabel={summary.totalBorrowedLabel}
          monthlyInterestLabel={summary.monthlyInterestLabel}
          borrowHref={portalBorrowRoute()}
        />
      </PortalReveal>

      <PortalReveal index={1}>
        <PortalCreditLineLoansSection positions={positions} loading={loading && positions.length === 0} />
      </PortalReveal>

      <PortalReveal index={2}>
        <AppBorrowExplainerSection />
      </PortalReveal>

      <PortalReveal index={3}>
        <AppBorrowFaqSection />
      </PortalReveal>
    </>
  )

  return (
    <PortalPageContainer>
      <PortalDetailBackLink href={PORTAL_ROUTES.dashboard} label="Retour au portefeuille" />

      {!deFiEnabled || !lombardEnabled ? (
        <Container className="py-6">
          <p className="m-0 font-ui text-[15px] text-v-fg-muted">
            L&apos;avance de liquidité est disponible sur Base uniquement. Basculez sur Base pour consulter
            vos emprunts Morpho.
          </p>
        </Container>
      ) : (
        <PortalExecutionScopeGate requirement="defi">
          <PortalPortfolioLayout
            main={main}
            side={
              <>
                <PortalAdvisorBanner />
              </>
            }
          />
        </PortalExecutionScopeGate>
      )}
    </PortalPageContainer>
  )
}
