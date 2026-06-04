'use client'

import { useMemo } from 'react'

import { displayBundleAssetSymbol, formatBundleTargetWeight } from '@/lib/portal/bundleFormat'
import { bundleTargetWeightToPct } from '@/lib/portal/bundleProductFormat'

export type PortalBundleAllocationRow = {
  asset: string
  assetDisplay?: string | null
  targetWeight: string | number | null | undefined
  estimatedAmount?: string | number | null | undefined
  entryAssetLabel?: string | null
}

const SEGMENT_COLORS = [
  '#2775CA',
  '#F7931A',
  '#627EEA',
  '#14B8A6',
  '#A855F7',
  '#E11D48',
  '#0EA5E9',
  '#84CC16',
] as const

const DONUT_R = 42
const DONUT_C = 2 * Math.PI * DONUT_R
const GAP_RATIO = 0.012

type Props = {
  rows: PortalBundleAllocationRow[]
  title?: string
  hint?: string
  className?: string
}

/** Allocation cible bundle — donut + légende (handoff InvestAllocation / portfolio). */
export function PortalBundleTargetAllocation({
  rows,
  title = 'Allocation du panier',
  hint,
  className = '',
}: Props) {
  const items = useMemo(() => {
    return rows
      .map((row, index) => {
        const pct = bundleTargetWeightToPct(row.targetWeight)
        if (pct <= 0) return null
        const name = row.assetDisplay?.trim() || displayBundleAssetSymbol(row.asset)
        return {
          key: `${row.asset}-${index}`,
          name,
          sym: displayBundleAssetSymbol(row.asset),
          pct,
          color: SEGMENT_COLORS[index % SEGMENT_COLORS.length]!,
        }
      })
      .filter((row): row is NonNullable<typeof row> => row != null)
  }, [rows])

  const segs = useMemo(() => {
    const gapLen = DONUT_C * GAP_RATIO
    const sum = items.reduce((s, a) => s + a.pct, 0) || 100
    let acc = 0
    return items.map((a) => {
      const frac = a.pct / sum
      const segLen = Math.max(DONUT_C * frac - gapLen, 0)
      const offset = -acc * DONUT_C
      acc += frac
      return { ...a, frac, segLen, offset }
    })
  }, [items])

  if (items.length === 0) return null

  const hintLabel =
    hint ?? `${items.length} actif${items.length > 1 ? 's' : ''}`

  return (
    <div className={`inv-alloc${className ? ` ${className}` : ''}`}>
      <div className="inv-sim__head">
        <span className="inv-sim__label">{title}</span>
        <span className="inv-sim__hint">{hintLabel}</span>
      </div>
      <div className="inv-alloc__split">
        <div className="inv-alloc__donut" aria-hidden="true">
          <svg viewBox="0 0 100 100" width="100%" height="100%">
            <circle cx="50" cy="50" r={DONUT_R} fill="none" stroke="var(--v-fg-10)" strokeWidth="16" />
            <g transform="rotate(-90 50 50)">
              {segs.map((s) => (
                <circle
                  key={s.key}
                  cx="50"
                  cy="50"
                  r={DONUT_R}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="16"
                  strokeLinecap="butt"
                  strokeDasharray={`${s.segLen} ${DONUT_C - s.segLen}`}
                  strokeDashoffset={s.offset}
                />
              ))}
            </g>
          </svg>
        </div>
        <ul className="inv-alloc__legend">
          {segs.map((a) => (
            <li key={a.key} className="inv-alloc__row">
              <span
                className="inv-alloc__icon"
                aria-hidden="true"
                style={{ background: a.color, color: '#fff', fontSize: 10, fontWeight: 700 }}
              >
                {a.sym.slice(0, 2)}
              </span>
              <span className="inv-alloc__name">
                <b>{a.name}</b>
                <span className="inv-alloc__sub">{a.sym}</span>
              </span>
              <span className="inv-alloc__pct v-tnum">{formatBundleTargetWeight(a.pct)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
