'use client'

import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import type { InstrumentStatCell } from '@/lib/portal/instrumentDetailFormat'
import { cn } from '@/lib/utils'

type Props = {
  stats: InstrumentStatCell[]
}

/** Grille statistiques détaillées — handoff `.ast-stats-x`. */
export function PortalInstrumentExtendedStats({ stats }: Props) {
  if (stats.length === 0) return null

  return (
    <section>
      <AppSectionHeader title="Statistiques détaillées" size="md" />
      <div className="ast-stats-x">
        {stats.map((stat) => (
          <div className="ast-stats-x__cell" key={stat.key}>
            <span className="ast-stats-x__k">{stat.key}</span>
            <span className="ast-stats-x__v">{stat.value}</span>
            {stat.sub ? (
              <span
                className={cn(
                  'ast-stats-x__sub',
                  stat.subDir === 1 && 'ast-stats-x__sub--up',
                  stat.subDir === -1 && 'ast-stats-x__sub--down',
                )}
              >
                {stat.sub}
              </span>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  )
}
