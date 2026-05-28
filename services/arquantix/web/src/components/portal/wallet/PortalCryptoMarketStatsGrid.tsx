'use client'

import { cn } from '@/lib/utils'

export type PortalCryptoMarketStat = {
  key: string
  value: string
  tone?: 'up' | 'down'
}

type Props = {
  stats: PortalCryptoMarketStat[]
  className?: string
}

/** Grille marché — handoff Position.html `.pos-stats` (kind crypto). */
export function PortalCryptoMarketStatsGrid({ stats, className }: Props) {
  if (stats.length === 0) return null

  return (
    <div className={cn('pos-stats', className)}>
      {stats.map((stat) => (
        <div key={stat.key} className="pos-stats__cell">
          <span className="pos-stats__k">{stat.key}</span>
          <span
            className={cn(
              'pos-stats__v',
              stat.tone === 'up' && 'is-up',
              stat.tone === 'down' && 'is-down',
            )}
          >
            {stat.value}
          </span>
        </div>
      ))}
    </div>
  )
}
