'use client'

import { useEffect, useRef, useState } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickData, LineData, Time } from 'lightweight-charts'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

interface CandlePoint {
  time: number  // UNIX seconds
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface AssetPriceChartProps {
  instrumentCode: string
  provider?: string
  startDate?: string
  endDate?: string
  viewMode?: 'line' | 'candle'
  allowCandlestick?: boolean  // If false, disable candlestick toggle (e.g., for bundles)
}

export function AssetPriceChart({
  instrumentCode,
  provider = 'binance',
  startDate,
  endDate,
  viewMode: initialViewMode = 'line',
  allowCandlestick = true,
}: AssetPriceChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Line' | 'Candlestick'> | null>(null)
  const [viewMode, setViewMode] = useState<'line' | 'candle'>(initialViewMode)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [candles, setCandles] = useState<CandlePoint[]>([])

  // Fetch candles
  useEffect(() => {
    if (!instrumentCode) {
      setCandles([])
      return
    }

    const fetchCandles = async () => {
      setIsLoading(true)
      setError(null)
      
      try {
        const params = new URLSearchParams({
          instrument_code: instrumentCode,
          provider,
          tf: '1d',
        })
        
        if (startDate) params.append('start', startDate)
        if (endDate) params.append('end', endDate)

        const response = await fetch(`/api/market-data/candles?${params.toString()}`)
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ error: 'Failed to fetch candles' }))
          throw new Error(errorData.error || errorData.detail || 'Failed to fetch candles')
        }

        const data: CandlePoint[] = await response.json()
        setCandles(data)
      } catch (err: any) {
        console.error('Fetch candles error:', err)
        setError(err.message || 'Failed to load chart data')
        setCandles([])
      } finally {
        setIsLoading(false)
      }
    }

    fetchCandles()
  }, [instrumentCode, provider, startDate, endDate])

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return

    // Cleanup previous chart
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
      seriesRef.current = null
    }

    // Create new chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    })

    chartRef.current = chart

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [])

  // Update series when candles or viewMode changes
  useEffect(() => {
    if (!chartRef.current || candles.length === 0) {
      // Remove existing series if no data
      if (seriesRef.current) {
        chartRef.current?.removeSeries(seriesRef.current)
        seriesRef.current = null
      }
      return
    }

    // Remove existing series
    if (seriesRef.current) {
      chartRef.current.removeSeries(seriesRef.current)
      seriesRef.current = null
    }

    // Create new series based on viewMode
    if (viewMode === 'candle') {
      const candlestickSeries = chartRef.current.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      })

      const candlestickData: CandlestickData[] = candles.map(c => ({
        time: c.time as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))

      candlestickSeries.setData(candlestickData)
      seriesRef.current = candlestickSeries
    } else {
      // Line mode: use close prices
      const lineSeries = chartRef.current.addLineSeries({
        color: '#3B82F6',
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
      })

      const lineData: LineData[] = candles.map(c => ({
        time: c.time as Time,
        value: c.close,
      }))

      lineSeries.setData(lineData)
      seriesRef.current = lineSeries
    }

    // Fit content
    chartRef.current.timeScale().fitContent()
  }, [candles, viewMode])

  if (!instrumentCode) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm text-gray-500 text-center py-8">
          Select an instrument to view price chart
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          {instrumentCode} Price Chart
        </h3>
        {allowCandlestick ? (
          <div className="flex items-center space-x-2">
            <Label htmlFor="view-mode-switch" className="text-sm text-gray-700">
              Line
            </Label>
            <Switch
              id="view-mode-switch"
              checked={viewMode === 'candle'}
              onCheckedChange={(checked) => setViewMode(checked ? 'candle' : 'line')}
            />
            <Label htmlFor="view-mode-switch" className="text-sm text-gray-700">
              Candle
            </Label>
          </div>
        ) : (
          <div className="text-xs text-gray-500 italic">
            Candlestick only available for a single instrument
          </div>
        )}
      </div>

      {isLoading && (
        <div className="text-center py-8 text-sm text-gray-500">
          Loading chart data...
        </div>
      )}

      {error && (
        <div className="text-center py-8 text-sm text-red-600">
          {error}
        </div>
      )}

      {!isLoading && !error && candles.length === 0 && (
        <div className="text-center py-8 text-sm text-gray-500">
          No data available for this instrument
        </div>
      )}

      {!isLoading && !error && candles.length > 0 && (
        <div ref={chartContainerRef} className="w-full" style={{ height: '400px' }} />
      )}
    </div>
  )
}

