'use client'

import { AppAccountDot } from '@/components/design-system/app/AppAccountDot'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import type { PortalTransactionHistoryItem } from '@/components/portal/PortalTransactionHistory'
import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

type Props = {
  items: PortalTransactionHistoryItem[]
  emptyMessage?: string
  className?: string
}

function resolveDot(item: PortalTransactionHistoryItem): {
  variant: 'green' | 'warm' | 'dark' | 'blue'
  icon: 'arrow-up' | 'arrow-down' | 'exchange' | 'plus' | 'trending-up'
} {
  if (item.variant === 'swap') return { variant: 'dark', icon: 'exchange' }
  if (item.variant === 'borrow') return { variant: 'blue', icon: 'trending-up' }
  if (item.variant === 'allocation') return { variant: 'green', icon: 'plus' }
  if (item.amountTone === 'in' || item.flowDirection === 'in') {
    return { variant: 'green', icon: 'arrow-up' }
  }
  if (item.amountTone === 'out' || item.flowDirection === 'out') {
    return { variant: 'warm', icon: 'arrow-down' }
  }
  return { variant: 'dark', icon: 'exchange' }
}

function amountClass(item: PortalTransactionHistoryItem): string {
  if (!item.amount || item.amount === '—') return 'pos-tx__val pos-tx__val--zero'
  if (item.amountTone === 'in' || item.flowDirection === 'in') return 'pos-tx__val is-up'
  if (item.amountTone === 'out' || item.flowDirection === 'out') return 'pos-tx__val is-down'
  return 'pos-tx__val'
}

function ActivityRow({ item }: { item: PortalTransactionHistoryItem }) {
  const dot = resolveDot(item)
  const showAmount = Boolean(item.amount && item.amount !== '—')

  const inner = (
    <>
      <AppAccountDot size={40} variant={dot.variant} glyph={{ name: dot.icon }} glyphSize={16} />
      <div className="pos-tx__body">
        <span className="pos-tx__label">{item.title}</span>
        {item.subtitle ? <span className="pos-tx__date">{item.subtitle}</span> : null}
      </div>
      <div className="pos-tx__amt">
        {showAmount ? (
          <span className={amountClass(item)}>{item.amount}</span>
        ) : (
          <span className="pos-tx__val pos-tx__val--zero">—</span>
        )}
      </div>
    </>
  )

  if (item.href) {
    return (
      <PortalNavLink href={item.href} className="pos-tx pos-tx--link no-underline">
        {inner}
      </PortalNavLink>
    )
  }

  return <div className="pos-tx">{inner}</div>
}

/** Activity list — handoff Position.html `.pos-list` / `.pos-tx`. */
export function PortalPositionActivityList({
  items,
  emptyMessage = 'No transactions yet.',
  className,
}: Props) {
  if (items.length === 0) {
    return <p className="m-0 font-ui text-[14px] text-v-fg-muted">{emptyMessage}</p>
  }

  return (
    <div className={cn('v-card pos-list', className)}>
      <div className="pos-list__items">
        {items.map((item, index) => (
          <div key={item.id}>
            <ActivityRow item={item} />
            {index < items.length - 1 ? <hr className="pos-list__sep" /> : null}
          </div>
        ))}
      </div>
    </div>
  )
}

export function PortalPositionActivityListSkeleton({ rows = 3 }: { rows?: number }) {
  const placeholders: ReactNode[] = []
  for (let i = 0; i < rows; i += 1) {
    placeholders.push(
      <div key={i} className="pos-tx">
        <span className="portal-shimmer h-10 w-10 shrink-0 rounded-full" aria-hidden />
        <div className="pos-tx__body flex flex-col gap-1.5">
          <span className="portal-shimmer h-4 w-32 rounded-v-input" aria-hidden />
          <span className="portal-shimmer h-3 w-20 rounded-v-input" aria-hidden />
        </div>
        <span className="portal-shimmer h-4 w-16 rounded-v-input" aria-hidden />
      </div>,
    )
  }
  return <div className="v-card pos-list">{placeholders}</div>
}
