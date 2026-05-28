'use client'

import {
  AppBalanceCardProduct,
  type AppBalanceCardProductAction,
} from '@/components/design-system/app/AppBalanceCardProduct'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { portalBorrowRoute, PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { normalizeLombardCollateralSymbol } from '@/lib/portal/lombard/lombardWalletAsset'
import { cn } from '@/lib/utils'

type Props = {
  ticker: string
  title: string
  balanceLabel: string
  holdingsPhrase?: string
  buyHref?: string
  sellHref?: string
  balancePending?: boolean
  avatarSymbol: string
  avatarLogoUrl?: string | null
  className?: string
}

/** En-tête détail position crypto — Webapp4 + handoff Position.html (kind crypto). */
export function PortalCryptoWalletDetailHeader({
  ticker,
  title,
  balanceLabel,
  holdingsPhrase,
  buyHref,
  sellHref,
  balancePending = false,
  avatarSymbol,
  avatarLogoUrl,
  className,
}: Props) {
  const lombardCollateral = normalizeLombardCollateralSymbol(ticker)
  const borrowHref = lombardCollateral
    ? portalBorrowRoute({ collateral: lombardCollateral })
    : portalBorrowRoute()

  const actions: AppBalanceCardProductAction[] = [
    {
      id: 'buy',
      label: 'Acheter',
      icon: 'arrow-down',
      href: buyHref,
      disabled: !buyHref,
      variant: 'primary',
    },
    {
      id: 'sell',
      label: 'Vendre',
      icon: 'arrow-up',
      href: sellHref,
      disabled: !sellHref,
      variant: 'secondary',
    },
    {
      id: 'borrow',
      label: 'Emprunter',
      icon: 'trending-up',
      href: borrowHref,
      variant: 'secondary',
    },
  ]

  return (
    <section className={cn('flex flex-col gap-4 pb-2 pt-5', className)}>
      <div className="flex items-center gap-4">
        <PortalCryptoAvatar
          ticker={ticker}
          symbol={avatarSymbol}
          apiLogoUrl={avatarLogoUrl}
          size="lg"
        />
        <div className="min-w-0">
          <p className="v-eyebrow m-0">{ticker}</p>
          {holdingsPhrase ? (
            <p className="m-0 mt-1 font-ui text-[14px] text-v-fg-muted">{holdingsPhrase}</p>
          ) : null}
        </div>
      </div>

      <AppBalanceCardProduct
        balanceLabel={balanceLabel}
        balanceLabelText={title}
        balancePending={balancePending}
        showRevenuePhrase={false}
        actions={actions}
        className="m-0"
      />
    </section>
  )
}
