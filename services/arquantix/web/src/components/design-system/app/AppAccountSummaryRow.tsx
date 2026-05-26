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
  indicator?: string
  indicatorTone?: AppAccountIndicatorTone
  showChevron?: boolean
  href?: string
  LinkComponent?: ComponentType<LinkLikeProps>
  className?: string
}

/** Ligne compte — preview/67-card-account. */
export function AppAccountSummaryRow({
  leading,
  title,
  subtitle,
  amount = '',
  amountNode,
  indicator,
  indicatorTone = 'plus',
  showChevron = true,
  href,
  LinkComponent,
  className,
}: Props) {
  const amountEl =
    amountNode ??
    (amount ? <div className="acct-summary__amt">{amount}</div> : null)

  const inner = (
    <>
      {leading}
      <div className="acct-summary__body">
        <div className="acct-summary__title">{title}</div>
        {subtitle ? <div className="acct-summary__sub">{subtitle}</div> : null}
      </div>
      <div className="acct-summary__right">
        {amountEl}
        {indicator ? (
          <span
            className={cn(
              'acct-summary__indic',
              indicatorTone === 'up' && 'acct-summary__indic--up',
              indicatorTone === 'plus' && 'acct-summary__indic--plus',
              indicatorTone === 'dn' && 'acct-summary__indic--dn',
            )}
          >
            {indicatorTone === 'up' ? (
              <KalaiIcon name="arrow-up" size={12} className="shrink-0" />
            ) : null}
            {indicatorTone === 'dn' ? (
              <KalaiIcon name="arrow-down" size={12} className="shrink-0" />
            ) : null}
            <span>{indicator}</span>
          </span>
        ) : null}
      </div>
      {showChevron ? (
        <span className="acct-summary__chv" aria-hidden>
          <KalaiIcon name="chevron-right" size={20} />
        </span>
      ) : null}
    </>
  )

  if (href) {
    const LinkImpl = LinkComponent ?? Link
    return (
      <LinkImpl href={href} className={cn('acct-summary__item no-underline', className)}>
        {inner}
      </LinkImpl>
    )
  }

  return <div className={cn('acct-summary__item', className)}>{inner}</div>
}
