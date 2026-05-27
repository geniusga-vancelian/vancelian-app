'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { formatLombardPercent } from '@/lib/portal/lombard/lombardFormat'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import { portalLombardPositionRoute } from '@/lib/portal/portalRouting'

type Props = {
  position: LombardActivePosition
}

export function PortalLombardAssetLoanCompactCard({ position }: Props) {
  return (
    <section className="flex flex-col gap-3 rounded-2xl border border-v-border bg-v-surface p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">Locked in Lombard</h2>
          <p className="m-0 mt-1 font-ui text-[14px] text-v-muted">
            {position.collateralAmount} {position.collateralDisplayName} locked as guarantee
          </p>
        </div>
      </div>
      <dl className="m-0 grid gap-2 font-ui text-[14px]">
        <div className="flex justify-between gap-4">
          <dt className="text-v-muted">Credit line drawn</dt>
          <dd className="m-0 font-medium text-v-fg">{position.borrowAmount} USDC</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-v-muted">Safety level</dt>
          <dd className="m-0 font-medium text-v-fg">{position.healthLabel}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-v-muted">Current usage</dt>
          <dd className="m-0 font-medium text-v-fg">{formatLombardPercent(position.currentLtvPercent)}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-v-muted">Interest rate</dt>
          <dd className="m-0 font-medium text-v-fg">{position.borrowApyLabel}</dd>
        </div>
      </dl>
      <PortalNavLink
        href={portalLombardPositionRoute({ marketId: position.marketId })}
        className="font-ui text-[14px] font-medium text-v-accent no-underline hover:underline"
      >
        View loan details
      </PortalNavLink>
    </section>
  )
}
