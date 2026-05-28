'use client'

import {
  AppBalanceCardProduct,
  type AppBalanceCardProductAction,
} from '@/components/design-system/app/AppBalanceCardProduct'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  balanceLabel: string
  changeAmountLabel?: string
  changePositive?: boolean
  depositHref: string
  balancePending?: boolean
  /** Conservé pour compatibilité appelants — ignoré (Webapp4 n’affiche plus le chart ici). */
  chartValues?: number[]
  className?: string
}

/** En-tête dashboard — Balance Card Webapp4 (home produit). */
export function PortalDashboardHeader({
  balanceLabel,
  changeAmountLabel,
  changePositive = true,
  depositHref,
  balancePending = false,
  className,
}: Props) {
  const actions: AppBalanceCardProductAction[] = [
    {
      id: 'invest',
      label: 'Investir',
      icon: 'arrow-up-right',
      href: PORTAL_ROUTES.invest,
      variant: 'primary',
    },
    {
      id: 'swap',
      label: 'Échanger',
      icon: 'exchange',
      href: PORTAL_ROUTES.walletSwap,
      variant: 'secondary',
    },
    {
      id: 'deposit',
      label: 'Déposer',
      icon: 'arrow-down',
      href: depositHref,
      variant: 'secondary',
    },
    {
      id: 'withdraw',
      label: 'Envoyer',
      icon: 'arrow-up',
      disabled: true,
      variant: 'secondary',
    },
  ]

  return (
    <section className={cn('pb-2 pt-5', className)}>
      <AppBalanceCardProduct
        balanceLabel={balanceLabel}
        balancePending={balancePending}
        revenueAmountLabel={changeAmountLabel}
        revenuePositive={changePositive}
        showRevenuePhrase={Boolean(changeAmountLabel)}
        actions={actions}
      />
    </section>
  )
}
