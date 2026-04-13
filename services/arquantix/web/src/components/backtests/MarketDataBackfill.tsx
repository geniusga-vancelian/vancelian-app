'use client'

import { useState, useEffect } from 'react'

interface MissingInstrument {
  id: number
  symbol: string
  name: string | null
  asset_class: string
  weekend_tradable: boolean
  bars_count: number
}

interface BackfillItem {
  symbol: string
  instrument_id: number
  status: 'ok' | 'error' | 'skip'
  bars_added: number
  error: string | null
  duration_ms: number
}

interface BackfillResponse {
  db_name: string
  start: string
  end: string
  days: number
  total_instruments: number
  missing_before: number
  processed: BackfillItem[]
  missing_after: number
  total_bars_added: number
  duration_ms: number
}

interface ValidateProviderItem {
  symbol: string
  asset_class: string
  function_used: string
  ok: boolean
  sample_date: string | null
  sample_open: number | null
  sample_close: number | null
  error: string | null
  available_keys: string[] | null
}

interface ValidateProviderResponse {
  total: number
  passed: number
  failed: number
  results: ValidateProviderItem[]
}

export function MarketDataBackfill() {
  const [missing, setMissing] = useState<MissingInstrument[]>([])
  const [loading, setLoading] = useState(false)
  const [backfilling, setBackfilling] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<ValidateProviderResponse | null>(null)
  const [days, setDays] = useState(365)
  const [result, setResult] = useState<BackfillResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadMissing = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/market-data/missing', {
        credentials: 'include',
      })
      const responseText = await response.text()
      let responseData: any = null
      try {
        responseData = responseText ? JSON.parse(responseText) : null
      } catch {
        responseData = { error: responseText || 'Failed to parse response' }
      }
      
      if (!response.ok) {
        const errorMsg = responseData.error || `Failed to load missing instruments (${response.status})`
        const backendBody = responseData.backend_body ? JSON.stringify(responseData.backend_body).substring(0, 200) : ''
        throw new Error(`${errorMsg}${backendBody ? `: ${backendBody}` : ''}`)
      }
      setMissing(responseData)
    } catch (err: any) {
      setError(err.message || 'Failed to load missing instruments')
    } finally {
      setLoading(false)
    }
  }

  const handleBackfill = async () => {
    setBackfilling(true)
    setError(null)
    setResult(null)
    try {
      const response = await fetch('/api/market-data/backfill-missing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ days, force: false }),
      })
      const responseText = await response.text()
      let responseData: any = null
      try {
        responseData = responseText ? JSON.parse(responseText) : null
      } catch {
        responseData = { error: responseText || 'Failed to parse response' }
      }
      
      if (!response.ok) {
        const errorMsg = responseData.error || `Backfill failed (${response.status})`
        const backendBody = responseData.backend_body ? JSON.stringify(responseData.backend_body).substring(0, 200) : ''
        throw new Error(`${errorMsg}${backendBody ? `: ${backendBody}` : ''}`)
      }
      setResult(responseData)
      // Reload missing list after backfill
      await loadMissing()
    } catch (err: any) {
      setError(err.message || 'Backfill failed')
    } finally {
      setBackfilling(false)
    }
  }

  const handleValidate = async () => {
    setValidating(true)
    setError(null)
    setValidationResult(null)
    try {
      // CORE_V1 symbols: BTC, ETH, SOL, URTH, QQQ, DIA, GLD
      const coreSymbols = ['BTC', 'ETH', 'SOL', 'URTH', 'QQQ', 'DIA', 'GLD']
      const response = await fetch('/api/market-data/validate-provider', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ symbols: coreSymbols, years: 10 }),
      })
      const responseText = await response.text()
      let responseData: any = null
      try {
        responseData = responseText ? JSON.parse(responseText) : null
      } catch {
        responseData = { error: responseText || 'Failed to parse response' }
      }
      
      if (!response.ok) {
        const errorMsg = responseData.error || `Validation failed (${response.status})`
        const backendBody = responseData.backend_body ? JSON.stringify(responseData.backend_body).substring(0, 200) : ''
        throw new Error(`${errorMsg}${backendBody ? `: ${backendBody}` : ''}`)
      }
      setValidationResult(responseData)
    } catch (err: any) {
      setError(err.message || 'Validation failed')
    } finally {
      setValidating(false)
    }
  }

  useEffect(() => {
    loadMissing()
  }, [])

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Market Data</h2>
        <div className="flex gap-2">
          <button
            onClick={handleValidate}
            disabled={validating || backfilling}
            className="px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 text-white rounded disabled:opacity-50"
          >
            {validating ? 'Validating...' : 'Validate Alpha Vantage (7 assets)'}
          </button>
          <button
            onClick={loadMissing}
            disabled={loading || validating || backfilling}
            className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded text-gray-700 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {validationResult && (
        <div className="mb-4 p-4 bg-gray-50 border rounded">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-900">Alpha Vantage Validation</h3>
            <div className="text-sm">
              <span className={validationResult.failed === 0 ? 'text-green-600' : 'text-red-600'}>
                {validationResult.passed}/{validationResult.total} passed
              </span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-2 py-1 text-left">Symbol</th>
                  <th className="px-2 py-1 text-left">Asset</th>
                  <th className="px-2 py-1 text-left">Function</th>
                  <th className="px-2 py-1 text-center">Status</th>
                  <th className="px-2 py-1 text-left">Sample Date</th>
                  <th className="px-2 py-1 text-right">Sample Open</th>
                  <th className="px-2 py-1 text-right">Sample Close</th>
                  <th className="px-2 py-1 text-left">Error</th>
                </tr>
              </thead>
              <tbody>
                {validationResult.results.map((item, idx) => (
                  <tr key={idx} className="border-t">
                    <td className="px-2 py-1 font-mono">{item.symbol}</td>
                    <td className="px-2 py-1">{item.asset_class}</td>
                    <td className="px-2 py-1 text-xs">{item.function_used}</td>
                    <td className="px-2 py-1 text-center">
                      {item.ok ? (
                        <span className="text-green-600 font-semibold">✓ OK</span>
                      ) : (
                        <span className="text-red-600 font-semibold">✗ FAIL</span>
                      )}
                    </td>
                    <td className="px-2 py-1">{item.sample_date || '-'}</td>
                    <td className="px-2 py-1 text-right">{item.sample_open?.toFixed(2) || '-'}</td>
                    <td className="px-2 py-1 text-right">{item.sample_close?.toFixed(2) || '-'}</td>
                    <td className="px-2 py-1 text-red-600 text-xs max-w-xs truncate">
                      {item.error || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {validationResult.failed > 0 && (
            <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-700">
              ⚠ Some symbols failed validation. Fix errors before backfilling.
            </div>
          )}
        </div>
      )}

      <div className="mb-4">
        <div className="text-sm text-gray-600 mb-2">
          Missing instruments: <span className="font-semibold">{missing.length}</span>
        </div>
        {missing.length > 0 && (
          <div className="text-xs text-gray-500 mb-3">
            {missing.map((m) => m.symbol).join(', ')}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 mb-4">
        <label className="text-sm text-gray-700">
          Days:
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            disabled={backfilling}
            className="ml-2 px-2 py-1 border rounded text-sm"
          >
            <option value={90}>90 days</option>
            <option value={180}>180 days</option>
            <option value={365}>365 days (1 year)</option>
            <option value={730}>730 days (2 years)</option>
          </select>
        </label>
        <button
          onClick={handleBackfill}
          disabled={backfilling || missing.length === 0}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {backfilling ? 'Backfilling...' : 'Backfill all missing instruments'}
        </button>
      </div>

      {missing.length === 0 && !loading && (
        <div className="text-sm text-green-600 bg-green-50 p-3 rounded">
          ✓ All instruments have bars
        </div>
      )}

      {backfilling && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-700">
          ⚠ Alpha Vantage rate limits. This can take a few minutes...
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          <div className="p-3 bg-gray-50 rounded text-sm">
            <div className="grid grid-cols-2 gap-2 mb-2">
              <div>
                <span className="text-gray-600">Processed:</span>{' '}
                <span className="font-semibold">
                  {result.processed.length} / {result.missing_before}
                </span>
              </div>
              <div>
                <span className="text-gray-600">Bars added:</span>{' '}
                <span className="font-semibold">{result.total_bars_added}</span>
              </div>
              <div>
                <span className="text-gray-600">Missing after:</span>{' '}
                <span className="font-semibold">{result.missing_after}</span>
              </div>
              <div>
                <span className="text-gray-600">Duration:</span>{' '}
                <span className="font-semibold">{(result.duration_ms / 1000).toFixed(1)}s</span>
              </div>
            </div>
          </div>

          <div className="max-h-64 overflow-y-auto border rounded">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-2 py-1 text-left">Symbol</th>
                  <th className="px-2 py-1 text-center">Status</th>
                  <th className="px-2 py-1 text-right">Bars</th>
                  <th className="px-2 py-1 text-right">Time</th>
                </tr>
              </thead>
              <tbody>
                {result.processed.map((item, idx) => (
                  <tr key={idx} className="border-t">
                    <td className="px-2 py-1 font-mono">{item.symbol}</td>
                    <td className="px-2 py-1 text-center">
                      {item.status === 'ok' && (
                        <span className="text-green-600 font-semibold">OK</span>
                      )}
                      {item.status === 'error' && (
                        <span className="text-red-600 font-semibold">ERROR</span>
                      )}
                      {item.status === 'skip' && (
                        <span className="text-gray-400">SKIP</span>
                      )}
                    </td>
                    <td className="px-2 py-1 text-right">{item.bars_added}</td>
                    <td className="px-2 py-1 text-right">
                      {(item.duration_ms / 1000).toFixed(1)}s
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {result.processed.some((p) => p.status === 'error') && (
            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs">
              <div className="font-semibold text-red-700 mb-1">Errors:</div>
              {result.processed
                .filter((p) => p.status === 'error')
                .map((p, idx) => (
                  <div key={idx} className="text-red-600">
                    <span className="font-mono">{p.symbol}:</span> {p.error}
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

