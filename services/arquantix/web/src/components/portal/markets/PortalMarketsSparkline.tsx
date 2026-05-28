'use client'

import { useMemo } from 'react'

/** Sparkline synthétique — handoff markets-view.jsx `sparkFor`. */
export function buildMarketsSparklineValues(ticker: string, changePct: number, points = 24): number[] {
  let h = 0
  for (let i = 0; i < ticker.length; i += 1) {
    h = (h * 31 + ticker.charCodeAt(i)) >>> 0
  }

  const rng = () => {
    h = (h * 9301 + 49297) % 233280
    return h / 233280
  }

  const values: number[] = []
  let v = 100
  for (let i = 0; i < points; i += 1) {
    const trend = (changePct / 100) * (i / (points - 1)) * 3
    v += (rng() - 0.5) * 4 + trend
    values.push(v)
  }
  return values
}

type Props = {
  ticker: string
  changePct: number
  positive?: boolean
  width?: number
  height?: number
}

export function PortalMarketsSparkline({
  ticker,
  changePct,
  positive,
  width = 80,
  height = 32,
}: Props) {
  const values = useMemo(
    () => buildMarketsSparklineValues(ticker, changePct),
    [ticker, changePct],
  )
  const isPositive = positive ?? changePct >= 0
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width
      const y = height - ((value - min) / range) * (height - 2) - 1
      return `${x},${y}`
    })
    .join(' ')

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden>
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
