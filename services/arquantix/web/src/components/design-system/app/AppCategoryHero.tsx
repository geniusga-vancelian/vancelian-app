'use client'

import { useMemo, useState } from 'react'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { cn } from '@/lib/utils'

export type AppCategoryHeroAction = {
  id: string
  label: string
  icon: string
  href?: string
  disabled?: boolean
  variant?: 'primary' | 'secondary'
  onClick?: () => void
}

type Props = {
  categoryTitle: string
  /** When set, replaces the default « {categoryTitle} balance » label (position detail hero). */
  label?: string
  balanceLabel: string
  balancePending?: boolean
  changeAmountLabel?: string
  changePercentLabel?: string
  changePositive?: boolean
  chartValues?: number[]
  accent?: string
  actions: AppCategoryHeroAction[]
  className?: string
}

function BarsIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <rect x="2" y="9" width="2.5" height="5" rx="1" />
      <rect x="6.75" y="5" width="2.5" height="9" rx="1" />
      <rect x="11.5" y="2" width="2.5" height="12" rx="1" />
    </svg>
  )
}

function CategoryAction({ action }: { action: AppCategoryHeroAction }) {
  const variant = action.variant ?? 'secondary'
  const className = cn(
    'btn btn--lg',
    variant === 'primary' ? 'btn--primary' : 'btn--secondary',
    action.disabled && 'btn--disabled',
  )
  const inner = (
    <>
      <KalaiIcon name={action.icon} size={16} className={variant === 'primary' ? 'text-v-fg' : ''} />
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

/** Hero compte catégorie — handoff `CategoryHero` (`.bal.bal--dark.bal--cat`). */
export function AppCategoryHero({
  categoryTitle,
  label,
  balanceLabel,
  balancePending = false,
  changeAmountLabel,
  changePercentLabel,
  changePositive = true,
  chartValues = [],
  accent = 'var(--v-fg)',
  actions,
  className,
}: Props) {
  const [hidden, setHidden] = useState(false)
  const displayLabel = label ?? `${categoryTitle} balance`
  const displayBalance = hidden ? '•\u00a0•\u00a0•\u00a0•\u00a0•\u00a0•' : balanceLabel
  const displayChangeAmount =
    hidden && changeAmountLabel ? '••••' : changeAmountLabel
  const displayChangePercent =
    hidden && changePercentLabel ? undefined : changePercentLabel

  const chartSeries = useMemo(
    () => (chartValues.length >= 2 ? chartValues : []),
    [chartValues],
  )

  return (
    <section
      className={cn('bal bal--dark bal--cat w-full max-w-none', className)}
      style={{ background: accent }}
    >
      <button
        type="button"
        className="bal__toggle"
        disabled
        aria-label="View allocation"
        title="Allocation view — coming soon"
      >
        <BarsIcon size={16} />
      </button>

      <div className="bal__solde">
        <div className="bal__lbl">
          {displayLabel}
          <button
            type="button"
            onClick={() => setHidden((value) => !value)}
            aria-label={hidden ? 'Show amounts' : 'Hide amounts'}
            className="inline-flex items-center justify-center border-0 bg-transparent p-0.5 opacity-70"
          >
            <KalaiIcon name={hidden ? 'eye-off' : 'eye'} size={16} />
          </button>
        </div>

        {balancePending ? (
          <span className="portal-shimmer-dark h-11 w-48 max-w-full rounded-v-input" aria-hidden />
        ) : (
          <div className="bal__amt v-tnum" aria-live="polite">
            {displayBalance}
          </div>
        )}

        {!balancePending && displayChangeAmount ? (
          <div className={cn('bal__chg', !changePositive && 'bal__chg--neg')}>
            <KalaiIcon name={changePositive ? 'arrow-up' : 'arrow-down'} size={16} aria-hidden />
            {displayChangeAmount}
            {displayChangePercent ? (
              <span className="bal__chg-pct">{`\u00a0· ${displayChangePercent}`}</span>
            ) : null}
          </div>
        ) : null}
      </div>

      {!balancePending && chartSeries.length >= 2 ? (
        <div className="bal__chart" aria-hidden="true">
          <PortalPerformanceChart
            values={chartSeries}
            tone="dark"
            height={96}
            strokeWidth={1.5}
            showEndpoint
          />
        </div>
      ) : null}

      <div className="bal__actions">
        {actions.map((action) => (
          <CategoryAction key={action.id} action={action} />
        ))}
      </div>
    </section>
  )
}
