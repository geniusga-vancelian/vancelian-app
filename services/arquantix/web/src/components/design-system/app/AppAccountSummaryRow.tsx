import type { ComponentType, ReactNode } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

export type AppAccountIndicatorTone = 'plus' | 'up' | 'dn'

type LinkLikeProps = {
  href: string
  className?: string
  children: ReactNode
}

type Props = {
  leading: ReactNode
  title: string
  subtitle?: string
  amount?: string
  amountNode?: ReactNode
  dailyLabel?: string
  dailyPositive?: boolean
  /** @deprecated Préférer dailyLabel */
  indicator?: string
  /** @deprecated Préférer dailyPositive */
  indicatorTone?: AppAccountIndicatorTone
  showChevron?: boolean
  pending?: boolean
  ctaLabel?: string
  /** Barre de progression (ex. compte euro en cours d’ouverture). */
  progressPercent?: number
  progressLabel?: ReactNode
  href?: string
  onClick?: () => void
  LinkComponent?: ComponentType<LinkLikeProps>
  className?: string
}

/** Ligne compte — Webapp4 `.acc-row`. */
export function AppAccountSummaryRow({
  leading,
  title,
  subtitle,
  amount = '',
  amountNode,
  dailyLabel,
  dailyPositive = true,
  indicator,
  indicatorTone,
  pending = false,
  ctaLabel,
  progressPercent,
  progressLabel,
  href,
  onClick,
  LinkComponent,
  showChevron = false,
  className,
}: Props) {
  const resolvedDaily =
    dailyLabel ??
    indicator ??
    undefined
  const resolvedPositive =
    dailyLabel != null
      ? dailyPositive
      : indicatorTone === 'dn'
        ? false
        : true

  const amountEl =
    amountNode ??
    (amount ? <span className="v-amount-md">{amount}</span> : null)

  const clampedProgress =
    progressPercent != null
      ? `${Math.max(0, Math.min(100, progressPercent))}%`
      : undefined

  const inner = (
    <>
      {leading}
      <span className="acc-row__body">
        <p className="acc-row__title">{title}</p>
        {subtitle ? <span className="acc-row__sub">{subtitle}</span> : null}
        {clampedProgress ? (
          <span className="acc-row__progress">
            <span className="acc-row__progress-track">
              <span className="acc-row__progress-fill" style={{ width: clampedProgress }} />
            </span>
            {progressLabel ? <span className="acc-row__progress-lbl">{progressLabel}</span> : null}
          </span>
        ) : null}
      </span>
      <span className="acc-row__right">
        {ctaLabel ? (
          <span className="acc-row__cta">
            {ctaLabel}
            <KalaiIcon name="chevron-right" size={16} aria-hidden />
          </span>
        ) : (
          <>
            {amountEl}
            {resolvedDaily ? (
              <span className={cn('acc-row__daily', !resolvedPositive && 'acc-row__daily--neg')}>
                {resolvedDaily}
              </span>
            ) : null}
          </>
        )}
      </span>
      {showChevron && !pending && !ctaLabel ? (
        <KalaiIcon name="chevron-right" size={16} className="shrink-0 text-v-fg-20" aria-hidden />
      ) : null}
    </>
  )

  const rowClass = cn('acc-row', pending && 'acc-row--pending', className)

  if (href) {
    const LinkImpl = LinkComponent ?? Link
    return (
      <LinkImpl href={href} className={cn(rowClass, 'no-underline')}>
        {inner}
      </LinkImpl>
    )
  }

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={rowClass}>
        {inner}
      </button>
    )
  }

  return <div className={rowClass}>{inner}</div>
}
