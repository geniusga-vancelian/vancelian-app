'use client'

import { AppTxList } from '@/components/design-system/app/AppTxList'
import { AppTxRow, type AppTxAmountTone } from '@/components/design-system/app/AppTxRow'
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
}

type Props = {
  title?: string
  action?: ReactNode
  emptyMessage?: string
  items: PortalTransactionHistoryItem[]
  className?: string
}

/** Historique transactions — pattern DS preview/17-list-transactions. */
export function PortalTransactionHistory({
  title = 'Transactions history',
  action,
  emptyMessage = 'Aucune transaction pour le moment.',
  items,
  className,
}: Props) {
  return (
    <AppTxList
      title={title}
      action={action}
      isEmpty={items.length === 0}
      emptyMessage={emptyMessage}
      className={className}
    >
      {items.map((tx) => (
        <AppTxRow
          key={tx.id}
          leading={
            <span
              className={cn(
                'avt avt--52 shrink-0 font-ui text-[14px] font-semibold',
                tx.incoming ? 'avt--green' : 'avt--warm',
              )}
            >
              {tx.incoming ? '↓' : '↑'}
            </span>
          }
          title={tx.title}
          subtitle={tx.subtitle}
          amount={tx.amount}
          amountTone={tx.amountTone ?? (tx.incoming ? 'in' : 'out')}
          meta={tx.meta}
        />
      ))}
    </AppTxList>
  )
}
