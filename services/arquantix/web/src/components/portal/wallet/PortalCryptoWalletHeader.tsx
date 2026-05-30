'use client'

import {
  AppCategoryHero,
  type AppCategoryHeroAction,
} from '@/components/design-system/app/AppCategoryHero'
import { portalBorrowRoute, PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  balanceLabel: string
  changeAmountLabel?: string
  changePercentLabel?: string
  changePositive?: boolean
  chartValues?: number[]
  depositHref: string
  balancePending?: boolean
  className?: string
}

/** Crypto wallet header — handoff Compte.html?id=cryptos (`CategoryHero`). */
export function PortalCryptoWalletHeader({
  balanceLabel,
  changeAmountLabel,
  changePercentLabel,
  changePositive = true,
  chartValues = [],
  depositHref,
  balancePending = false,
  className,
}: Props) {
  const actions: AppCategoryHeroAction[] = [
    {
      id: 'buy',
      label: 'Buy',
      icon: 'arrow-down',
      href: depositHref,
      variant: 'primary',
    },
    {
      id: 'sell',
      label: 'Sell',
      icon: 'arrow-up',
      href: PORTAL_ROUTES.walletSwap,
      variant: 'secondary',
    },
    {
      id: 'borrow',
      label: 'Borrow',
      icon: 'trending-up',
      href: portalBorrowRoute(),
      variant: 'secondary',
    },
  ]

  return (
    <AppCategoryHero
      categoryTitle="Crypto"
      balanceLabel={balanceLabel}
      balancePending={balancePending}
      changeAmountLabel={changeAmountLabel}
      changePercentLabel={changePercentLabel}
      changePositive={changePositive}
      chartValues={chartValues}
      accent="var(--v-fg)"
      actions={actions}
      className={className}
    />
  )
}
