'use client'

import {
  AppBalanceCardProduct,
  type AppBalanceCardProductAction,
} from '@/components/design-system/app/AppBalanceCardProduct'
import { portalBorrowRoute, PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  balanceLabel: string
  depositHref: string
  balancePending?: boolean
  className?: string
}

/** En-tête wallet crypto — Balance Card Webapp4 (handoff Cryptos · category-detail). */
export function PortalCryptoWalletHeader({
  balanceLabel,
  depositHref,
  balancePending = false,
  className,
}: Props) {
  const actions: AppBalanceCardProductAction[] = [
    {
      id: 'buy',
      label: 'Acheter',
      icon: 'arrow-down',
      href: depositHref,
      variant: 'primary',
    },
    {
      id: 'sell',
      label: 'Vendre',
      icon: 'arrow-up',
      href: PORTAL_ROUTES.walletSwap,
      variant: 'secondary',
    },
    {
      id: 'borrow',
      label: 'Emprunter',
      icon: 'trending-up',
      href: portalBorrowRoute(),
      variant: 'secondary',
    },
  ]

  return (
    <section className={cn('pb-2 pt-5', className)}>
      <AppBalanceCardProduct
        balanceLabel={balanceLabel}
        balanceLabelText="Cryptos"
        balancePending={balancePending}
        showRevenuePhrase={false}
        actions={actions}
      />
    </section>
  )
}
