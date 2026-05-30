'use client'

import {
  AppBalanceCardPortfolio,
  type AppBalanceCardPortfolioAction,
} from '@/components/design-system/app/AppBalanceCardPortfolio'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  balanceLabel: string
  changeAmountLabel?: string
  changePercentLabel?: string
  changePositive?: boolean
  depositHref: string
  balancePending?: boolean
  chartValues?: number[]
  className?: string
}

/** En-tête dashboard — balance card handoff Portfolio.html (`.bal.bal--light`). */
export function PortalDashboardHeader({
  balanceLabel,
  changeAmountLabel,
  changePercentLabel,
  changePositive = true,
  depositHref,
  balancePending = false,
  chartValues = [],
  className,
}: Props) {
  const actions: AppBalanceCardPortfolioAction[] = [
    {
      id: 'deposit',
      label: 'Deposit',
      icon: 'arrow-up',
      href: depositHref,
      variant: 'primary',
    },
    {
      id: 'withdraw',
      label: 'Withdraw',
      icon: 'arrow-down',
      href: PORTAL_ROUTES.walletWithdraw,
      variant: 'secondary',
    },
    {
      id: 'invest',
      label: 'Invest',
      icon: 'trending-up',
      href: PORTAL_ROUTES.invest,
      variant: 'secondary',
    },
    {
      id: 'borrow',
      label: 'Borrow',
      icon: 'money-dollar',
      href: PORTAL_ROUTES.borrow,
      variant: 'secondary',
    },
  ]

  return (
    <AppBalanceCardPortfolio
      className={className}
      balanceLabel={balanceLabel}
      balancePending={balancePending}
      changeAmountLabel={changeAmountLabel}
      changePercentLabel={changePercentLabel}
      changePositive={changePositive}
      chartValues={chartValues}
      actions={actions}
    />
  )
}
