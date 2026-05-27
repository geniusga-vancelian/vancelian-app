'use client'

import {
  AppBalanceCardVariantB,
  type AppBalanceCardFab,
} from '@/components/design-system/app/AppBalanceCardVariantB'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  welcomeName: string
  showAvatar?: boolean
  avatarInitials?: string | null
  avatarImageUrl?: string | null
  balanceLabel: string
  changeAmountLabel?: string
  changePercentLabel?: string
  changePositive?: boolean
  chartValues: number[]
  showChart?: boolean
  depositHref: string
  balancePending?: boolean
  className?: string
}

/** En-tête dashboard — Balance Card variante A anthracite (DS preview/19). */
export function PortalDashboardHeader({
  welcomeName,
  showAvatar = true,
  avatarInitials,
  avatarImageUrl,
  balanceLabel,
  changeAmountLabel,
  changePercentLabel,
  changePositive = true,
  chartValues,
  showChart = true,
  depositHref,
  balancePending = false,
  className,
}: Props) {
  const fabs: AppBalanceCardFab[] = [
    { id: 'deposit', label: 'Déposer', icon: 'add', href: depositHref },
    { id: 'withdraw', label: 'Retirer', icon: 'send-1', disabled: true },
    { id: 'swap', label: 'Échanger', icon: 'exchange', href: PORTAL_ROUTES.walletSwap },
    { id: 'invest', label: 'Investir', icon: 'trending-up', href: PORTAL_ROUTES.invest },
  ]

  return (
    <section className={cn('pb-2 pt-5', className)}>
      <AppBalanceCardVariantB
        welcomeName={welcomeName}
        showAvatar={showAvatar}
        avatarInitials={avatarInitials}
        avatarImageUrl={avatarImageUrl}
        balanceLabel={balanceLabel}
        balancePending={balancePending}
        changeAmountLabel={changeAmountLabel}
        changePercentLabel={changePercentLabel}
        changePositive={changePositive}
        chartValues={chartValues}
        showChart={showChart}
        fabs={fabs}
      />
    </section>
  )
}
