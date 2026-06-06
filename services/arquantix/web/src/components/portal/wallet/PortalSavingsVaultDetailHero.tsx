'use client'

import {
  AppCategoryHero,
  type AppCategoryHeroAction,
} from '@/components/design-system/app/AppCategoryHero'
import {
  formatSavingsPositionReferenceMoney,
  resolveSavingsDailyYieldLabel,
  resolveSavingsVaultHeroSubtitle,
} from '@/lib/portal/portalSavingsFormat'
import type { PortalSavingsPosition } from '@/lib/portal/portalSavingsTypes'
import type { PortalLedgityVaultDetails } from '@/lib/portal/ledgity/ledgityVaultTypes'

type Props = {
  vaultName: string
  position: PortalSavingsPosition
  referenceCurrency: string
  apyDisplay: string
  averageApyBps: number | null
  chartValues: number[]
  depositHref: string
  withdrawHref: string
  vault?: PortalLedgityVaultDetails | null
  balancePending?: boolean
}

/** Hero position coffre — handoff Position.html kind=coffre (`.bal.bal--dark.bal--cat`). */
export function PortalSavingsVaultDetailHero({
  vaultName,
  position,
  referenceCurrency,
  apyDisplay,
  averageApyBps,
  chartValues,
  depositHref,
  withdrawHref,
  vault,
  balancePending = false,
}: Props) {
  const actions: AppCategoryHeroAction[] = [
    {
      id: 'deposit',
      label: 'Verser',
      icon: 'arrow-up',
      href: depositHref,
      variant: 'primary',
    },
    {
      id: 'withdraw',
      label: 'Retirer',
      icon: 'arrow-down',
      href: withdrawHref,
      variant: 'secondary',
    },
  ]

  const dailyLabel = resolveSavingsDailyYieldLabel({
    position,
    apyBps: averageApyBps,
    referenceCurrency,
  })

  const subtitle = resolveSavingsVaultHeroSubtitle({
    assetSymbol: position.assetSymbol,
    apyDisplay,
    withdrawMode: vault?.withdrawMode ?? null,
  })

  const earnedPositive =
    position.yieldSyncStatus !== 'pending' &&
    !position.earnedYieldDisplay.startsWith('0 ') &&
    position.earnedYieldDisplay !== '—' &&
    !position.earnedYieldDisplay.includes('synchronisation')

  return (
    <div className="flex flex-col gap-3">
      <AppCategoryHero
        categoryTitle={vaultName}
        label={vaultName}
        balanceLabel={formatSavingsPositionReferenceMoney(position, referenceCurrency)}
        balancePending={balancePending}
        changeAmountLabel={
          earnedPositive ? `+ ${position.earnedYieldDisplay}` : undefined
        }
        changePositive
        chartValues={chartValues}
        accent="var(--v-green)"
        actions={actions}
      />
      <p className="m-0 px-1 font-ui text-[13px] text-v-fg-muted">{subtitle}</p>
      {dailyLabel ? (
        <p className="m-0 px-1 font-editorial text-[17px] font-light leading-snug tracking-tight text-v-fg-body">
          Vous recevez{' '}
          <span className="font-ui font-medium tabular-nums text-v-fg">{dailyLabel}</span> chaque jour
          sur cette position.
        </p>
      ) : null}
    </div>
  )
}
