'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { PortfolioBar } from './types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle } from 'lucide-react'

interface CPPIChartsProps {
  portfolio: PortfolioBar[]
  strategyParams?: {
    floor_ratio?: number
    multiplier?: number
    risky_cap?: number
    core_min?: number
  }
}

export function CPPICharts({ portfolio, strategyParams }: CPPIChartsProps) {
  // Check if we have CPPI data
  const hasCPPIData = portfolio.some(bar => 
    bar.weights_json?._cppi_risky_weight != null || 
    bar.weights_json?._cppi_core_weight != null
  )

  if (!hasCPPIData) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="flex items-center gap-3 text-amber-600 bg-amber-50 p-4 rounded-lg border border-amber-200">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium">CPPI allocation data not available</p>
              <p className="text-amber-700 mt-1">
                Ensure CPPI debug/weights_json is stored per date. Run backtest with debug=true.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Prepare allocation chart data (Core vs Risky weights)
  const allocationChartData: Array<{
    date: string
    dateFull: string
    'Risky Weight (%)': number | null
    'Core Weight (%)': number | null
  }> = []

  portfolio.forEach(bar => {
    const weights = bar.weights_json
    const riskyWeight = weights?._cppi_risky_weight != null ? Number(weights._cppi_risky_weight) * 100 : null
    const coreWeight = weights?._cppi_core_weight != null ? Number(weights._cppi_core_weight) * 100 : (riskyWeight != null ? 100 - riskyWeight : null)
    
    allocationChartData.push({
      date: new Date(bar.date).toLocaleDateString('fr-FR', { month: '2-digit', year: 'numeric' }),
      dateFull: bar.date,
      'Risky Weight (%)': riskyWeight,
      'Core Weight (%)': coreWeight,
    })
  })

  return (
    <div className="space-y-6">
      {/* Full-width Allocation Chart (Core vs Risky) */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">CPPI Allocation (Core vs Risky)</CardTitle>
        </CardHeader>
        <CardContent>
          {allocationChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={allocationChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  stroke="#6b7280"
                  fontSize={12}
                  tick={{ fill: '#6b7280' }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  stroke="#6b7280"
                  fontSize={12}
                  tick={{ fill: '#6b7280' }}
                  domain={[0, 100]}
                  label={{ value: '%', angle: -90, position: 'insideLeft', fill: '#6b7280' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                    fontSize: '12px',
                  }}
                  labelFormatter={(label) => {
                    const point = allocationChartData.find(p => p.date === label)
                    return point?.dateFull ? new Date(point.dateFull).toLocaleDateString('fr-FR') : label
                  }}
                  formatter={(value) =>
                    value != null && typeof value === 'number' ? `${value.toFixed(2)}%` : 'N/A'
                  }
                />
                <Legend
                  wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
                  iconType="line"
                />
                <Line
                  type="monotone"
                  dataKey="Core Weight (%)"
                  stroke="#10B981"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  connectNulls={false}
                />
                <Line
                  type="monotone"
                  dataKey="Risky Weight (%)"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                  connectNulls={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[400px] flex items-center justify-center text-gray-500 text-sm">
              No allocation data available
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
