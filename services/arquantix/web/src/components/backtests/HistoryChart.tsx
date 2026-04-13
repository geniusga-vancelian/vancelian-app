'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { InstrumentPerformance } from './types'
import { useState } from 'react'

interface HistoryChartProps {
  instruments: InstrumentPerformance[]
  layout?: 'single' | 'multiples'
}

export function HistoryChart({ instruments, layout = 'single' }: HistoryChartProps) {
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

  // Merge all series by date
  const dateMap = new Map<string, Record<string, string | number>>()

  instruments.forEach(inst => {
    inst.series.forEach(point => {
      if (!dateMap.has(point.date)) {
        dateMap.set(point.date, { date: point.date })
      }
      const row = dateMap.get(point.date)!
      row[inst.symbol] = point.value
    })
  })

  const chartData = Array.from(dateMap.values()).sort((a, b) => 
    new Date(a.date).getTime() - new Date(b.date).getTime()
  ).map(item => ({
    ...item,
    date: new Date(item.date).toLocaleDateString('fr-FR', { month: '2-digit', year: 'numeric' }),
  }))

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
    const half = Math.ceil(instruments.length / 2)
    const firstHalf = instruments.slice(0, half)
    const secondHalf = instruments.slice(half)

    return (
      <div className="space-y-6">
        {firstHalf.length > 0 && (
          <div>
            <h3 className="text-sm font-medium mb-2">Instruments (1/2)</h3>
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

  // Single chart
  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend onClick={(e) => toggleSeries(e.dataKey as string)} />
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
      </LineChart>
    </ResponsiveContainer>
  )
}






