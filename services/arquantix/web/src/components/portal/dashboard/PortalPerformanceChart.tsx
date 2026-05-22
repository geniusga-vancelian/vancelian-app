'use client'

import { cn } from '@/lib/utils'

type Props = {
  values: number[]
  height?: number
  strokeWidth?: number
  tone?: 'light' | 'dark'
  className?: string
}

/** Courbe lissée (Catmull-Rom) — trait `currentColor` selon le fond. */
export function PortalPerformanceChart({
  values,
  height = 80,
  strokeWidth = 2,
  tone = 'light',
  className,
}: Props) {
  const series = values.length >= 2 ? values : [0.2, 0.35, 0.28, 0.42, 0.38, 0.55, 0.5, 0.62, 0.58, 0.72]
  const width = 320
  const innerHeight = height - 16
  const minY = Math.min(...series)
  const maxY = Math.max(...series)
  const range = Math.max(maxY - minY, 0.001)

  const xs: number[] = []
  const ys: number[] = []
  for (let i = 0; i < series.length; i++) {
    xs.push((width * i) / (series.length - 1))
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

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      className={cn(tone === 'dark' ? 'text-v-dark-fg/90' : 'text-v-green', className)}
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
  )
}
