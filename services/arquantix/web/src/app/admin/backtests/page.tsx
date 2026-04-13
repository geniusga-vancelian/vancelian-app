'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { BacktestChart } from '@/components/backtests/BacktestChart'
import { BacktestStatsTable } from '@/components/backtests/BacktestStatsTable'
import { CPPICharts } from '@/components/backtests/CPPICharts'
import { CoreSatelliteCharts } from '@/components/backtests/CoreSatelliteCharts'
import type { InstrumentInfo, Bundle, BacktestCreateRequest, BacktestDetailResponse, SeriesResponse } from '@/components/backtests/types'
import { Play, BarChart3, Package } from 'lucide-react'
import { z } from 'zod'

export default function BacktestsPage() {
  const router = useRouter()
  
  // Data sources
  const [instruments, setInstruments] = useState<InstrumentInfo[]>([])
  const [bundles, setBundles] = useState<Bundle[]>([])
  const [loadingInstruments, setLoadingInstruments] = useState(true)
  const [loadingBundles, setLoadingBundles] = useState(true)

  // Selection state
  const [selectionType, setSelectionType] = useState<'instruments' | 'bundle'>('instruments')
  const [selectedInstrumentIds, setSelectedInstrumentIds] = useState<number[]>([])
  const [selectedBundleId, setSelectedBundleId] = useState<string>('')

  // Backtest config
  const [name, setName] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [strategyType, setStrategyType] = useState<'equal_weight' | 'momentum' | 'bundle_strategy' | 'CPPI' | 'CORE_SATELLITE'>('equal_weight')
  const [lookbackDays, setLookbackDays] = useState(20)
  // CPPI params - JSON textarea
  const CPPI_DEFAULTS = {
    floor_ratio: 0.90,
    multiplier: 4.0,
    risky_cap: 1.0,
    core_min: 0.0,
    core_yield: 0.035,
    day_count: 365,
    debug: false,
  }
  const [cppiParamsJson, setCppiParamsJson] = useState<string>('')
  const [cppiParamsError, setCppiParamsError] = useState<string | null>(null)
  const [cppiDebug, setCppiDebug] = useState(false)
  // Core-Satellite params - JSON textarea
  const CORE_SATELLITE_DEFAULTS = {
    core_yield: 0.035,
    target_te: 0.10,
    te_tolerance: 0.0025,
    te_max_hard_mult: 1.10,
    lookback_risk_days: 63,
    lookback_return_days: 63,
    day_count: 252,
    core_min: 0.0,
    max_weight_per_asset: 0.40,
    core_grid_step: 0.01,
    sat_min: 0.0,
    shrinkage: false,
    turnover_penalty: 0.0,
    stability_penalty: 0.0,
    optimization_method: 'grid',
    allocation_mode: 'te_target',
    lambda_risk: 0.2,
    multiplier: 4.0,
    floor_rel_ratio: 0.95,
    floor_accrues_with_core: true,
    debug: false,
  }
  const [coreSatelliteParamsJson, setCoreSatelliteParamsJson] = useState<string>('')
  const [coreSatelliteParamsError, setCoreSatelliteParamsError] = useState<string | null>(null)
  const [coreSatelliteDebug, setCoreSatelliteDebug] = useState(false)
  const [rebalance, setRebalance] = useState<'daily' | 'weekly' | 'monthly'>('weekly')
  const [feesBps, setFeesBps] = useState(0)
  const [slippageBps, setSlippageBps] = useState(0)
  const [allowWeekendTrading, setAllowWeekendTrading] = useState(true)

  // Results state
  const [running, setRunning] = useState(false)
  const [runId, setRunId] = useState<number | null>(null)
  const [backtestDetail, setBacktestDetail] = useState<BacktestDetailResponse | null>(null)
  const [backtestSeries, setBacktestSeries] = useState<SeriesResponse | null>(null)
  const [loadingResults, setLoadingResults] = useState(false)

  useEffect(() => {
    // Check if user is authenticated
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          router.push('/admin/login')
          return
        }
        fetchInstruments()
        fetchBundles()
        
        // Set default dates (1 year back to today)
        const today = new Date()
        const oneYearAgo = new Date()
        oneYearAgo.setFullYear(today.getFullYear() - 1)
        setEndDate(today.toISOString().split('T')[0])
        setStartDate(oneYearAgo.toISOString().split('T')[0])
      })
      .catch(() => {
        router.push('/admin/login')
      })
  }, [router])

  const fetchInstruments = async () => {
    setLoadingInstruments(true)
    try {
      const response = await fetch('/api/market-data/instruments?is_active=true', {
        credentials: 'include',
      })

      const data = await response.json()

      if (response.ok) {
        setInstruments(data.instruments || data || [])
      }
    } catch (error: any) {
      console.error('Error fetching instruments:', error)
      setInstruments([])
    } finally {
      setLoadingInstruments(false)
    }
  }

  const fetchBundles = async () => {
    setLoadingBundles(true)
    try {
      const response = await fetch('/api/bundles', {
        credentials: 'include',
      })

      const data = await response.json()

      if (response.ok) {
        setBundles(data.bundles || data || [])
      }
    } catch (error: any) {
      console.error('Error fetching bundles:', error)
      setBundles([])
    } finally {
      setLoadingBundles(false)
    }
  }

  const handleRun = async () => {
    // Validation
    if (!startDate || !endDate) {
      toastError('Veuillez sélectionner une période')
      return
    }

    if (new Date(endDate) <= new Date(startDate)) {
      toastError('La date de fin doit être après la date de début')
      return
    }

    if (selectionType === 'instruments' && selectedInstrumentIds.length === 0) {
      toastError('Veuillez sélectionner au moins un instrument')
      return
    }

    if (selectionType === 'bundle' && !selectedBundleId) {
      toastError('Veuillez sélectionner un bundle')
      return
    }

    if (strategyType === 'momentum' && (!lookbackDays || lookbackDays < 1 || lookbackDays > 252)) {
      toastError('Lookback days doit être entre 1 et 252')
      return
    }

    setRunning(true)
    setRunId(null)
    setBacktestDetail(null)
    setBacktestSeries(null)

    try {
      // If bundle selected, fetch bundle to get instrument_ids
      let finalInstrumentIds = selectedInstrumentIds

      if (selectionType === 'bundle' && selectedBundleId) {
        const bundle = bundles.find(b => b.id === selectedBundleId)
        if (bundle) {
          finalInstrumentIds = bundle.instrument_ids
        }
      }

      // Parse CPPI params if strategy is CPPI
      let cppiParams: Record<string, any> | undefined = undefined
      if (strategyType === 'CPPI') {
        const parsed = parseCppiParams(cppiParamsJson)
        if (parsed === null && cppiParamsJson.trim()) {
          // Invalid JSON and not empty - validation error already set
          return
        }
        // Merge with defaults (parsed can be partial or null)
        const mergedCppi: Record<string, unknown> = {
          ...CPPI_DEFAULTS,
          ...parsed,
          debug: cppiDebug,
        }
        Object.keys(mergedCppi).forEach((key) => {
          if (mergedCppi[key] === undefined) {
            delete mergedCppi[key]
          }
        })
        cppiParams = mergedCppi
      }

      // Parse Core-Satellite params if strategy is CORE_SATELLITE
      let coreSatelliteParams: Record<string, any> | undefined = undefined
      if (strategyType === 'CORE_SATELLITE') {
        const parsed = parseCoreSatelliteParams(coreSatelliteParamsJson)
        if (parsed === null && coreSatelliteParamsJson.trim()) {
          // Invalid JSON and not empty - validation error already set
          return
        }
        const mergedCs: Record<string, unknown> = {
          ...CORE_SATELLITE_DEFAULTS,
          ...parsed,
          debug: coreSatelliteDebug,
        }
        Object.keys(mergedCs).forEach((key) => {
          if (mergedCs[key] === undefined) {
            delete mergedCs[key]
          }
        })
        coreSatelliteParams = mergedCs
      }

      const request: BacktestCreateRequest = {
        name: name || undefined,
        start_date: startDate,
        end_date: endDate,
        instrument_ids: selectionType === 'bundle' && (strategyType === 'CPPI' || strategyType === 'CORE_SATELLITE') ? undefined : finalInstrumentIds,
        bundle_id: selectionType === 'bundle' ? selectedBundleId : undefined,
        strategy: {
          type: strategyType,
          params: strategyType === 'momentum' ? { lookback_days: lookbackDays } : 
                  strategyType === 'CPPI' ? cppiParams : 
                  strategyType === 'CORE_SATELLITE' ? coreSatelliteParams : undefined,
        },
        rebalance,
        fees_bps: feesBps,
        slippage_bps: slippageBps,
        allow_weekend_trading: allowWeekendTrading,
      }

      const response = await fetch('/api/backtests/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(request),
      })

      const responseText = await response.text()
      let data: any = null

      try {
        data = responseText ? JSON.parse(responseText) : null
      } catch {
        data = { error: responseText || 'Failed to parse response' }
      }

      if (!response.ok) {
        const errorMsg = data.error || data.detail || data.message || `Backtest failed (${response.status})`
        toastError(`Échec du backtest: ${errorMsg}`)
        return
      }

      toastSuccess('Backtest lancé avec succès')
      setRunId(data.run_id)

      // Load results (chart will appear on the right)
      await loadResults(data.run_id)
    } catch (error: any) {
      console.error('[Backtest] Run error:', error)
      toastError(`Erreur lors du backtest: ${error.message}`)
    } finally {
      setRunning(false)
    }
  }

  const loadResults = async (id: number) => {
    setLoadingResults(true)
    try {
      // Load detail
      const detailRes = await fetch(`/api/backtests/${id}`, {
        credentials: 'include',
      })

      if (detailRes.ok) {
        const detailData = await detailRes.json()
        setBacktestDetail(detailData)
      }

      // Load series
      const seriesRes = await fetch(`/api/backtests/${id}/series`, {
        credentials: 'include',
      })

      if (seriesRes.ok) {
        const seriesData = await seriesRes.json()
        // Ensure data structure matches expected format
        setBacktestSeries({
          portfolio: seriesData.portfolio || seriesData.portfolio_series || [],
          instruments: seriesData.instruments || seriesData.instrument_series || [],
        })
      } else {
        // If series not available (backtest pending), set empty arrays
        setBacktestSeries({
          portfolio: [],
          instruments: [],
        })
      }
    } catch (error: any) {
      console.error('Error loading results:', error)
      toastError('Failed to load backtest results')
      // Set empty arrays on error to prevent undefined errors
      setBacktestSeries({
        portfolio: [],
        instruments: [],
      })
    } finally {
      setLoadingResults(false)
    }
  }

  const toggleInstrument = (instrumentId: number) => {
    setSelectedInstrumentIds(prev => {
      if (prev.includes(instrumentId)) {
        return prev.filter(id => id !== instrumentId)
      } else {
        return [...prev, instrumentId]
      }
    })
  }

  // CPPI params validation schema
  const cppiParamsSchema = z.object({
    floor_ratio: z.number().min(0).max(1).optional(),
    multiplier: z.number().min(0).optional(),
    risky_cap: z.number().min(0).max(1).optional(),
    core_min: z.number().min(0).max(1).optional(),
    core_yield: z.number().min(0).optional(),
    day_count: z.number().int().min(1).optional(),
    debug: z.boolean().optional(),
  })

  // Parse and validate CPPI params JSON
  const parseCppiParams = (jsonString: string): Record<string, any> | null => {
    if (!jsonString.trim()) {
      setCppiParamsError(null)
      return null // Empty string means use defaults
    }
    try {
      const parsed = JSON.parse(jsonString)
      const validated = cppiParamsSchema.parse(parsed)
      setCppiParamsError(null) // Clear error on success
      return validated
    } catch (error) {
      if (error instanceof z.ZodError) {
        const errors = error.issues
          .map((e) => `${e.path.map(String).join('.')}: ${e.message}`)
          .join(', ')
        setCppiParamsError(`Validation error: ${errors}`)
      } else {
        setCppiParamsError('Invalid JSON format')
      }
      return null
    }
  }

  // Core-Satellite params validation schema
  const coreSatelliteParamsSchema = z.object({
    core_yield: z.number().min(0).optional(),
    target_te: z.number().min(0).max(1).optional(),
    te_tolerance: z.number().min(0).optional(),
    te_max_hard_mult: z.number().min(1).optional(),
    lookback_risk_days: z.number().int().min(5).optional(),
    lookback_return_days: z.number().int().min(5).optional(),
    day_count: z.number().int().min(1).optional(),
    core_min: z.number().min(0).max(1).optional(),
    max_weight_per_asset: z.number().min(0).max(1).optional(),
    core_grid_step: z.number().min(0).max(1).optional(),
    top_k_satellite: z.number().int().min(1).optional(),
    sat_min: z.number().min(0).max(1).optional(),
    shrinkage: z.boolean().optional(),
    turnover_penalty: z.number().min(0).optional(),
    stability_penalty: z.number().min(0).optional(),
    optimization_method: z.enum(['grid', 'quadratic']).optional(),
    allocation_mode: z.enum(['te_target', 'utility_lambda', 'dynamic_cushion']).optional(),
    lambda_risk: z.number().min(0).optional(),
    multiplier: z.number().min(0).optional(),
    floor_rel_ratio: z.number().min(0).max(1).optional(),
    floor_accrues_with_core: z.boolean().optional(),
    sat_max: z.number().min(0).max(1).optional(),
    debug: z.boolean().optional(),
  })

  // Parse and validate Core-Satellite params JSON
  const parseCoreSatelliteParams = (jsonString: string): Record<string, any> | null => {
    if (!jsonString.trim()) {
      setCoreSatelliteParamsError(null)
      return null // Empty string means use defaults
    }
    try {
      const parsed = JSON.parse(jsonString)
      const validated = coreSatelliteParamsSchema.parse(parsed)
      setCoreSatelliteParamsError(null) // Clear error on success
      return validated
    } catch (error) {
      if (error instanceof z.ZodError) {
        const errors = error.issues
          .map((e) => `${e.path.map(String).join('.')}: ${e.message}`)
          .join(', ')
        setCoreSatelliteParamsError(`Validation error: ${errors}`)
      } else {
        setCoreSatelliteParamsError('Invalid JSON format')
      }
      return null
    }
  }

  // Use defaults for Core-Satellite params
  const useCoreSatelliteDefaults = () => {
    setCoreSatelliteParamsJson(JSON.stringify(CORE_SATELLITE_DEFAULTS, null, 2))
    setCoreSatelliteParamsError(null)
    setCoreSatelliteDebug(CORE_SATELLITE_DEFAULTS.debug)
  }

  // Use defaults for CPPI params
  const useCppiDefaults = () => {
    setCppiParamsJson(JSON.stringify(CPPI_DEFAULTS, null, 2))
    setCppiParamsError(null)
    setCppiDebug(CPPI_DEFAULTS.debug)
  }

  // Update selected instruments when bundle changes
  useEffect(() => {
    if (selectionType === 'bundle' && selectedBundleId) {
      const bundle = bundles.find(b => b.id === selectedBundleId)
      if (bundle) {
        setSelectedInstrumentIds(bundle.instrument_ids)
      }
    }
  }, [selectedBundleId, bundles, selectionType])

  // Initialize strategy type when selection type changes
  useEffect(() => {
    if (selectionType === 'bundle') {
      // When switching to bundle, preserve CPPI or CORE_SATELLITE if already selected, otherwise default to bundle_strategy
      if (strategyType !== 'bundle_strategy' && strategyType !== 'CPPI' && strategyType !== 'CORE_SATELLITE') {
        setStrategyType('bundle_strategy')
      }
    } else if (selectionType === 'instruments') {
      // When switching to instruments, default to equal_weight if current strategy is bundle_strategy
      if (strategyType === 'bundle_strategy') {
        setStrategyType('equal_weight')
      }
    }
  }, [selectionType])

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Backtests</h1>

      {/* Two-column layout: Configuration on left, Chart on right */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Configuration */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Configuration du Backtest</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nom du Backtest (optionnel)
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Ex: Test Crypto Portfolio 2024"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>

                {/* Selection Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Source des Instruments
                  </label>
                  <Select value={selectionType} onValueChange={(v: 'instruments' | 'bundle') => setSelectionType(v)}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="instruments">Instruments individuels</SelectItem>
                      <SelectItem value="bundle">Bundle</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Instruments Selection */}
                {selectionType === 'instruments' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Instruments ({selectedInstrumentIds.length} sélectionné{selectedInstrumentIds.length !== 1 ? 's' : ''})
                    </label>
                    {loadingInstruments ? (
                      <div className="text-gray-500 py-4">Chargement des instruments...</div>
                    ) : instruments.length === 0 ? (
                      <div className="text-gray-500 py-4">
                        Aucun instrument disponible. Créez des instruments dans Market Data.
                      </div>
                    ) : (
                      <div className="border border-gray-300 rounded-md p-4 max-h-64 overflow-y-auto">
                        <div className="space-y-2">
                          {instruments.map((inst) => (
                            <label
                              key={inst.id}
                              className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
                            >
                              <input
                                type="checkbox"
                                checked={selectedInstrumentIds.includes(inst.id)}
                                onChange={() => toggleInstrument(inst.id)}
                                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                              />
                              <div className="flex-1">
                                <span className="font-medium">{inst.symbol}</span>
                                {inst.name && (
                                  <span className="text-sm text-gray-600 ml-2">({inst.name})</span>
                                )}
                                <span className="text-xs text-gray-500 ml-2 capitalize">
                                  {inst.asset_class}
                                </span>
                              </div>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Bundle Selection */}
                {selectionType === 'bundle' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Bundle
                    </label>
                    {loadingBundles ? (
                      <div className="text-gray-500 py-4">Chargement des bundles...</div>
                    ) : bundles.length === 0 ? (
                      <div className="text-gray-500 py-4">
                        Aucun bundle disponible. <a href="/admin/bundles" className="text-indigo-600 hover:underline">Créez-en un</a>.
                      </div>
                    ) : (
                      <Select value={selectedBundleId} onValueChange={setSelectedBundleId}>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Sélectionner un bundle" />
                        </SelectTrigger>
                        <SelectContent>
                          {bundles.map((bundle) => (
                            <SelectItem key={bundle.id} value={bundle.id}>
                              <div className="flex items-center gap-2">
                                <Package className="w-4 h-4" />
                                <span>{bundle.name}</span>
                                <span className="text-xs text-gray-500">
                                  ({bundle.instrument_ids.length} instrument{bundle.instrument_ids.length !== 1 ? 's' : ''})
                                </span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                    {selectedBundleId && (
                      <div className="mt-2 text-sm text-gray-600">
                        Instruments dans ce bundle: {selectedInstrumentIds.length}
                      </div>
                    )}
                  </div>
                )}

                {/* Date Range */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Date de début *
                    </label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Date de fin *
                    </label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      required
                    />
                  </div>
                </div>

                {/* Strategy */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Stratégie
                  </label>
                  {selectionType === 'bundle' ? (
                    <Select
                      value={strategyType === 'bundle_strategy' || strategyType === 'CPPI' || strategyType === 'CORE_SATELLITE' ? strategyType : 'bundle_strategy'} 
                      onValueChange={(v: 'bundle_strategy' | 'CPPI' | 'CORE_SATELLITE') => {
                        setStrategyType(v)
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="bundle_strategy">Bundle Strategy</SelectItem>
                        <SelectItem value="CPPI">CPPI</SelectItem>
                        <SelectItem value="CORE_SATELLITE">Core-Satellite</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <Select value={strategyType} onValueChange={(v: 'equal_weight' | 'momentum' | 'CPPI' | 'CORE_SATELLITE') => setStrategyType(v)}>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="equal_weight">Equal Weight</SelectItem>
                        <SelectItem value="momentum">Momentum</SelectItem>
                        <SelectItem value="CPPI">CPPI</SelectItem>
                        <SelectItem value="CORE_SATELLITE">Core-Satellite</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                </div>

                {selectionType === 'bundle' && strategyType === 'bundle_strategy' && (
                  <div className="mt-1 p-2 bg-gray-100 rounded-md text-sm text-gray-700">
                    Stratégie fixée pour les bundles: utilise les allocations du bundle.
                  </div>
                )}

                {strategyType === 'momentum' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Lookback Days (1-252)
                    </label>
                    <input
                      type="number"
                      value={lookbackDays}
                      onChange={(e) => setLookbackDays(parseInt(e.target.value) || 20)}
                      min={1}
                      max={252}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                )}

                {strategyType === 'CPPI' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="block text-sm font-medium text-gray-700">
                        CPPI Parameters (JSON)
                      </label>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={useCppiDefaults}
                        className="text-xs"
                      >
                        Use defaults
                      </Button>
                    </div>
                    <textarea
                      value={cppiParamsJson}
                      onChange={(e) => {
                        setCppiParamsJson(e.target.value)
                        // Clear error on change, validation happens on blur
                        if (!e.target.value.trim()) {
                          setCppiParamsError(null)
                        }
                      }}
                      onBlur={(e) => {
                        if (e.target.value.trim()) {
                          parseCppiParams(e.target.value)
                        } else {
                          setCppiParamsError(null)
                        }
                      }}
                      placeholder={JSON.stringify(CPPI_DEFAULTS, null, 2)}
                      className={`w-full px-3 py-2 border rounded-md font-mono text-sm min-h-[200px] ${
                        cppiParamsError ? 'border-red-500' : 'border-gray-300'
                      }`}
                      rows={10}
                    />
                    {cppiParamsError && (
                      <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                        {cppiParamsError}
                      </div>
                    )}
                    <div className="text-xs text-gray-500">
                      <p className="mb-1">Parameters:</p>
                      <ul className="list-disc list-inside space-y-0.5">
                        <li><strong>floor_ratio</strong> (0-1): Floor as ratio of initial capital</li>
                        <li><strong>multiplier</strong> (&gt;=0): Multiplier for cushion</li>
                        <li><strong>risky_cap</strong> (0-1): Maximum risky weight</li>
                        <li><strong>core_min</strong> (0-1): Minimum core weight</li>
                        <li><strong>core_yield</strong> (&gt;=0): Annual yield for core sleeve</li>
                        <li><strong>day_count</strong> (int &gt;0): Days per year for accrual</li>
                      </ul>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="cppi-debug"
                        checked={cppiDebug}
                        onChange={(e) => setCppiDebug(e.target.checked)}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <label htmlFor="cppi-debug" className="text-sm font-medium text-gray-700">
                        Debug logs
                      </label>
                      <span className="text-xs text-gray-500">(Enable debug output in backtest results)</span>
                    </div>
                  </div>
                )}

                {strategyType === 'CORE_SATELLITE' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="block text-sm font-medium text-gray-700">
                        Core-Satellite Parameters (JSON)
                      </label>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={useCoreSatelliteDefaults}
                        className="text-xs"
                      >
                        Use defaults
                      </Button>
                    </div>
                    <textarea
                      value={coreSatelliteParamsJson}
                      onChange={(e) => {
                        setCoreSatelliteParamsJson(e.target.value)
                        // Clear error on change, validation happens on blur
                        if (!e.target.value.trim()) {
                          setCoreSatelliteParamsError(null)
                        }
                      }}
                      onBlur={(e) => {
                        if (e.target.value.trim()) {
                          parseCoreSatelliteParams(e.target.value)
                        } else {
                          setCoreSatelliteParamsError(null)
                        }
                      }}
                      placeholder={JSON.stringify(CORE_SATELLITE_DEFAULTS, null, 2)}
                      className={`w-full px-3 py-2 border rounded-md font-mono text-sm min-h-[200px] ${
                        coreSatelliteParamsError ? 'border-red-500' : 'border-gray-300'
                      }`}
                      rows={10}
                    />
                    {coreSatelliteParamsError && (
                      <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                        {coreSatelliteParamsError}
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="core-satellite-debug"
                        checked={coreSatelliteDebug}
                        onChange={(e) => setCoreSatelliteDebug(e.target.checked)}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <label htmlFor="core-satellite-debug" className="text-sm font-medium text-gray-700">
                        Debug logs
                      </label>
                      <span className="text-xs text-gray-500">(Enable debug output in backtest results)</span>
                    </div>
                  </div>
                )}

                {/* Rebalance */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Rebalance
                  </label>
                  <Select value={rebalance} onValueChange={(v: 'daily' | 'weekly' | 'monthly') => setRebalance(v)}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="daily">Daily</SelectItem>
                      <SelectItem value="weekly">Weekly</SelectItem>
                      <SelectItem value="monthly">Monthly</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Costs */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Fees (bps)
                    </label>
                    <input
                      type="number"
                      value={feesBps}
                      onChange={(e) => setFeesBps(parseFloat(e.target.value) || 0)}
                      min={0}
                      max={1000}
                      step={0.1}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Slippage (bps)
                    </label>
                    <input
                      type="number"
                      value={slippageBps}
                      onChange={(e) => setSlippageBps(parseFloat(e.target.value) || 0)}
                      min={0}
                      max={1000}
                      step={0.1}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                </div>

                {/* Weekend Trading */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="weekend-trading"
                    checked={allowWeekendTrading}
                    onChange={(e) => setAllowWeekendTrading(e.target.checked)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <label htmlFor="weekend-trading" className="text-sm font-medium text-gray-700">
                    Autoriser le trading le weekend
                  </label>
                </div>

                {/* Run Button */}
                <div className="pt-4 border-t">
                  <Button
                    onClick={handleRun}
                    disabled={running || (selectionType === 'instruments' && selectedInstrumentIds.length === 0) || (selectionType === 'bundle' && !selectedBundleId)}
                    className="w-full"
                    size="lg"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    {running ? 'Exécution en cours...' : 'Lancer le Backtest'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Chart and Results */}
        <div className="space-y-6">
          {loadingResults ? (
            <Card>
              <CardContent className="py-12 text-center">
                <div className="text-gray-500">Chargement des résultats...</div>
              </CardContent>
            </Card>
          ) : backtestDetail && backtestSeries ? (
            <>
              {/* Backtest Info */}
              <Card>
                <CardHeader>
                  <CardTitle>
                    {backtestDetail.run.name || `Backtest #${backtestDetail.run.id}`}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Période:</span>
                      <p className="font-medium text-xs">
                        {backtestDetail.run.effective_start_date || backtestDetail.run.start_date} - {backtestDetail.run.effective_end_date || backtestDetail.run.end_date}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-600">Stratégie:</span>
                      <p className="font-medium capitalize">{backtestDetail.run.strategy_type}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Rebalance:</span>
                      <p className="font-medium capitalize">{backtestDetail.run.rebalance}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Status:</span>
                      <p className={`font-medium ${
                        backtestDetail.run.status === 'SUCCESS' ? 'text-green-600' :
                        backtestDetail.run.status === 'FAILED' ? 'text-red-600' :
                        'text-yellow-600'
                      }`}>
                        {backtestDetail.run.status}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Chart */}
              {backtestSeries && backtestSeries.portfolio && backtestSeries.portfolio.length > 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Graphique de Performance</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <BacktestChart
                      portfolio={backtestSeries.portfolio}
                      instruments={backtestSeries.instruments || []}
                      layout="single"
                      strategyType={backtestDetail.run.strategy_type}
                      floorRatio={backtestDetail.run.strategy_params_json?.floor_ratio}
                      coreYield={backtestDetail.run.strategy_params_json?.core_yield}
                      coreDayCount={backtestDetail.run.strategy_params_json?.day_count}
                    />
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="py-12 text-center">
                    <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Aucune donnée disponible</h3>
                    <p className="text-gray-600">
                      Le backtest est en cours d'exécution ou n'a pas encore généré de données.
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* CPPI Charts - Show only if strategy is CPPI */}
              {backtestDetail.run.strategy_type === 'CPPI' && backtestSeries && backtestSeries.portfolio && backtestSeries.portfolio.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>CPPI Analytics</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CPPICharts
                      portfolio={backtestSeries.portfolio}
                      strategyParams={backtestDetail.run.strategy_params_json}
                    />
                  </CardContent>
                </Card>
              )}

              {/* Core-Satellite Charts - Show only if strategy is CORE_SATELLITE */}
              {backtestDetail.run.strategy_type === 'CORE_SATELLITE' && backtestSeries && backtestSeries.portfolio && backtestSeries.portfolio.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Core-Satellite Analytics</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CoreSatelliteCharts
                      portfolio={backtestSeries.portfolio}
                      strategyParams={backtestDetail.run.strategy_params_json}
                    />
                  </CardContent>
                </Card>
              )}

              {/* Stats */}
              {backtestDetail.portfolio_metrics && (
                <Card>
                  <CardHeader>
                    <CardTitle>Statistiques</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <BacktestStatsTable
                      portfolioMetrics={backtestDetail.portfolio_metrics}
                      instrumentMetrics={backtestDetail.instrument_metrics.map(im => ({
                        instrument_id: im.instrument_id,
                        symbol: im.symbol,
                        metrics: im.metrics,
                      }))}
                    />
                  </CardContent>
                </Card>
              )}
            </>
          ) : runId ? (
            <Card>
              <CardContent className="py-12 text-center">
                <div className="text-gray-500">Chargement des résultats du backtest...</div>
                <Button onClick={() => loadResults(runId)} className="mt-4">
                  Recharger
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Aucun résultat</h3>
                <p className="text-gray-600 mb-4">
                  Lancez un backtest pour voir les résultats ici
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
