import type { ReactNode } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

export type AppTxAmountTone = 'in' | 'out' | 'neutral'

type Props = {
  leading: ReactNode
  title: string
  subtitle?: string
  amount: string
  amountTone?: AppTxAmountTone
  meta?: string
  className?: string
  showChevron?: boolean
  href?: string
}

/** Ligne transaction — preview/17-list-transactions. */
export function AppTxRow({
  leading,
  title,
  subtitle,
  amount,
  amountTone = 'neutral',
  meta,
  className,
  showChevron = true,
  href,
}: Props) {
  const inner = (
    <>
      {leading}
      <div className="tx-item__body">
        <div className="tx-item__title">{title}</div>
        {subtitle ? <div className="tx-item__sub">{subtitle}</div> : null}
      </div>
      <div className="tx-item__right">
        <div
          className={cn(
            'tx-item__amt',
            amountTone === 'in' && 'tx-item__amt--in',
            amountTone === 'out' && 'tx-item__amt--out',
          )}
        >
          {amount}
        </div>
        {meta ? <div className="tx-item__meta">{meta}</div> : null}
      </div>
      {showChevron ? (
        <span className="tx-item__chv" aria-hidden>
          <KalaiIcon name="chevron-right" size={20} />
        </span>
      ) : null}
    </>
  )

  if (href) {
    return (
      <Link href={href} className={cn('tx-item no-underline', className)}>
        {inner}
      </Link>
    )
  }

  return <div className={cn('tx-item', className)}>{inner}</div>
}
