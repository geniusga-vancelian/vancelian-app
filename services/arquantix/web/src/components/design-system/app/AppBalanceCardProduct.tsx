'use client'

import { useState } from 'react'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { AppMoneyPhrase } from '@/components/design-system/app/AppMoneyPhrase'
import { cn } from '@/lib/utils'

export type AppBalanceCardProductAction = {
  id: string
  label: string
  icon: string
  href?: string
  disabled?: boolean
  variant?: 'primary' | 'secondary'
  onClick?: () => void
}

type Props = {
  balanceLabel: string
  balanceLabelText?: string
  balancePending?: boolean
  revenueAmountLabel?: string
  revenuePositive?: boolean
  showRevenuePhrase?: boolean
  revenuePrefix?: string
  revenueSuffix?: string
  actions: AppBalanceCardProductAction[]
  className?: string
}

function BalanceAction({ action }: { action: AppBalanceCardProductAction }) {
  const variant = action.variant ?? (action.id === 'invest' ? 'primary' : 'secondary')
  const className = cn(
    'btn',
    variant === 'primary' ? 'btn--primary' : 'btn--secondary',
    action.disabled && 'btn--disabled',
  )
  const inner = (
    <>
      <KalaiIcon name={action.icon} size={16} className={variant === 'primary' ? 'text-white' : ''} />
      {action.label}
    </>
  )

  if (action.href && !action.disabled) {
    return (
      <PortalNavLink href={action.href} className={cn(className, 'no-underline')}>
        {inner}
      </PortalNavLink>
    )
  }

  return (
    <button type="button" className={className} disabled={action.disabled} onClick={action.onClick}>
      {inner}
    </button>
  )
}

/** Balance card home produit — Webapp4 pattern (v-card · v-amount-hero · money-phrase). */
export function AppBalanceCardProduct({
  balanceLabel,
  balanceLabelText = 'Solde total',
  balancePending = false,
  revenueAmountLabel,
  revenuePositive = true,
  showRevenuePhrase = true,
  revenuePrefix,
  revenueSuffix,
  actions,
  className,
}: Props) {
  const [balanceVisible, setBalanceVisible] = useState(true)
  const displayBalance = balanceVisible ? balanceLabel : '••••••'
  const displayRevenue =
    balanceVisible && revenueAmountLabel ? revenueAmountLabel : balanceVisible ? undefined : '••••'

  return (
    <article className={cn('v-card bal-product', className)}>
      <div className="bal-product__head">
        <p className="v-eyebrow m-0">{balanceLabelText}</p>
        <div className="bal-product__tools">
          <button
            type="button"
            className="ic-btn"
            aria-label={balanceVisible ? 'Masquer le solde' : 'Afficher le solde'}
            onClick={() => setBalanceVisible((v) => !v)}
          >
            <KalaiIcon name={balanceVisible ? 'eye' : 'eye-off'} size={16} />
          </button>
          <button type="button" className="ic-btn" aria-label="Vue allocation" disabled>
            <KalaiIcon name="bar-chart-2" size={16} />
          </button>
        </div>
      </div>

      {balancePending ? (
        <span className="portal-shimmer h-14 w-48 rounded-v-input" aria-hidden />
      ) : (
        <p className="v-amount-hero bal-product__amt">{displayBalance}</p>
      )}

      {!balancePending && showRevenuePhrase && displayRevenue ? (
        <AppMoneyPhrase
          prefix={revenuePrefix}
          amount={displayRevenue}
          suffix={revenueSuffix}
          positive={revenuePositive}
        />
      ) : null}

      <div className="bal-product__actions">
        {actions.map((action) => (
          <BalanceAction key={action.id} action={action} />
        ))}
      </div>
    </article>
  )
}
