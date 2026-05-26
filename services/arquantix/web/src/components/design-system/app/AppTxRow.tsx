import type { ComponentType, ReactNode } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

export type AppTxAmountTone = 'in' | 'out' | 'neutral'

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
  /** Remplace le montant texte (shimmer, CTA, …). */
  amountNode?: ReactNode
  amountTone?: AppTxAmountTone
  amountClassName?: string
  /** Indicateur sous le montant (preview/67 — perf, APY, …). */
  indicator?: ReactNode
  meta?: string
  className?: string
  showChevron?: boolean
  href?: string
  /** Lien portail (prefetch / warm). Défaut : `next/link`. */
  LinkComponent?: ComponentType<LinkLikeProps>
}

/** Ligne transaction — preview/17-list-transactions. */
export function AppTxRow({
  leading,
  title,
  subtitle,
  amount = '',
  amountNode,
  amountTone = 'neutral',
  amountClassName,
  indicator,
  meta,
  className,
  showChevron = true,
  href,
  LinkComponent,
}: Props) {
  const amountEl =
    amountNode ??
    (amount ? (
      <div
        className={cn(
          'tx-item__amt',
          amountTone === 'in' && 'tx-item__amt--in',
          amountTone === 'out' && 'tx-item__amt--out',
          amountClassName,
        )}
      >
        {amount}
      </div>
    ) : null)

  const inner = (
    <>
      {leading}
      <div className="tx-item__body">
        <div className="tx-item__title">{title}</div>
        {subtitle ? <div className="tx-item__sub">{subtitle}</div> : null}
      </div>
      <div className="tx-item__right">
        {amountEl}
        {indicator}
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
    const LinkImpl = LinkComponent ?? Link
    return (
      <LinkImpl href={href} className={cn('tx-item no-underline', className)}>
        {inner}
      </LinkImpl>
    )
  }

  return <div className={cn('tx-item', className)}>{inner}</div>
}
