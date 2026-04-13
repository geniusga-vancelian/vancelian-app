'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { PortfolioBar } from './types'

interface CoreSatelliteChartsProps {
  portfolio: PortfolioBar[]
  strategyParams?: any
}

export function CoreSatelliteCharts({ portfolio, strategyParams }: CoreSatelliteChartsProps) {
  // Extract Core-Satellite specific series
  const allocationData = portfolio.map(bar => {
    const weights = bar.weights_json || {}
    const coreWeight = weights._core_weight ?? 0
    const satWeightScalar = weights._cs_sat_weight_scalar ?? 0
    
    return {
      date: new Date(bar.date).toLocaleDateString('fr-FR', { month: '2-digit', year: 'numeric' }),
      dateFull: bar.date,
      'Core Weight (%)': coreWeight * 100,
      'Satellite Weight (%)': satWeightScalar * 100,
    }
  })

  const hasAllocationData = allocationData.some(d => d['Core Weight (%)'] !== 0 || d['Satellite Weight (%)'] !== 0)

  if (!hasAllocationData) {
    return (
      <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded">
        No Core-Satellite allocation data available. Ensure debug mode is enabled.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Core vs Satellite Allocation Chart (Full Width) */}
      <div>
        <h3 className="text-sm font-medium mb-2">Core-Satellite Allocation (Core vs Satellite)</h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={allocationData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis 
              domain={[0, 100]}
              label={{ value: 'Weight (%)', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="Core Weight (%)"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="Satellite Weight (%)"
              stroke="#10B981"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Optional: Realized TE vs Target TE (if available) */}
      {portfolio.some(bar => bar.weights_json?._te_realized != null) && (
        <div>
          <h3 className="text-sm font-medium mb-2">Tracking Error (Realized vs Target)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart
              data={portfolio.map(bar => {
                const weights = bar.weights_json || {}
                const teRealized = weights._te_realized ?? null
                const targetTe = strategyParams?.target_te ?? null
                
                return {
                  date: new Date(bar.date).toLocaleDateString('fr-FR', { month: '2-digit', year: 'numeric' }),
                  dateFull: bar.date,
                  'Realized TE (%)': teRealized ? teRealized * 100 : null,
                  'Target TE (%)': targetTe ? targetTe * 100 : null,
                }
              })}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis
                label={{ value: 'TE (%)', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="Realized TE (%)"
                stroke="#EF4444"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="Target TE (%)"
                stroke="#F59E0B"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Optional: Dynamic Cushion (if allocation_mode is dynamic_cushion) */}
      {portfolio.some(bar => bar.weights_json?._cs_cushion != null) && (
        <div>
          <h3 className="text-sm font-medium mb-2">Dynamic Cushion (Relative Performance)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart
              data={portfolio.map(bar => {
                const weights = bar.weights_json || {}
                return {
                  date: new Date(bar.date).toLocaleDateString('fr-FR', { month: '2-digit', year: 'numeric' }),
                  dateFull: bar.date,
                  'Relative Index': weights._cs_rel_index ?? null,
                  'Relative Floor': weights._cs_rel_floor ?? null,
                  'Cushion': weights._cs_cushion ?? null,
                }
              })}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="Relative Index"
                stroke="#8B5CF6"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="Relative Floor"
                stroke="#EF4444"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="Cushion"
                stroke="#10B981"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
