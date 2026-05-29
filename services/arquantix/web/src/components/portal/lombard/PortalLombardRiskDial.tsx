'use client'

import { useCallback, useRef } from 'react'

import type { LombardBorrowZoneStyle } from '@/lib/portal/lombard/lombardBorrowUi'

type Props = {
  ltv: number
  zone: LombardBorrowZoneStyle
  maxLtv?: number
  onLtvChange: (ltv: number) => void
  disabled?: boolean
}

const SIZE = 320
const CY = 170
const CX = SIZE / 2
const R = 122
const STROKE = 12

function ltvToAngle(l: number, maxLtv: number): number {
  const span = Math.max(1, maxLtv - 1)
  return 180 - ((l - 1) / span) * 180
}

function angleToLtv(angle: number, maxLtv: number): number {
  const span = Math.max(1, maxLtv - 1)
  return Math.round(1 + (1 - angle / 180) * span)
}

function pointFromAngle(a: number): { x: number; y: number } {
  const rad = (a * Math.PI) / 180
  return { x: CX + R * Math.cos(rad), y: CY - R * Math.sin(rad) }
}

function arcPath(a1: number, a2: number): string {
  const p1 = pointFromAngle(a1)
  const p2 = pointFromAngle(a2)
  return `M ${p1.x.toFixed(2)} ${p1.y.toFixed(2)} A ${R} ${R} 0 0 1 ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`
}

export function PortalLombardRiskDial({
  ltv,
  zone,
  maxLtv = 70,
  onLtvChange,
  disabled = false,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const draggingRef = useRef(false)

  const clampLtv = useCallback(
    (value: number) => Math.min(maxLtv, Math.max(1, Math.round(value))),
    [maxLtv],
  )

  const handleEvent = useCallback(
    (clientX: number, clientY: number) => {
      if (!svgRef.current || disabled) return
      const rect = svgRef.current.getBoundingClientRect()
      const scale = SIZE / rect.width
      const x = (clientX - rect.left) * scale
      const y = (clientY - rect.top) * scale
      const dx = x - CX
      const dy = CY - y
      if (dy < -5) return
      let angle = (Math.atan2(dy, dx) * 180) / Math.PI
      angle = Math.max(0, Math.min(180, angle))
      onLtvChange(clampLtv(angleToLtv(angle, maxLtv)))
    },
    [clampLtv, disabled, maxLtv, onLtvChange],
  )

  const a50 = ltvToAngle(50, maxLtv)
  const a60 = ltvToAngle(60, maxLtv)
  const thumb = pointFromAngle(ltvToAngle(ltv, maxLtv))

  return (
    <div className="brw-dial">
      <svg
        ref={svgRef}
        viewBox={`0 ${CY - R - STROKE} ${SIZE} ${R + STROKE + 40}`}
        className="brw-dial__svg"
        onPointerDown={(e) => {
          if (disabled) return
          e.preventDefault()
          draggingRef.current = true
          svgRef.current?.setPointerCapture?.(e.pointerId)
          handleEvent(e.clientX, e.clientY)
        }}
        onPointerMove={(e) => {
          if (!draggingRef.current || disabled) return
          handleEvent(e.clientX, e.clientY)
        }}
        onPointerUp={(e) => {
          draggingRef.current = false
          svgRef.current?.releasePointerCapture?.(e.pointerId)
        }}
        onPointerCancel={(e) => {
          draggingRef.current = false
          svgRef.current?.releasePointerCapture?.(e.pointerId)
        }}
        role="slider"
        aria-label="Niveau d'emprunt"
        aria-valuemin={1}
        aria-valuemax={maxLtv}
        aria-valuenow={ltv}
        aria-valuetext={`${ltv} pour cent · ${zone.title}`}
        aria-disabled={disabled}
        tabIndex={disabled ? -1 : 0}
        onKeyDown={(e) => {
          if (disabled) return
          if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
            e.preventDefault()
            onLtvChange(clampLtv(ltv - 1))
          }
          if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
            e.preventDefault()
            onLtvChange(clampLtv(ltv + 1))
          }
        }}
      >
        <defs>
          <linearGradient id="portalBrwRiskGrad" gradientUnits="userSpaceOnUse" x1={CX - R} y1={CY} x2={CX + R} y2={CY}>
            <stop offset="0%" style={{ stopColor: 'var(--v-green)' }} />
            <stop offset="62%" style={{ stopColor: 'var(--v-green)' }} />
            <stop offset="82%" style={{ stopColor: 'var(--v-yellow)' }} />
            <stop offset="95%" style={{ stopColor: 'var(--v-error)' }} />
            <stop offset="100%" style={{ stopColor: 'var(--v-error)' }} />
          </linearGradient>
        </defs>
        <path
          d={arcPath(180, 0)}
          className="brw-dial__track"
          stroke="url(#portalBrwRiskGrad)"
          strokeWidth={STROKE}
          strokeLinecap="round"
          fill="none"
        />
        {ltv > 1 ? (
          <path
            d={arcPath(180, ltvToAngle(ltv, maxLtv))}
            className="brw-dial__fill"
            stroke="url(#portalBrwRiskGrad)"
            strokeWidth={STROKE}
            strokeLinecap="round"
            fill="none"
          />
        ) : null}
        <path
          d={arcPath(180, a50)}
          stroke="var(--v-fg-10)"
          strokeWidth={1}
          fill="none"
          opacity={0.35}
        />
        <path
          d={arcPath(a50, a60)}
          stroke="var(--v-fg-10)"
          strokeWidth={1}
          fill="none"
          opacity={0.35}
        />
        <circle cx={thumb.x} cy={thumb.y} r={15} className="brw-dial__thumb-halo" />
        <circle
          cx={thumb.x}
          cy={thumb.y}
          r={10}
          fill="#FFFFFF"
          stroke={zone.color}
          strokeWidth={3}
          className="brw-dial__thumb"
        />
        <circle cx={thumb.x} cy={thumb.y} r={3} fill={zone.color} />
      </svg>
      <div className="brw-dial__center">
        <p className="brw-dial__value" style={{ color: zone.color }}>
          {ltv}
          <span>%</span>
        </p>
        <p className="brw-dial__label" style={{ background: zone.bg, color: zone.color }}>
          {zone.title}
        </p>
      </div>
    </div>
  )
}
