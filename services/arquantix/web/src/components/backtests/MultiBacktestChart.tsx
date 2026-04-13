'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { BacktestCompareResponse } from './types'
import { useState } from 'react'

interface MultiBacktestChartProps {
  data: BacktestCompareResponse
}

export function MultiBacktestChart({ data }: MultiBacktestChartProps) {
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

  // Prepare chart data
  const chartData = data.series.map(item => {
    const dataPoint: any = {
      date: new Date(item.date).toLocaleDateString('fr-FR', { month: '2-digit', year: 'numeric' }),
      dateFull: item.date,
    }

    // Add values for each run
    Object.entries(item.values).forEach(([runId, navValue]) => {
      const runMeta = data.runs[runId]
      const seriesKey = runMeta ? `${runMeta.name} (${runId})` : `Run ${runId}`
      dataPoint[seriesKey] = navValue
    })

    return dataPoint
  })

  // Colors for different runs
  const colors = [
    '#3B82F6', // blue
    '#10B981', // green
    '#F59E0B', // amber
    '#EF4444', // red
    '#8B5CF6', // purple
    '#EC4899', // pink
    '#06B6D4', // cyan
    '#84CC16', // lime
    '#F97316', // orange
    '#6366F1', // indigo
  ]

  // Get run IDs and labels
  const runEntries = Object.entries(data.runs).map(([runId, meta]) => ({
    runId,
    label: `${meta.name} (${runId})`,
    color: colors[parseInt(runId) % colors.length],
  }))

  if (chartData.length === 0) {
    return (
      <div className="h-[500px] flex items-center justify-center text-gray-500 text-sm">
        No data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={500}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis label={{ value: 'NAV (base100)', angle: -90, position: 'insideLeft' }} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            fontSize: '12px',
          }}
          labelFormatter={(label) => {
            const point = chartData.find(p => p.date === label)
            return point?.dateFull ? new Date(point.dateFull).toLocaleDateString('fr-FR') : label
          }}
          formatter={(value) =>
            value != null && typeof value === 'number' ? value.toFixed(2) : 'N/A'
          }
        />
        <Legend
          onClick={(e) => toggleSeries(e.dataKey as string)}
          wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
          iconType="line"
        />
        {runEntries.map((run, idx) => (
          <Line
            key={run.runId}
            type="monotone"
            dataKey={run.label}
            stroke={run.color}
            strokeWidth={2}
            dot={false}
            hide={hiddenSeries.has(run.label)}
            connectNulls={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
