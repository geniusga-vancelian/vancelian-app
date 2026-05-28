'use client'

import { useMemo, useRef, useState } from 'react'

import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import {
  CHART_PERIOD_OPTIONS,
  type ChartPeriodId,
  type InstrumentCandle,
  formatChangePct,
  formatCryptoPrice,
  lineTrendPositive,
} from '@/lib/portal/instrumentDetailFormat'
import { cn } from '@/lib/utils'

type ChartMode = 'line' | 'candle'

type Props = {
  candles: InstrumentCandle[]
  period: ChartPeriodId
  onPeriodChange: (period: ChartPeriodId) => void
  loading?: boolean
  error?: string | null
  onRetry?: () => void
  periodPerf: { absUsd: number; pct: number } | null
  priceUsd: number
}

function CandlestickPlot({ candles, positive }: { candles: InstrumentCandle[]; positive: boolean }) {
  const W = 720
  const H = 220
  const P = 24
  const accent = positive ? 'var(--v-green)' : 'var(--v-error)'

  const { slotW, candleW, lo, spanV } = useMemo(() => {
    const lows = candles.map((c) => c.low)
    const highs = candles.map((c) => c.high)
    const vmin = Math.min(...lows)
    const vmax = Math.max(...highs)
    const span = (vmax - vmin) || 1
    const pad = span * 0.12
    const loVal = vmin - pad
    const hiVal = vmax + pad
    const cn = candles.length
    const slot = (W - P * 2) / Math.max(cn, 1)
    return {
      slotW: slot,
      candleW: Math.max(2, Math.min(14, slot * 0.62)),
      lo: loVal,
      spanV: hiVal - loVal,
    }
  }, [candles])

  const y = (value: number) => P + (H - P * 2) * (1 - (value - lo) / spanV)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="ast-chart__svg" aria-hidden>
      {candles.map((candle, index) => {
        const cx = P + (index + 0.5) * slotW
        const up = candle.close >= candle.open
        const color = up ? 'var(--v-green)' : 'var(--v-error)'
        const bodyTop = y(Math.max(candle.open, candle.close))
        const bodyBot = y(Math.min(candle.open, candle.close))
        const bodyH = Math.max(1, bodyBot - bodyTop)
        return (
          <g key={index}>
            <line x1={cx} x2={cx} y1={y(candle.high)} y2={y(candle.low)} stroke={color} strokeWidth="1" />
            <rect
              x={cx - candleW / 2}
              y={bodyTop}
              width={candleW}
              height={bodyH}
              fill={color}
              rx="0.5"
            />
          </g>
        )
      })}
      <circle
        cx={P + (candles.length - 0.5) * slotW}
        cy={y(candles[candles.length - 1]?.close ?? 0)}
        r="4"
        fill={accent}
      />
    </svg>
  )
}

/** Graphique performance — handoff `.ast-chart`. */
export function PortalInstrumentChartModule({
  candles,
  period,
  onPeriodChange,
  loading,
  error,
  onRetry,
  periodPerf,
  priceUsd,
}: Props) {
  const [mode, setMode] = useState<ChartMode>('line')
  const plotRef = useRef<HTMLDivElement>(null)

  const closes = candles.map((c) => c.close)
  const positive = lineTrendPositive(candles)
  const accentClass = positive ? 'text-v-green' : 'text-v-error'

  const deltaPct = periodPerf?.pct ?? 0
  const deltaUp = deltaPct >= 0

  return (
    <section className="ast-chart">
      <header className="ast-chart__head">
        <h2 className="ast-chart__title">Performance</h2>
        {periodPerf ? (
          <span className="ast-chart__delta">
            <span className="ast-chart__delta-lbl">Variation</span>
            <span className={accentClass}>
              {deltaUp ? '+ ' : '− '}
              {Math.abs(deltaPct).toFixed(2).replace('.', ',')} %
            </span>
          </span>
        ) : null}
      </header>

      <div className="ast-chart__plot" ref={plotRef}>
        {loading && candles.length === 0 ? (
          <div className="flex h-[240px] items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-v-fg-10 border-t-v-fg" />
          </div>
        ) : error && candles.length === 0 ? (
          <div className="flex h-[240px] flex-col items-center justify-center gap-3 text-center">
            <p className="m-0 font-ui text-[14px] text-v-error">{error}</p>
            {onRetry ? (
              <button
                type="button"
                onClick={onRetry}
                className="v-text-link border-0 bg-transparent p-0 font-ui text-[13px]"
              >
                Réessayer
              </button>
            ) : null}
          </div>
        ) : closes.length >= 2 ? (
          mode === 'line' ? (
            <div className={cn('h-[240px]', accentClass)}>
              <PortalPerformanceChart values={closes} height={240} tone="light" showEndpoint />
            </div>
          ) : (
            <CandlestickPlot candles={candles} positive={positive} />
          )
        ) : (
          <div className="flex h-[240px] items-center justify-center">
            <p className="m-0 font-ui text-[14px] text-v-fg-muted">
              Aucune donnée graphique pour cette plage.
            </p>
          </div>
        )}
      </div>

      <div className="ast-chart__controls">
        <div className="ast-chart__type" role="tablist" aria-label="Type de graphique">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'line'}
            className={cn('ast-chart__type-btn', mode === 'line' && 'is-active')}
            onClick={() => setMode('line')}
          >
            <KalaiIcon name="graph" size={16} />
            Ligne
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'candle'}
            className={cn('ast-chart__type-btn', mode === 'candle' && 'is-active')}
            onClick={() => setMode('candle')}
          >
            <KalaiIcon name="bar-chart-2" size={16} />
            Bougies
          </button>
        </div>

        <div className="perf-tabs" role="tablist" aria-label="Plage de temps">
          {CHART_PERIOD_OPTIONS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              className={cn('perf-tabs__tab', period === item.id && 'is-active')}
              aria-selected={period === item.id}
              onClick={() => onPeriodChange(item.id)}
            >
              {item.chip}
            </button>
          ))}
        </div>
      </div>

      {priceUsd > 0 ? (
        <p className="m-0 font-ui text-[11px] leading-relaxed text-v-fg-muted">
          Cours indicatif en {formatCryptoPrice(priceUsd, 'USD')} (USDT). Les performances passées ne
          préjugent pas des performances futures.
        </p>
      ) : null}
    </section>
  )
}
