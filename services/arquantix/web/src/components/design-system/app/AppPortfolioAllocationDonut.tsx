'use client'

import { cn } from '@/lib/utils'

export type AppPortfolioAllocationSlice = {
  label: string
  percentage: number
  colorHex: string
}

export type AppPortfolioAllocationDonutProps = {
  title: string
  subtitle?: string
  periodLabel?: string
  slices: AppPortfolioAllocationSlice[]
  centerValue?: string
  centerLabel?: string
  className?: string
}

function buildConicGradient(slices: AppPortfolioAllocationSlice[]): string {
  if (!slices.length) return 'conic-gradient(var(--v-fg-10) 0deg 360deg)'
  const total = slices.reduce((sum, s) => sum + Math.max(0, s.percentage), 0) || 100
  let cursor = 0
  const parts = slices.map((slice) => {
    const span = (Math.max(0, slice.percentage) / total) * 100
    const start = cursor
    const end = cursor + span
    cursor = end
    const color = slice.colorHex?.trim() || 'var(--v-fg-muted)'
    return `${color} ${start}% ${end}%`
  })
  return `conic-gradient(${parts.join(', ')})`
}

/** Allocation donut — portfolio split (preview 91). */
export function AppPortfolioAllocationDonut({
  title,
  subtitle,
  periodLabel,
  slices,
  centerValue,
  centerLabel,
  className,
}: AppPortfolioAllocationDonutProps) {
  if (!slices.length && !title.trim()) return null

  const totalPct = slices.reduce((sum, s) => sum + Math.max(0, s.percentage), 0) || 100

  return (
    <div className={cn('alloc', className)}>
      <div className="alloc__head">
        <div className="min-w-0">
          {title ? <div className="alloc__title">{title}</div> : null}
          {subtitle ? <div className="alloc__sub">{subtitle}</div> : null}
        </div>
        {periodLabel ? <span className="alloc__period">{periodLabel}</span> : null}
      </div>

      {slices.length > 0 ? (
        <div className="alloc__body">
          <div className="alloc__donut" aria-hidden={!centerValue && !centerLabel}>
            <div
              className="alloc__donut-ring"
              style={{ background: buildConicGradient(slices) }}
            />
            {centerValue || centerLabel ? (
              <div className="alloc__center">
                {centerValue ? <span className="alloc__center__val">{centerValue}</span> : null}
                {centerLabel ? <span className="alloc__center__lbl">{centerLabel}</span> : null}
              </div>
            ) : null}
          </div>

          <div className="alloc__legend">
            {slices.map((slice, index) => {
              const pct =
                totalPct > 0
                  ? (Math.max(0, slice.percentage) / totalPct) * 100
                  : slice.percentage
              return (
                <div key={`${slice.label}-${index}`} className="alloc__leg-row">
                  <span
                    className="alloc__leg-dot"
                    style={{ background: slice.colorHex?.trim() || 'var(--v-fg-muted)' }}
                  />
                  <span className="alloc__leg-lbl">{slice.label}</span>
                  <span className="alloc__leg-pct">{pct.toFixed(1)}%</span>
                </div>
              )
            })}
          </div>
        </div>
      ) : null}
    </div>
  )
}
