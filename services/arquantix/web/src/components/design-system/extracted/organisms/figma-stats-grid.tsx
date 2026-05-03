import { cn } from '@/lib/utils'
import { FigmaStatCard } from '../molecules/figma-stat-card'

export interface FigmaStatItem {
  value: string
  label: string
}

interface FigmaStatsGridProps {
  stats: FigmaStatItem[]
  columns?: 3 | 4 | 6
}

function splitIntoRows(
  stats: FigmaStatItem[],
  columns: 3 | 4 | 6,
): FigmaStatItem[][] {
  if (columns === 6) {
    return stats.length > 0 ? [stats] : []
  }
  if (columns === 4) {
    return [stats.slice(0, 4), stats.slice(4, 8)].filter((r) => r.length > 0)
  }
  return [stats.slice(0, 3), stats.slice(3, 6)].filter((r) => r.length > 0)
}

export function FigmaStatsGrid({ stats, columns = 3 }: FigmaStatsGridProps) {
  const rows = splitIntoRows(stats, columns)

  return (
    <>
      <div
        className={cn(
          /* Pleine largeur du parent (ex. `Container` = même cadre que la navbar) */
          'relative mx-auto hidden w-full min-w-0 shrink-0 flex-col content-stretch items-stretch gap-[24px] self-stretch md:flex',
        )}
      >
        {rows.map((row, rowIndex) => (
          <div
            key={rowIndex}
            className="relative flex min-h-[76px] w-full min-w-0 shrink-0 content-stretch items-stretch"
          >
            {row.map((stat, index) => (
              <FigmaStatCard
                key={`${stat.value}-${index}`}
                value={stat.value}
                label={stat.label}
                showBorder={index > 0}
              />
            ))}
          </div>
        ))}
      </div>

      <div className="relative mx-auto flex w-full flex-col items-stretch md:hidden">
        {stats.map((stat, index) => (
          <div
            key={`${stat.value}-${index}`}
            className={cn('w-full', index > 0 ? 'border-t border-[#f3f3f3]' : '')}
          >
            <FigmaStatCard
              value={stat.value}
              label={stat.label}
              align="center"
            />
          </div>
        ))}
      </div>
    </>
  )
}
