'use client'

import { PerformanceResponse } from './types'

interface HistoryStatsTableProps {
  performance: PerformanceResponse
}

export function HistoryStatsTable({ performance }: HistoryStatsTableProps) {
  const validInstruments = performance.instruments.filter(inst => inst.stats !== null)

  if (validInstruments.length === 0) {
    return (
      <div className="text-sm text-gray-500">
        No statistics available (no valid data for any instrument)
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Instrument
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Total Return (%)
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Max Drawdown (%)
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Vol Annual (%)
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {validInstruments.map(inst => (
            <tr key={inst.instrument_id}>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{inst.symbol}</td>
              <td className="px-4 py-3 text-sm text-gray-700">
                {inst.stats ? (inst.stats.total_return * 100).toFixed(2) : 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-700">
                {inst.stats ? (inst.stats.max_drawdown * 100).toFixed(2) : 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-700">
                {inst.stats ? (inst.stats.vol_annual * 100).toFixed(2) : 'N/A'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}






