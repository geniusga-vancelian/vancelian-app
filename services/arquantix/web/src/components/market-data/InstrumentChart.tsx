'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useEffect, useState, useRef } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts'

interface Bar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface InstrumentChartProps {
  instrumentId: number | null
  instrumentSymbol: string | null
  startDate: string
  endDate: string
  viewMode: 'base100' | 'price'
  chartType: 'line' | 'candlestick'
  /** Increment to force refetch of bars (e.g. after "Refresh Market data") */
  refreshKey?: number
}

export function InstrumentChart({ 
  instrumentId, 
  instrumentSymbol, 
  startDate, 
  endDate,
  viewMode,
  chartType,
  refreshKey = 0,
}: InstrumentChartProps) {
  const [bars, setBars] = useState<Bar[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

  useEffect(() => {
    if (!instrumentId || !startDate || !endDate) {
      setBars([])
      setError(null)
      return
    }

    const loadBars = async () => {
      setLoading(true)
      setError(null)
      
      try {
        const response = await fetch(
          `/api/market-data/bars?instrument_id=${instrumentId}&start=${startDate}&end=${endDate}`,
          { credentials: 'include' }
        )

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ error: 'Failed to load data' }))
          throw new Error(errorData.error || `Failed to load bars (${response.status})`)
        }

        const data = await response.json()
        setBars(data.bars || [])
      } catch (err: any) {
        console.error('Error loading bars:', err)
        setError(err.message || 'Failed to load historical data')
        setBars([])
      } finally {
        setLoading(false)
      }
    }

    loadBars()
  }, [instrumentId, startDate, endDate, refreshKey])

  // Cleanup lightweight-charts when switching away from candlestick
  useEffect(() => {
    if (chartType !== 'candlestick' && chartInstanceRef.current) {
      chartInstanceRef.current.remove()
      chartInstanceRef.current = null
      seriesRef.current = null
    }
  }, [chartType])

  // Render lightweight-charts candlestick
  useEffect(() => {
    if (chartType !== 'candlestick' || !chartContainerRef.current || !bars.length) {
      // Cleanup if switching away from candlestick or no data
      if (chartType !== 'candlestick' && chartInstanceRef.current) {
        chartInstanceRef.current.remove()
        chartInstanceRef.current = null
        seriesRef.current = null
      }
      return
    }

    // Wait for container to have dimensions
    if (chartContainerRef.current.clientWidth === 0 || chartContainerRef.current.clientHeight === 0) {
      // Retry after a short delay
      const timeoutId = setTimeout(() => {
        // This will trigger a re-render if dimensions are available
      }, 100)
      return () => clearTimeout(timeoutId)
    }

    // Cleanup existing chart before creating new one
    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove()
      chartInstanceRef.current = null
      seriesRef.current = null
    }

    const container = chartContainerRef.current
    const width = container.clientWidth || 800
    const height = container.clientHeight || 600

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: 'white' },
        textColor: '#333',
      },
      width,
      height,
      grid: {
        vertLines: { color: '#e5e7eb' },
        horzLines: { color: '#e5e7eb' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    })

    let candlestickSeries: ISeriesApi<'Candlestick'>
    try {
      candlestickSeries = chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      console.error('Error creating candlestick series:', err)
      throw new Error(`Failed to create candlestick series: ${message}`)
    }

    // Prepare data for lightweight-charts
    // Ensure Open, High, Low, Close are correctly formatted as numbers
    const firstClose = bars[0]?.close || 1
    const candlestickData: CandlestickData[] = bars.map((bar) => {
      const date = new Date(bar.date + 'T00:00:00Z')
      // lightweight-charts expects UTC timestamp in seconds
      const time = (date.getTime() / 1000) as Time
      
      // Convert to numbers explicitly (ensure they are not Decimal types)
      let open = viewMode === 'base100' 
        ? (Number(bar.open) / Number(firstClose)) * 100 
        : Number(bar.open)
      let high = viewMode === 'base100' 
        ? (Number(bar.high) / Number(firstClose)) * 100 
        : Number(bar.high)
      let low = viewMode === 'base100' 
        ? (Number(bar.low) / Number(firstClose)) * 100 
        : Number(bar.low)
      let close = viewMode === 'base100' 
        ? (Number(bar.close) / Number(firstClose)) * 100 
        : Number(bar.close)
      
      // Ensure data integrity for candlesticks: high >= low, open and close within [low, high]
      // This is CRITICAL for candlestick charts to render correctly
      // If high < low, the candlestick will not render properly
      if (high < low) {
        console.warn(`[Candlestick] High < Low for ${bar.date}. Original: high=${high}, low=${low}. Swapping.`)
        ;[high, low] = [low, high]
      }
      
      // Ensure open and close are within [low, high] range
      // If they are outside, clamp them to the range
      const originalOpen = open
      const originalClose = close
      open = Math.max(low, Math.min(high, open))
      close = Math.max(low, Math.min(high, close))
      
      if (originalOpen !== open || originalClose !== close) {
        console.warn(`[Candlestick] Open or Close outside [low, high] for ${bar.date}. Clamped values.`)
      }
      
      // Return data with explicit number conversion to ensure they are numbers, not strings
      return {
        time,
        open: Number(open),
        high: Number(high),
        low: Number(low),
        close: Number(close),
      }
    })

    candlestickSeries.setData(candlestickData)
    
    // Fit content after data is set
    setTimeout(() => {
      chart.timeScale().fitContent()
    }, 100)

    chartInstanceRef.current = chart
    seriesRef.current = candlestickSeries

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({ 
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight 
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (chart) {
        chart.remove()
      }
      chartInstanceRef.current = null
      seriesRef.current = null
    }
  }, [bars, chartType, viewMode])

  if (!instrumentId) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
        <div className="text-center text-gray-500">
          <p className="text-lg font-medium mb-2">Aucun instrument sélectionné</p>
          <p className="text-sm">Sélectionnez un instrument dans le tableau pour voir son graphique</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
        <div className="text-center text-gray-500">
          <p>Chargement des données historiques...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-red-50 rounded-lg border border-red-200">
        <div className="text-center text-red-700">
          <p className="font-semibold mb-2">Erreur</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    )
  }

  if (bars.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200 p-6">
        <div className="text-center text-gray-500 max-w-md">
          <p className="text-lg font-medium mb-2">Aucune donnée disponible</p>
          <p className="text-sm mb-2">Aucune barre historique trouvée pour {instrumentSymbol} sur la plage de dates sélectionnée.</p>
          <p className="text-xs text-gray-400">
            Pour les assets Binance, lancez l’ingestion 1d depuis le répertoire <code className="bg-gray-200 px-1 rounded">api</code> :{' '}
            <code className="bg-gray-200 px-1 rounded text-left block mt-1">python scripts/run_candles_1d_ingestion.py</code>
            {' '}ou le backfill :{' '}
            <code className="bg-gray-200 px-1 rounded text-left block mt-1">python scripts/run_candles_backfill.py --timeframe 1d --confirm</code>
          </p>
        </div>
      </div>
    )
  }

  // Render candlestick chart (handled by lightweight-charts effect above)
  if (chartType === 'candlestick') {
    return (
      <div className="h-full flex flex-col">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {instrumentSymbol} - {viewMode === 'base100' ? 'Base 100' : 'Prix Réel'} (Candlestick)
          </h3>
          <p className="text-sm text-gray-600">
            {bars.length} barres du {bars[0]?.date} au {bars[bars.length - 1]?.date}
          </p>
        </div>
        
        <div className="flex-1 min-h-0 w-full" ref={chartContainerRef} style={{ minHeight: '400px' }} />
      </div>
    )
  }

  // Render line chart (recharts)
  const firstClose = bars[0]?.close || 1
  const chartData = bars.map(bar => ({
    date: new Date(bar.date).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric', year: 'numeric' }),
    dateFull: bar.date,
    Close: viewMode === 'base100' 
      ? parseFloat(((bar.close / firstClose) * 100).toFixed(2))
      : parseFloat(bar.close.toFixed(2)),
    Open: viewMode === 'base100'
      ? parseFloat(((bar.open / firstClose) * 100).toFixed(2))
      : parseFloat(bar.open.toFixed(2)),
    High: viewMode === 'base100'
      ? parseFloat(((bar.high / firstClose) * 100).toFixed(2))
      : parseFloat(bar.high.toFixed(2)),
    Low: viewMode === 'base100'
      ? parseFloat(((bar.low / firstClose) * 100).toFixed(2))
      : parseFloat(bar.low.toFixed(2)),
    Volume: bar.volume,
  }))

  return (
    <div className="h-full flex flex-col">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          {instrumentSymbol} - {viewMode === 'base100' ? 'Base 100' : 'Prix Réel'} (Line Chart)
        </h3>
        <p className="text-sm text-gray-600">
          {bars.length} barres du {bars[0]?.date} au {bars[bars.length - 1]?.date}
        </p>
      </div>
      
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="date" 
              stroke="#6b7280"
              fontSize={12}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis 
              stroke="#6b7280"
              fontSize={12}
              label={{ 
                value: viewMode === 'base100' ? 'Prix (Base 100)' : 'Prix Réel', 
                angle: -90, 
                position: 'insideLeft' 
              }}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '6px' }}
              labelFormatter={(label) => `Date: ${label}`}
              formatter={(value: any, name?: string) => {
                if (name === 'Volume') {
                  return [value.toLocaleString('fr-FR'), 'Volume']
                }
                const numValue = typeof value === 'number' ? value : parseFloat(String(value))
                return [numValue.toFixed(2), name ?? '']
              }}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="Close" 
              stroke="#3B82F6" 
              strokeWidth={2}
              dot={false}
              name={`Close (${viewMode === 'base100' ? 'Base 100' : 'Prix Réel'})`}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
