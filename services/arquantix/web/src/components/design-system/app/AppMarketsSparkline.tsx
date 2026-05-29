'use client'

import { useMemo } from 'react'

import {
  MARKETS_SPARKLINE_HOURLY_POINTS,
  resolveMarketsSparklineValues,
} from '@/lib/portal/marketsSparkline'

type Props = {
  ticker: string
  changePct: number
  /** Série horaire (24 closes) — source API `sparkline_24h` downsampled. */
  sparkline24h?: number[]
  positive?: boolean
  width?: number
  height?: number
}

/** Mini line chart marchés — `.mk-row__spark` (Top crypto · All crypto). */
export function AppMarketsSparkline({
  ticker,
  changePct,
  sparkline24h,
  positive,
  width = 80,
  height = 32,
}: Props) {
  const values = useMemo(
    () => resolveMarketsSparklineValues({ sparkline24h, ticker, changePct }),
    [changePct, sparkline24h, ticker],
  )
  const isPositive = positive ?? changePct >= 0
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const pointCount = values.length
  const points = values
    .map((value, index) => {
      const x = (index / (pointCount - 1)) * width
      const y = height - ((value - min) / range) * (height - 2) - 1
      return `${x},${y}`
    })
    .join(' ')

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden
      data-sparkline-points={MARKETS_SPARKLINE_HOURLY_POINTS}
    >
      <polyline
        fill="none"
        stroke={isPositive ? 'var(--v-green)' : 'var(--v-error)'}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
    </svg>
  )
}
