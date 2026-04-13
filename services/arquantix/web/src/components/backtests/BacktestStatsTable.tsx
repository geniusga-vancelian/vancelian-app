'use client'

interface BacktestStatsTableProps {
  portfolioMetrics: Record<string, number>
  instrumentMetrics: Array<{
    instrument_id: number
    symbol: string
    metrics: Record<string, number>
  }>
}

export function BacktestStatsTable({ portfolioMetrics, instrumentMetrics }: BacktestStatsTableProps) {
  const metrics = [
    { key: 'cagr', label: 'CAGR (%)', format: (v: number) => (v * 100).toFixed(2) },
    { key: 'volatility', label: 'Volatility (%)', format: (v: number) => (v * 100).toFixed(2) },
    { key: 'sharpe', label: 'Sharpe Ratio', format: (v: number) => v.toFixed(2) },
    { key: 'calmar', label: 'Calmar Ratio', format: (v: number) => v.toFixed(2) },
    { key: 'max_drawdown', label: 'Max Drawdown (%)', format: (v: number) => (v * 100).toFixed(2) },
    { key: 'mean_daily_return', label: 'Mean Daily Return (%)', format: (v: number) => (v * 100).toFixed(4) },
    { key: 'variance_daily_return', label: 'Variance Daily Return', format: (v: number) => v.toFixed(6) },
  ]

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Métrique
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Portfolio
            </th>
            {instrumentMetrics.map(inst => (
              <th
                key={inst.instrument_id}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {inst.symbol}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {metrics.map(metric => (
            <tr key={metric.key}>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{metric.label}</td>
              <td className="px-4 py-3 text-sm text-gray-700">
                {portfolioMetrics[metric.key] !== undefined
                  ? metric.format(portfolioMetrics[metric.key])
                  : 'N/A'}
              </td>
              {instrumentMetrics.map(inst => (
                <td key={inst.instrument_id} className="px-4 py-3 text-sm text-gray-700">
                  {inst.metrics[metric.key] !== undefined ? metric.format(inst.metrics[metric.key]) : 'N/A'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}





