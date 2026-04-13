'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { PortfolioBar, InstrumentSeries } from './types'
import { useState } from 'react'

interface BacktestChartProps {
  portfolio: PortfolioBar[]
  instruments: InstrumentSeries[]
  layout?: 'single' | 'multiples'
  strategyType?: string  // Optional: 'CPPI' to show Floor series
  floorRatio?: number  // Optional: floor_ratio for CPPI (default 0.9) to convert floor to base100
  coreYield?: number  // Optional: annual core yield for Core 100% benchmark
  coreDayCount?: number  // Optional: day_count used for core yield compounding (default 252)
}

export function BacktestChart({
  portfolio,
  instruments,
  layout = 'single',
  strategyType,
  floorRatio = 0.9,
  coreYield,
  coreDayCount = 252,
}: BacktestChartProps) {
  const [hiddenSeries, setHiddenSeries] = useState<Set<string>>(new Set())

  const toggleSeries = (key: string) => {
    setHiddenSeries(prev => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  // Check if CPPI and has floor data
  const isCPPI = strategyType === 'CPPI'
  const hasFloorData = isCPPI && portfolio.some(bar => bar.weights_json?._cppi_floor != null)
  
  // Check if CORE_SATELLITE and core yield is provided
  const isCoreSatellite = strategyType === 'CORE_SATELLITE'
  const hasCoreBenchmark = isCoreSatellite && typeof coreYield === 'number'

  // Calculate floor conversion factor (floor is stored as absolute, need base100)
  // floor_base100 = (floor / V0) * 100, where V0 = initial capital
  // At t=0: floor_absolute = floor_ratio * V0, so floor_base100 = floor_ratio * 100
  // We use the first bar to calculate V0 from the relationship:
  // first_floor_absolute = floor_ratio * V0, so V0 = first_floor_absolute / floor_ratio
  // Therefore: floor_base100 = (floor / V0) * 100 = (floor / (first_floor / floor_ratio)) * 100
  // = (floor * floor_ratio / first_floor) * 100
  let floorConversionFactor: number | null = null
  if (hasFloorData && portfolio.length > 0 && floorRatio > 0) {
    const firstBar = portfolio[0]
    const firstFloor = firstBar.weights_json?._cppi_floor
    if (firstFloor != null && firstFloor > 0) {
      // Convert: floor_base100 = (floor * floor_ratio / first_floor) * 100
      // This ensures floor starts at floor_ratio * 100 (e.g., 90 if floor_ratio=0.9)
      floorConversionFactor = (floorRatio * 100) / firstFloor
    }
  }

  // Prepare data: merge portfolio + instruments by date
  let coreBenchmarkValue = 100
  let previousDate: Date | null = null
  const chartData = portfolio.map(bar => {
    const currentDate = new Date(bar.date)
    const dataPoint: any = {
      date: new Date(bar.date).toLocaleDateString('fr-FR', { month: '2-digit', year: 'numeric' }),
      dateFull: bar.date,
      Portfolio: bar.nav_base100,
    }

    instruments.forEach(inst => {
      const instBar = inst.series.find(s => s.date === bar.date)
      if (instBar) {
        dataPoint[inst.symbol] = instBar.base100
      }
    })

    // Add Floor for CPPI (convert to base100)
    if (hasFloorData && bar.weights_json?._cppi_floor != null && floorConversionFactor != null) {
      const floorValue = bar.weights_json._cppi_floor
      // Convert absolute floor to base100: floor_base100 = floor * conversion_factor
      dataPoint['Floor'] = floorValue * floorConversionFactor
    }

    // Add Core 100% benchmark for Core-Satellite
    if (hasCoreBenchmark && coreYield != null) {
      if (previousDate) {
        const deltaMs = currentDate.getTime() - previousDate.getTime()
        const deltaDays = Math.max(deltaMs / (1000 * 60 * 60 * 24), 0)
        const growthFactor = Math.pow(1 + coreYield, deltaDays / coreDayCount)
        coreBenchmarkValue = coreBenchmarkValue * growthFactor
      }
      dataPoint['Core 100%'] = coreBenchmarkValue
    }

    previousDate = currentDate
    return dataPoint
  })

  const colors = [
    '#3B82F6', // blue
    '#10B981', // green
    '#F59E0B', // amber
    '#EF4444', // red
    '#8B5CF6', // purple
    '#EC4899', // pink
    '#06B6D4', // cyan
    '#84CC16', // lime
  ]

  if (layout === 'multiples') {
    // Split instruments into groups
    const half = Math.ceil(instruments.length / 2)
    const firstHalf = instruments.slice(0, half)
    const secondHalf = instruments.slice(half)

    return (
      <div className="space-y-6">
        {/* Portfolio only */}
        <div>
          <h3 className="text-sm font-medium mb-2">Portfolio NAV</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="Portfolio"
                stroke="#3B82F6"
                strokeWidth={2}
                dot={false}
              />
              {hasFloorData && (
                <Line
                  type="monotone"
                  dataKey="Floor"
                  stroke="#EF4444"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              )}
              {hasCoreBenchmark && (
                <Line
                  type="monotone"
                  dataKey="Core 100%"
                  stroke="#10B981"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  dot={false}
                  hide={hiddenSeries.has('Core 100%')}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* First half instruments */}
        {firstHalf.length > 0 && (
          <div>
            <h3 className="text-sm font-medium mb-2">Instruments (1/{firstHalf.length > 0 ? 2 : 1})</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend onClick={(e) => toggleSeries(e.dataKey as string)} />
                {firstHalf.map((inst, idx) => (
                  <Line
                    key={inst.instrument_id}
                    type="monotone"
                    dataKey={inst.symbol}
                    stroke={colors[idx % colors.length]}
                    strokeWidth={2}
                    dot={false}
                    hide={hiddenSeries.has(inst.symbol)}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Second half instruments */}
        {secondHalf.length > 0 && (
          <div>
            <h3 className="text-sm font-medium mb-2">Instruments (2/2)</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend onClick={(e) => toggleSeries(e.dataKey as string)} />
                {secondHalf.map((inst, idx) => (
                  <Line
                    key={inst.instrument_id}
                    type="monotone"
                    dataKey={inst.symbol}
                    stroke={colors[(idx + firstHalf.length) % colors.length]}
                    strokeWidth={2}
                    dot={false}
                    hide={hiddenSeries.has(inst.symbol)}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    )
  }

  // Single chart layout
  return (
    <ResponsiveContainer width="100%" height={500}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend onClick={(e) => toggleSeries(e.dataKey as string)} />
        <Line
          type="monotone"
          dataKey="Portfolio"
          stroke="#3B82F6"
          strokeWidth={3}
          dot={false}
          hide={hiddenSeries.has('Portfolio')}
        />
        {instruments.map((inst, idx) => (
          <Line
            key={inst.instrument_id}
            type="monotone"
            dataKey={inst.symbol}
            stroke={colors[idx % colors.length]}
            strokeWidth={2}
            dot={false}
            hide={hiddenSeries.has(inst.symbol)}
          />
        ))}
        {hasFloorData && (
          <Line
            type="monotone"
            dataKey="Floor"
            stroke="#EF4444"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
            hide={hiddenSeries.has('Floor')}
          />
        )}
        {hasCoreBenchmark && (
          <Line
            type="monotone"
            dataKey="Core 100%"
            stroke="#10B981"
            strokeWidth={2}
            strokeDasharray="4 4"
            dot={false}
            hide={hiddenSeries.has('Core 100%')}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  )
}
