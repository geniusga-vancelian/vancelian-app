'use client'

import { cn } from '@/lib/utils'

type Props = {
  values: number[]
  height?: number
  strokeWidth?: number
  tone?: 'light' | 'dark'
  /** Pastille ronde sur le dernier point (HTML overlay — évite l’étirement SVG). */
  showEndpoint?: boolean
  /** Halo radar lent autour du point (temps réel). */
  endpointLive?: boolean
  className?: string
}

const CHART_WIDTH = 320

function buildChartPath(series: number[], height: number) {
  const innerHeight = height - 16
  const minY = Math.min(...series)
  const maxY = Math.max(...series)
  const range = Math.max(maxY - minY, 0.001)

  const xs: number[] = []
  const ys: number[] = []
  for (let i = 0; i < series.length; i++) {
    xs.push((CHART_WIDTH * i) / (series.length - 1))
    ys.push(innerHeight - ((series[i]! - minY) / range) * innerHeight + 8)
  }

  let d = `M ${xs[0]} ${ys[0]}`
  const tension = 1 / 6
  for (let i = 0; i < series.length - 1; i++) {
    const x0 = xs[i]!
    const y0 = ys[i]!
    const x1 = xs[i + 1]!
    const y1 = ys[i + 1]!
    const xPrev = i > 0 ? xs[i - 1]! : x0
    const yPrev = i > 0 ? ys[i - 1]! : y0
    const xNext = i + 2 < series.length ? xs[i + 2]! : x1
    const yNext = i + 2 < series.length ? ys[i + 2]! : y1
    const c1x = x0 + (x1 - xPrev) * tension
    const c1y = y0 + (y1 - yPrev) * tension
    const c2x = x1 - (xNext - x0) * tension
    const c2y = y1 - (yNext - y0) * tension
    d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${x1} ${y1}`
  }

  const endX = xs[xs.length - 1]!
  const endY = ys[ys.length - 1]!

  return { d, endX, endY }
}

/** Courbe lissée (Catmull-Rom) — trait `currentColor` selon le fond. */
export function PortalPerformanceChart({
  values,
  height = 80,
  strokeWidth = 2,
  tone = 'light',
  showEndpoint = false,
  endpointLive = false,
  className,
}: Props) {
  const series = values.length >= 2 ? values : [0.2, 0.35, 0.28, 0.42, 0.38, 0.55, 0.5, 0.62, 0.58, 0.72]
  const { d, endX, endY } = buildChartPath(series, height)
  const endLeftPct = (endX / CHART_WIDTH) * 100
  const endTopPct = (endY / height) * 100

  return (
    <div className={cn('portal-chart relative h-full w-full', className)} style={{ height }}>
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${height}`}
        width="100%"
        height="100%"
        preserveAspectRatio="none"
        className={cn(
          'block h-full w-full',
          tone === 'dark' ? 'text-v-dark-fg/90' : 'text-v-green',
        )}
        aria-hidden
      >
        <path
          d={d}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      {showEndpoint ? (
        <span
          className={cn(
            'portal-chart__end-wrap',
            endpointLive && 'portal-chart__end-wrap--live',
            tone === 'dark' ? 'portal-chart__end-wrap--dark' : 'portal-chart__end-wrap--light',
          )}
          style={{ left: `${endLeftPct}%`, top: `${endTopPct}%` }}
          aria-hidden
        >
          {endpointLive ? (
            <>
              <span className="portal-chart__end-ring" />
              <span className="portal-chart__end-ring portal-chart__end-ring--delay" />
            </>
          ) : null}
          <span
            className={cn(
              'portal-chart__end',
              tone === 'dark' ? 'portal-chart__end--dark' : 'portal-chart__end--light',
            )}
          />
        </span>
      ) : null}
    </div>
  )
}
