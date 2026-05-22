'use client'

import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import {
  CHART_PERIOD_OPTIONS,
  type ChartPeriodId,
  type InstrumentCandle,
  lineTrendPositive,
} from '@/lib/portal/instrumentDetailFormat'
import { cn } from '@/lib/utils'

type Props = {
  candles: InstrumentCandle[]
  period: ChartPeriodId
  onPeriodChange: (period: ChartPeriodId) => void
  loading?: boolean
  error?: string | null
  onRetry?: () => void
}

export function PortalInstrumentChartModule({
  candles,
  period,
  onPeriodChange,
  loading,
  error,
  onRetry,
}: Props) {
  const closes = candles.map((c) => c.close)
  const positive = lineTrendPositive(candles)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        {CHART_PERIOD_OPTIONS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onPeriodChange(item.id)}
            className={cn(
              'rounded-v-pill border px-3 py-1.5 font-ui text-[12px] font-medium transition-colors duration-v-fast',
              period === item.id
                ? 'border-v-fg bg-white text-v-fg shadow-v-subtle'
                : 'border-transparent bg-v-fg-05 text-v-fg-body hover:bg-v-fg-10',
            )}
          >
            {item.chip}
          </button>
        ))}
      </div>

      <div className="min-h-[220px] rounded-v-card bg-v-card px-2 py-3 sm:px-4">
        {loading && candles.length === 0 ? (
          <div className="flex h-[200px] items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-v-fg-10 border-t-v-fg" />
          </div>
        ) : error && candles.length === 0 ? (
          <div className="flex h-[200px] flex-col items-center justify-center gap-3 text-center">
            <p className="m-0 font-ui text-[14px] text-v-error">{error}</p>
            {onRetry ? (
              <button
                type="button"
                onClick={onRetry}
                className="v-text-link border-0 bg-transparent p-0 font-ui text-[13px]"
              >
                Retry
              </button>
            ) : null}
          </div>
        ) : closes.length >= 2 ? (
          <PortalPerformanceChart
            values={closes}
            height={200}
            tone="light"
            className={positive ? 'text-v-green' : 'text-v-error'}
          />
        ) : (
          <div className="flex h-[200px] items-center justify-center">
            <p className="m-0 font-ui text-[14px] text-v-fg-muted">No chart data for this period.</p>
          </div>
        )}
      </div>

      <p className="m-0 font-ui text-[11px] leading-relaxed text-v-fg-muted">
        Mid-rate indicative price in USD (USDT). Past performance is not indicative of future results.
      </p>
    </div>
  )
}
