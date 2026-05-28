'use client'

import { AppTxExchangeAvatar } from '@/components/design-system/app/AppTxExchangeAvatar'
import { AppTxFlowAvatar } from '@/components/design-system/app/AppTxFlowAvatar'
import { AppTxList } from '@/components/design-system/app/AppTxList'
import { AppTxRow, type AppTxAmountTone } from '@/components/design-system/app/AppTxRow'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

export type PortalTransactionHistoryItem = {
  id: string
  title: string
  subtitle?: string
  amount: string
  amountTone?: AppTxAmountTone
  meta?: string
  incoming?: boolean
  variant?: 'flow' | 'swap' | 'borrow'
  flowDirection?: 'in' | 'out'
  fromAsset?: string
  toAsset?: string
  href?: string
}

type Props = {
  title?: string
  action?: ReactNode
  moreHref?: string
  moreLabel?: string
  emptyMessage?: string
  items: PortalTransactionHistoryItem[]
  className?: string
  /** Variant A preview/17 — pas de séparateurs entre lignes. */
  seamless?: boolean
}

function resolveLeading(item: PortalTransactionHistoryItem): ReactNode {
  const fromAsset = item.fromAsset?.trim()
  const toAsset = item.toAsset?.trim()
  if ((item.variant === 'swap' || item.variant === 'borrow' || (fromAsset && toAsset)) && fromAsset && toAsset) {
    return <AppTxExchangeAvatar fromAsset={fromAsset} toAsset={toAsset} />
  }

  const flowDirection =
    item.flowDirection ?? (item.incoming || item.amountTone === 'in' ? 'in' : 'out')
  return <AppTxFlowAvatar direction={flowDirection} />
}

export function PortalTransactionHistoryMoreLink({
  href,
  label = 'All transactions',
  className,
}: {
  href: string
  label?: string
  className?: string
}) {
  return (
    <PortalNavLink
      href={href}
      className={cn('module-head__action inline-flex items-center gap-1 no-underline', className)}
    >
      {label}
      <KalaiIcon name="chevron-right" size={16} className="text-current" aria-hidden />
    </PortalNavLink>
  )
}

export function PortalTransactionHistoryRows({
  items,
  emptyMessage = 'Aucune transaction pour le moment.',
  seamless = false,
}: {
  items: PortalTransactionHistoryItem[]
  emptyMessage?: string
  seamless?: boolean
}) {
  return (
    <AppTxList isEmpty={items.length === 0} emptyMessage={emptyMessage} seamless={seamless}>
      {items.map((tx) => (
        <AppTxRow
          key={tx.id}
          href={tx.href}
          LinkComponent={tx.href ? PortalNavLink : undefined}
          leading={resolveLeading(tx)}
          title={tx.title}
          subtitle={tx.subtitle}
          amount={tx.amount}
          amountTone={tx.amountTone ?? (tx.incoming ? 'in' : 'out')}
          meta={tx.meta}
          showChevron={Boolean(tx.href)}
        />
      ))}
    </AppTxList>
  )
}

/** Historique transactions — pattern DS preview/17-list-transactions (variant A). */
export function PortalTransactionHistory({
  title = 'Transactions history',
  action,
  moreHref,
  moreLabel = 'All transactions',
  emptyMessage = 'Aucune transaction pour le moment.',
  items,
  className,
  seamless = false,
}: Props) {
  const headerAction =
    action ?? (moreHref ? <PortalTransactionHistoryMoreLink href={moreHref} label={moreLabel} /> : null)

  return (
    <section className={cn('flex w-full flex-col gap-3', className)}>
      {title ? (
        <header className="flex items-center justify-between gap-3">
          <h2 className="module-head__title">{title}</h2>
          {headerAction ? <div className="shrink-0">{headerAction}</div> : null}
        </header>
      ) : null}
      <PortalTransactionHistoryRows
        items={items}
        emptyMessage={emptyMessage}
        seamless={seamless}
      />
    </section>
  )
}
