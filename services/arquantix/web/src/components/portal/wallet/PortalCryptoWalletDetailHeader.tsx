'use client'

import {
  AppCategoryHero,
  type AppCategoryHeroAction,
} from '@/components/design-system/app/AppCategoryHero'
import { cryptoBrandColor } from '@/lib/portal/cryptoInstrumentAssets'
import { portalBorrowRoute } from '@/lib/portal/portalRouting'
import { normalizeLombardCollateralSymbol } from '@/lib/portal/lombard/lombardWalletAsset'
import { cn } from '@/lib/utils'

type Props = {
  ticker: string
  title: string
  balanceLabel: string
  changeAmountLabel?: string
  changePercentLabel?: string
  changePositive?: boolean
  chartValues?: number[]
  buyHref?: string
  sellHref?: string
  balancePending?: boolean
  className?: string
}

/** Position hero — handoff Position.html kind=crypto (`.bal.bal--dark.bal--cat`). */
export function PortalCryptoWalletDetailHeader({
  ticker,
  title,
  balanceLabel,
  changeAmountLabel,
  changePercentLabel,
  changePositive = true,
  chartValues = [],
  buyHref,
  sellHref,
  balancePending = false,
  className,
}: Props) {
  const lombardCollateral = normalizeLombardCollateralSymbol(ticker)
  const borrowHref = lombardCollateral
    ? portalBorrowRoute({ collateral: lombardCollateral })
    : portalBorrowRoute()

  const actions: AppCategoryHeroAction[] = [
    {
      id: 'buy',
      label: 'Buy',
      icon: 'arrow-down',
      href: buyHref,
      disabled: !buyHref,
      variant: 'primary',
    },
    {
      id: 'sell',
      label: 'Sell',
      icon: 'arrow-up',
      href: sellHref,
      disabled: !sellHref,
      variant: 'secondary',
    },
    {
      id: 'borrow',
      label: 'Borrow',
      icon: 'trending-up',
      href: borrowHref,
      variant: 'secondary',
    },
  ]

  return (
    <AppCategoryHero
      categoryTitle={ticker}
      label={title}
      balanceLabel={balanceLabel}
      balancePending={balancePending}
      changeAmountLabel={changeAmountLabel}
      changePercentLabel={changePercentLabel}
      changePositive={changePositive}
      chartValues={chartValues}
      accent={cryptoBrandColor(ticker)}
      actions={actions}
      className={cn('pt-0', className)}
    />
  )
}
