'use client'

import { AppLoanCard } from '@/components/design-system/app/AppLoanCard'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import {
  formatLombardCollateralSubtitle,
  formatLombardUsdcAmountLabel,
  mapLombardHealthToLoanSafety,
  resolveLombardCollateralIconUrl,
  resolveLombardHealthLabelFr,
  resolveLombardLoanAlertPercent,
  resolveLombardUsagePercent,
} from '@/lib/portal/lombard/lombardLoanCardFormat'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import { portalLombardPositionRoute } from '@/lib/portal/portalRouting'

type Props = {
  positions: LombardActivePosition[]
  loading?: boolean
}

function LombardLoanCard({ position }: { position: LombardActivePosition }) {
  const usagePercent = resolveLombardUsagePercent(position)
  const safety = mapLombardHealthToLoanSafety(position.healthStatus)

  return (
    <AppLoanCard
      assetTitle={`Garantie ${position.collateralDisplayName}`}
      collateralSubtitle={formatLombardCollateralSubtitle(position)}
      collateralIconUrl={resolveLombardCollateralIconUrl(position.collateralSymbol)}
      stats={[
        {
          label: 'Montant emprunté',
          value: formatLombardUsdcAmountLabel(Number(String(position.borrowAmount).replace(',', '.'))),
        },
      ]}
      trailingStats={[
        {
          label: "Taux d'intérêt",
          value: position.borrowApyLabel,
        },
      ]}
      safety={safety}
      safetyLabel={resolveLombardHealthLabelFr(position.healthStatus, position.healthLabel)}
      usagePercent={usagePercent}
      alertAtPercent={resolveLombardLoanAlertPercent()}
      href={portalLombardPositionRoute({
        marketId: position.marketId,
        collateral: position.collateralSymbol,
      })}
      LinkComponent={PortalNavLink}
    />
  )
}

/** Liste emprunts Morpho — handoff `.loan-list` · `Mes emprunts`. */
export function PortalCreditLineLoansSection({ positions, loading = false }: Props) {
  const activeLoans = positions.filter(
    (position) => Number(String(position.borrowAmount).replace(',', '.')) > 0,
  )

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader
        title="Mes emprunts"
        count={loading ? undefined : activeLoans.length}
        size="sm"
      />
      {loading ? (
        <div className="loan-list">
          <div className="portal-shimmer h-48 w-full rounded-v-lg" aria-hidden />
        </div>
      ) : activeLoans.length > 0 ? (
        <div className="loan-list">
          {activeLoans.map((position) => (
            <LombardLoanCard key={position.marketId} position={position} />
          ))}
        </div>
      ) : (
        <p className="m-0 font-ui text-[14px] text-v-fg-muted">
          Aucun emprunt actif pour le moment. Empruntez des USDC en gardant vos cryptos en garantie.
        </p>
      )}
    </section>
  )
}
