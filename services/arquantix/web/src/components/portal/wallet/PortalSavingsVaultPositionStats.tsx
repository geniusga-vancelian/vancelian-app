'use client'

import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import type { PortalSavingsPositionStat } from '@/lib/portal/portalSavingsFormat'
import { cn } from '@/lib/utils'

type Props = {
  stats: PortalSavingsPositionStat[]
}

/** Grille position coffre — handoff Position.html stats + `pos-stats`. */
export function PortalSavingsVaultPositionStats({ stats }: Props) {
  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title="Ma position" size="sm" />
      <div className="pos-stats">
        {stats.map((row) => (
          <div key={row.key} className="pos-stats__cell">
            <span className="pos-stats__k">{row.label}</span>
            <span
              className={cn(
                'pos-stats__v',
                row.tone === 'accent' && 'is-up',
                row.tone === 'muted' && 'text-v-fg-muted',
              )}
            >
              {row.value}
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}
