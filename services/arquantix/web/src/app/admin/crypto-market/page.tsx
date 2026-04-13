'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { InstrumentChart } from '@/components/market-data/InstrumentChart'
import { Switch } from '@/components/ui/switch'
import { RefreshCw } from 'lucide-react'

const LIVE_PRICE_INTERVAL_MS = 1000
const CURRENCY_SYMBOL = '$'

interface Instrument {
  id: number
  symbol: string
  name: string | null
  asset_class: string
  weekend_tradable: string
  provider: string
  provider_symbol: string | null
  is_active: string
  created_at: string | null
}

interface HoleInfo {
  start_datetime: string | null
  end_datetime: string | null
  bar_count?: number
  expected_bar_count?: number
  consistency_note?: string
  holes: Array<{ start: string; end: string }>
  current_datetime_utc?: string | null
  missing_bars_to_now?: number | null
  lag_note?: string
}

interface OhlcHolesRow {
  instrument_id: number
  symbol: string
  M5: HoleInfo
  H1: HoleInfo
  H4: HoleInfo
  D1: HoleInfo
  W1: HoleInfo
}

export default function CryptoMarketPage() {
  const router = useRouter()
  const [instruments, setInstruments] = useState<Instrument[]>([])
  const [loadingInstruments, setLoadingInstruments] = useState(false)
  const [selectedInstrumentId, setSelectedInstrumentId] = useState<number | null>(null)
  const [selectedInstrumentSymbol, setSelectedInstrumentSymbol] = useState<string | null>(null)

  const [viewMode, setViewMode] = useState<'base100' | 'price'>('base100')
  const [chartType, setChartType] = useState<'line' | 'candlestick'>('line')

  const getDefaultStartDate = () => {
    const date = new Date()
    date.setFullYear(date.getFullYear() - 2)
    return date.toISOString().split('T')[0]
  }
  const getDefaultEndDate = () => new Date().toISOString().split('T')[0]

  const [startDate, setStartDate] = useState<string>(getDefaultStartDate())
  const [endDate, setEndDate] = useState<string>(getDefaultEndDate())
  const [refreshKey, setRefreshKey] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const [pricesByInstrumentId, setPricesByInstrumentId] = useState<Record<number, number>>({})
  const [ohlcHolesByInstrumentId, setOhlcHolesByInstrumentId] = useState<Record<number, OhlcHolesRow>>({})
  const [loadingHoles, setLoadingHoles] = useState(false)
  const [lastDownloadSummary, setLastDownloadSummary] = useState<Array<{ instrument_id: number; provider_symbol: string; bars_by_period: Record<string, number> }> | null>(null)
  const [lastHolesSummary, setLastHolesSummary] = useState<{ total_holes_remaining: number; total_missing_bars_to_now_remaining: number; message: string } | null>(null)
  const [cronRefreshEnabled, setCronRefreshEnabled] = useState(true)
  const [cronLogs, setCronLogs] = useState<Array<{ datetime: string; job: string; bars_by_asset_period: unknown }>>([])
  const livePriceIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) router.push('/admin/login')
      })
      .catch(() => router.push('/admin/login'))

    loadInstruments()
    fetch('/api/market-data/cron-refresh-status', { credentials: 'include' })
      .then((r) => r.json())
      .then((data) => {
        if (typeof data.enabled === 'boolean') setCronRefreshEnabled(data.enabled)
      })
      .catch(() => {})

    const loadLogs = () => {
      fetch('/api/market-data/cron-refresh-logs?limit=100', { credentials: 'include' })
        .then((r) => r.json())
        .then((data) => {
          if (Array.isArray(data.logs)) setCronLogs(data.logs)
        })
        .catch(() => {})
    }
    loadLogs()
    const logInterval = setInterval(loadLogs, 30000)
    return () => clearInterval(logInterval)
  }, [router])

  const instrumentsRef = useRef<Instrument[]>([])
  instrumentsRef.current = instruments

  const fetchLivePrices = async () => {
    const list = instrumentsRef.current
    if (list.length === 0) return
    const symbols = list
      .map((i) => i.provider_symbol)
      .filter((s): s is string => !!s?.trim())
    if (symbols.length === 0) return
    try {
      const res = await fetch(
        `/api/market-data/market-summary?symbols=${encodeURIComponent(symbols.join(','))}`,
        { credentials: 'include', cache: 'no-store' }
      )
      if (!res.ok) return
      const data = await res.json()
      const summaries = data.summaries as Array<{ instrument_id: number; price: number }> | undefined
      if (!Array.isArray(summaries)) return
      const next: Record<number, number> = {}
      for (const s of summaries) {
        if (typeof s.instrument_id === 'number' && typeof s.price === 'number') {
          next[s.instrument_id] = s.price
        }
      }
      setPricesByInstrumentId((prev) => (Object.keys(next).length ? next : prev))
    } catch {
      // ignore network errors for live ticker
    }
  }

  useEffect(() => {
    if (instruments.length === 0) return
    fetchLivePrices()
    livePriceIntervalRef.current = setInterval(fetchLivePrices, LIVE_PRICE_INTERVAL_MS)
    return () => {
      if (livePriceIntervalRef.current) {
        clearInterval(livePriceIntervalRef.current)
        livePriceIntervalRef.current = null
      }
    }
  }, [instruments.length])

  const loadInstruments = async (): Promise<Instrument[]> => {
    setLoadingInstruments(true)
    try {
      const response = await fetch(
        '/api/market-data/instruments?asset_class=crypto&provider=binance',
        { credentials: 'include' }
      )
      const data = await response.json()
      if (response.ok && data.instruments) {
        const list = data.instruments as Instrument[]
        setInstruments(list)
        if (!selectedInstrumentId && list.length > 0) {
          setSelectedInstrumentId(list[0].id)
          setSelectedInstrumentSymbol(list[0].symbol)
        }
        return list
      }
      return []
    } catch (error: any) {
      console.error('Error loading crypto instruments:', error)
      toastError('Erreur lors du chargement des assets crypto')
      return []
    } finally {
      setLoadingInstruments(false)
    }
  }

  const handleCronRefreshChange = async (enabled: boolean) => {
    setCronRefreshEnabled(enabled)
    try {
      const res = await fetch('/api/market-data/cron-refresh-status', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
      if (!res.ok) {
        setCronRefreshEnabled(!enabled)
        toastError('Impossible de modifier le cron')
        return
      }
      toastSuccess(enabled ? 'Cron Refresh Data activé (toutes les minutes)' : 'Cron Refresh Data désactivé')
    } catch {
      setCronRefreshEnabled(!enabled)
      toastError('Erreur réseau')
    }
  }

  const handleSelectInstrument = (instrument: Instrument) => {
    setSelectedInstrumentId(instrument.id)
    setSelectedInstrumentSymbol(instrument.symbol)
  }

  const handleDateChange = () => {
    if (!startDate || !endDate) {
      toastError('Les dates de début et de fin sont obligatoires')
      return
    }
    if (new Date(startDate) > new Date(endDate)) {
      toastError('La date de début doit être antérieure à la date de fin')
      return
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      setLastHolesSummary(null)
      const backfillRes = await fetch('/api/market-data/backfill-lag', {
        method: 'POST',
        credentials: 'include',
      })
      const backfillData = await backfillRes.json()
      if (!backfillRes.ok) {
        toastError(backfillData.error || backfillData.detail || 'Erreur backfill barres en retard')
        return
      }
      setLastDownloadSummary(backfillData.download_summary ?? null)
      setLastHolesSummary(backfillData.summary ?? null)
      const summary = backfillData.summary as { total_holes_remaining?: number; total_missing_bars_to_now_remaining?: number; message?: string } | undefined
      const totalHoles = summary?.total_holes_remaining ?? 0
      const totalMissing = summary?.total_missing_bars_to_now_remaining ?? 0
      if (totalHoles === 0 && totalMissing === 0) {
        toastSuccess('Refresh terminé. Trous restants : 0 (OK).')
      } else {
        toastError(summary?.message ?? `Trous restants : ${totalHoles} lacunes, ${totalMissing} barres en retard`)
      }
      const dlSummary = backfillData.download_summary as Array<{ bars_by_period?: Record<string, number> }> | undefined
      if (Array.isArray(dlSummary) && dlSummary.some((s) => Object.values(s.bars_by_period ?? {}).some((n) => n > 0))) {
        toastSuccess('Barres manquantes téléchargées (uniquement les besoins détectés).')
      }
      if (Array.isArray(backfillData.holes_analysis_after)) {
        const byId: Record<number, OhlcHolesRow> = {}
        for (const row of backfillData.holes_analysis_after as OhlcHolesRow[]) {
          byId[row.instrument_id] = row
        }
        setOhlcHolesByInstrumentId(byId)
      }
      setRefreshKey((k) => k + 1)
      await loadInstruments()
    } catch (e: any) {
      toastError(e?.message || 'Erreur lors du rafraîchissement')
    } finally {
      setRefreshing(false)
    }
  }


  const loadOhlcHoles = async () => {
    if (instruments.length === 0) {
      toastError('Chargez d’abord les assets')
      return
    }
    setLoadingHoles(true)
    try {
      const ids = instruments.map((i) => i.id).join(',')
      const res = await fetch(`/api/market-data/ohlc-holes?instrument_ids=${encodeURIComponent(ids)}`, {
        credentials: 'include',
      })
      const data = await res.json()
      if (!res.ok) {
        toastError(data.error || 'Erreur lors du chargement des trous OHLC')
        return
      }
      const rows = (data.data || []) as OhlcHolesRow[]
      const byId: Record<number, OhlcHolesRow> = {}
      for (const row of rows) {
        byId[row.instrument_id] = row
      }
      setOhlcHolesByInstrumentId(byId)
      toastSuccess('Trous OHLC mis à jour')
    } catch (e: any) {
      toastError(e?.message || 'Erreur lors du chargement des trous OHLC')
    } finally {
      setLoadingHoles(false)
    }
  }

  function formatHoleCell(info: HoleInfo): string {
    if (!info) return '—'
    const start = info.start_datetime ?? '—'
    const end = info.end_datetime ?? '—'
    const barCount = info.bar_count ?? '—'
    const expected = info.expected_bar_count ?? '—'
    const consistency = info.consistency_note ?? '—'
    const holesJson = JSON.stringify(info.holes ?? [])
    const nowUtc = info.current_datetime_utc ?? '—'
    const missingToNow = info.missing_bars_to_now ?? '—'
    const lag = info.lag_note ?? '—'
    return [
      `Starting datetime: ${start}`,
      `End datetime: ${end}`,
      `Barres en mémoire: ${barCount}`,
      `Barres attendues (plage × timeframe): ${expected}`,
      `Cohérence: ${consistency}`,
      `Datetime courante (UTC): ${nowUtc}`,
      `Barres manquantes (dernière barre → maintenant): ${missingToNow}`,
      `Retard: ${lag}`,
      `Holes: ${holesJson}`,
    ].join('\n')
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-3xl font-bold text-gray-900">Crypto market</h1>
        <div className="flex gap-2">
          <Button
            onClick={loadOhlcHoles}
            variant="outline"
            disabled={loadingHoles || instruments.length === 0}
          >
            {loadingHoles ? 'Vérification…' : 'Vérifier les trous OHLC'}
          </Button>
          <Button
            onClick={handleRefresh}
            variant="outline"
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      <Card className="mb-6 p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Label htmlFor="cron-refresh" className="text-base font-semibold text-gray-900 whitespace-nowrap">
              Cron Refresh Data
            </Label>
            <Switch
              id="cron-refresh"
              checked={cronRefreshEnabled}
              onCheckedChange={handleCronRefreshChange}
              className="data-[state=checked]:bg-green-600 data-[state=unchecked]:bg-gray-300"
            />
          </div>
          <span className="text-sm text-muted-foreground">
            {cronRefreshEnabled ? 'Actif — le cron tourne toutes les minutes.' : 'Inactif — le cron ne tourne pas.'}
          </span>
        </div>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Log des exécutions du cron</CardTitle>
          <p className="text-sm text-muted-foreground">
            Dernières exécutions (Datetime, Job, NB bars ajouté par Asset et période OHLC).
          </p>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left p-3 font-medium">Datetime</th>
                  <th className="text-left p-3 font-medium">Job réalisé</th>
                  <th className="text-left p-3 font-medium">NB bars ajouté par Asset et période OHLC (JSON)</th>
                </tr>
              </thead>
              <tbody>
                {cronLogs.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="p-4 text-muted-foreground text-center">
                      Aucun log pour l’instant.
                    </td>
                  </tr>
                ) : (
                  [...cronLogs].reverse().map((log, idx) => (
                    <tr key={`${log.datetime}-${idx}`} className="border-b last:border-0">
                      <td className="p-3 whitespace-nowrap">{log.datetime}</td>
                      <td className="p-3">{log.job}</td>
                      <td className="p-3 font-mono text-xs max-w-md overflow-x-auto">
                        {Array.isArray(log.bars_by_asset_period) && log.bars_by_asset_period.length > 0
                          ? JSON.stringify(log.bars_by_asset_period)
                          : '[]'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Crypto assets table */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Assets crypto ({instruments.length})</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Cliquez sur un asset pour afficher le graphique à droite.
              </p>
            </CardHeader>
            <CardContent>
              {loadingInstruments ? (
                <div className="text-center py-8 text-gray-500">Chargement...</div>
              ) : instruments.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  Aucun asset crypto configuré.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left">Symbole</th>
                        <th className="px-4 py-2 text-left">Nom</th>
                        <th className="px-4 py-2 text-right">Prix (temps réel)</th>
                        <th className="px-4 py-2 text-left">Provider</th>
                        <th className="px-4 py-2 text-center">Actif</th>
                        <th className="px-4 py-2 text-left whitespace-nowrap">M5</th>
                        <th className="px-4 py-2 text-left whitespace-nowrap">H1</th>
                        <th className="px-4 py-2 text-left whitespace-nowrap">H4</th>
                        <th className="px-4 py-2 text-left whitespace-nowrap">D1</th>
                        <th className="px-4 py-2 text-left whitespace-nowrap">W1</th>
                      </tr>
                    </thead>
                    <tbody>
                      {instruments.map((inst) => {
                        const price = pricesByInstrumentId[inst.id]
                        const priceFormatted =
                          price != null
                            ? new Intl.NumberFormat('fr-FR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              }).format(price) + ` ${CURRENCY_SYMBOL}`
                            : '—'
                        return (
                          <tr
                            key={inst.id}
                            onClick={() => handleSelectInstrument(inst)}
                            className={`border-t cursor-pointer transition-colors ${
                              selectedInstrumentId === inst.id
                                ? 'bg-indigo-600 text-white'
                                : inst.is_active === 'false'
                                ? 'bg-gray-100 opacity-60'
                                : 'hover:bg-gray-50'
                            }`}
                          >
                            <td className={`px-4 py-2 font-mono font-semibold ${selectedInstrumentId === inst.id ? 'text-white' : ''}`}>
                              {inst.symbol}
                            </td>
                            <td className={`px-4 py-2 ${selectedInstrumentId === inst.id ? 'text-white' : ''}`}>
                              {inst.name || inst.provider_symbol || '-'}
                            </td>
                            <td className={`px-4 py-2 text-right font-mono tabular-nums ${selectedInstrumentId === inst.id ? 'text-white' : ''}`}>
                              {priceFormatted}
                            </td>
                            <td className={`px-4 py-2 capitalize ${selectedInstrumentId === inst.id ? 'text-white' : ''}`}>
                              {inst.provider}
                            </td>
                            <td className={`px-4 py-2 text-center ${selectedInstrumentId === inst.id ? 'text-white' : ''}`}>
                              {inst.is_active === 'true' ? (
                                <span className={selectedInstrumentId === inst.id ? 'text-white' : 'text-green-600'}>✓</span>
                              ) : (
                                <span className={selectedInstrumentId === inst.id ? 'text-gray-200' : 'text-red-600'}>✗</span>
                              )}
                            </td>
                            {(['M5', 'H1', 'H4', 'D1', 'W1'] as const).map((period) => {
                              const row = ohlcHolesByInstrumentId[inst.id]
                              const info = row?.[period]
                              const text = info ? formatHoleCell(info) : '—'
                              return (
                                <td
                                  key={period}
                                  className={`px-4 py-2 text-left text-xs max-w-[220px] ${selectedInstrumentId === inst.id ? 'text-white' : ''}`}
                                  title={text}
                                >
                                  <pre className="whitespace-pre-wrap break-words font-sans m-0">{text}</pre>
                                </td>
                              )
                            })}
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Chart */}
        <div>
          <Card className="h-full flex flex-col">
            <CardHeader>
              <CardTitle>Graphique historique</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col min-h-0">
              <div className="mb-6 space-y-4 border-b pb-4">
                <div>
                  <Label htmlFor="viewMode" className="mb-2 block">Affichage</Label>
                  <Select value={viewMode} onValueChange={(v: 'base100' | 'price') => setViewMode(v)}>
                    <SelectTrigger id="viewMode" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="base100">Base 100</SelectItem>
                      <SelectItem value="price">Prix réel</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="chartType" className="mb-2 block">Type de graphique</Label>
                  <Select value={chartType} onValueChange={(v: 'line' | 'candlestick') => setChartType(v)}>
                    <SelectTrigger id="chartType" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="line">Line Chart</SelectItem>
                      <SelectItem value="candlestick">Candlestick</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="startDate" className="mb-2 block">Date de début *</Label>
                    <Input
                      id="startDate"
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      onBlur={handleDateChange}
                      required
                      className="w-full"
                    />
                  </div>
                  <div>
                    <Label htmlFor="endDate" className="mb-2 block">Date de fin *</Label>
                    <Input
                      id="endDate"
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      onBlur={handleDateChange}
                      required
                      max={getDefaultEndDate()}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>

              <div className="flex-1 min-h-0" style={{ minHeight: '400px' }}>
                {selectedInstrumentId && selectedInstrumentSymbol ? (
                  <InstrumentChart
                    instrumentId={selectedInstrumentId}
                    instrumentSymbol={selectedInstrumentSymbol}
                    startDate={startDate}
                    endDate={endDate}
                    viewMode={viewMode}
                    chartType={chartType}
                    refreshKey={refreshKey}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full min-h-[400px] rounded border border-dashed border-gray-300 bg-gray-50/50 text-gray-500">
                    <p className="text-center px-4">
                      Sélectionnez un asset dans le tableau à gauche pour afficher le graphique historique.
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {(lastDownloadSummary !== null || lastHolesSummary !== null) && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Résultat du dernier Refresh</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Analyse des trous restants (normalement 0) et barres téléchargées par asset/période.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {lastHolesSummary !== null && (
              <div className="rounded-md border bg-muted/50 p-4">
                <h4 className="font-medium mb-2">Trous restants après Refresh</h4>
                <pre className="text-sm whitespace-pre-wrap">
                  {JSON.stringify(lastHolesSummary, null, 2)}
                </pre>
                {lastHolesSummary.total_holes_remaining === 0 && lastHolesSummary.total_missing_bars_to_now_remaining === 0 && (
                  <p className="mt-2 text-green-600 font-medium">Aucun trou restant (OK).</p>
                )}
              </div>
            )}
            {lastDownloadSummary !== null && (
              <>
                <Label className="text-muted-foreground">Barres téléchargées (JSON)</Label>
                <textarea
                  readOnly
                  className="w-full min-h-[200px] max-h-[400px] p-4 font-mono text-sm bg-gray-50 border rounded-md resize-y"
                  value={JSON.stringify(lastDownloadSummary, null, 2)}
                  spellCheck={false}
                />
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
