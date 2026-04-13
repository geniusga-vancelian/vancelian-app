'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { InstrumentChart } from '@/components/market-data/InstrumentChart'
import { Upload, ArrowRight, RefreshCw } from 'lucide-react'

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

export default function MarketDataPage() {
  const router = useRouter()
  const [instruments, setInstruments] = useState<Instrument[]>([])
  const [loadingInstruments, setLoadingInstruments] = useState(false)
  const [selectedInstrumentId, setSelectedInstrumentId] = useState<number | null>(null)
  const [selectedInstrumentSymbol, setSelectedInstrumentSymbol] = useState<string | null>(null)
  
  // Filters state
  const [viewMode, setViewMode] = useState<'base100' | 'price'>('base100')
  const [chartType, setChartType] = useState<'line' | 'candlestick'>('line')
  
  // Default to 5 years ago to today
  const getDefaultStartDate = () => {
    const date = new Date()
    date.setFullYear(date.getFullYear() - 5)
    return date.toISOString().split('T')[0]
  }
  
  const getDefaultEndDate = () => {
    return new Date().toISOString().split('T')[0]
  }
  
  const [startDate, setStartDate] = useState<string>(getDefaultStartDate())
  const [endDate, setEndDate] = useState<string>(getDefaultEndDate())
  const [refreshKey, setRefreshKey] = useState(0)
  const [refreshing, setRefreshing] = useState(false)  

  useEffect(() => {
    // Check if user is authenticated
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          router.push('/admin/login')
        }
      })
      .catch(() => {
        router.push('/admin/login')
      })
    
    // Load instruments
    loadInstruments()
  }, [router])

  const loadInstruments = async () => {
    setLoadingInstruments(true)
    try {
      // Load all instruments (not filtered by is_active)
      const response = await fetch('/api/market-data/instruments', {
        credentials: 'include',
      })
      const data = await response.json()
      if (response.ok && data.instruments) {
        setInstruments(data.instruments)
        // Auto-select first instrument if none selected
        if (!selectedInstrumentId && data.instruments.length > 0) {
          setSelectedInstrumentId(data.instruments[0].id)
          setSelectedInstrumentSymbol(data.instruments[0].symbol)
        }
      }
    } catch (error: any) {
      console.error('Error loading instruments:', error)
      toastError('Erreur lors du chargement des instruments')
    } finally {
      setLoadingInstruments(false)
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
    
    // Dates are valid, chart will update automatically via props
  }

  const handleRefreshMarketData = async () => {
    setRefreshing(true)
    try {
      setRefreshKey((k) => k + 1)
      await loadInstruments()
      toastSuccess('Données market data rafraîchies')
    } catch {
      toastError('Erreur lors du rafraîchissement')
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Instruments Market Data</h1>
        <div className="flex items-center gap-2">
          <Button
            onClick={handleRefreshMarketData}
            variant="outline"
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh Market data
          </Button>
          <Button
            onClick={() => router.push('/admin/market-data/upload')}
            variant="default"
          >
            <Upload className="w-4 h-4 mr-2" />
            Upload Data
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>

      {/* Two-column layout: Table on left, Chart on right */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Instruments Table */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Assets ({instruments.length})</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Cliquez sur un asset pour afficher le graphique à droite.
              </p>
            </CardHeader>
            <CardContent>
              {loadingInstruments ? (
                <div className="text-center py-8 text-gray-500">Chargement...</div>
              ) : instruments.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>Aucun instrument</p>
                  <Button
                    onClick={() => router.push('/admin/market-data/upload')}
                    className="mt-4"
                    variant="outline"
                  >
                    Créer un instrument
                  </Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left">Symbole</th>
                        <th className="px-4 py-2 text-left">Nom</th>
                        <th className="px-4 py-2 text-left">Catégorie</th>
                        <th className="px-4 py-2 text-center">Weekend</th>
                        <th className="px-4 py-2 text-center">Actif</th>
                      </tr>
                    </thead>
                    <tbody>
                      {instruments.map((inst) => (
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
                          <td className={`px-4 py-2 font-mono font-semibold ${
                            selectedInstrumentId === inst.id ? 'text-white' : ''
                          }`}>{inst.symbol}</td>
                          <td className={`px-4 py-2 ${selectedInstrumentId === inst.id ? 'text-white' : ''}`}>{inst.name || '-'}</td>
                          <td className={`px-4 py-2 capitalize ${selectedInstrumentId === inst.id ? 'text-white' : ''}`}>{inst.asset_class}</td>
                          <td className={`px-4 py-2 text-center ${selectedInstrumentId === inst.id ? 'text-white' : ''}`}>
                            {inst.weekend_tradable === 'true' ? (
                              <span className={selectedInstrumentId === inst.id ? 'text-white' : 'text-green-600'}>✓</span>
                            ) : (
                              <span className={selectedInstrumentId === inst.id ? 'text-gray-200' : 'text-gray-400'}>-</span>
                            )}
                          </td>
                          <td className={`px-4 py-2 text-center ${selectedInstrumentId === inst.id ? 'text-white' : ''}`}>
                            {inst.is_active === 'true' ? (
                              <span className={selectedInstrumentId === inst.id ? 'text-white' : 'text-green-600'}>✓</span>
                            ) : (
                              <span className={selectedInstrumentId === inst.id ? 'text-gray-200' : 'text-red-600'}>✗</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Chart with Filters */}
        <div>
          <Card className="h-full flex flex-col">
            <CardHeader>
              <CardTitle>Graphique Historique</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col min-h-0">
              {/* Filters */}
              <div className="mb-6 space-y-4 border-b pb-4">
                {/* Filter 1: Base 100 or Price */}
                <div>
                  <Label htmlFor="viewMode" className="mb-2 block">Affichage</Label>
                  <Select
                    value={viewMode}
                    onValueChange={(value: 'base100' | 'price') => setViewMode(value)}
                  >
                    <SelectTrigger id="viewMode" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="base100">Base 100</SelectItem>
                      <SelectItem value="price">Prix Réel</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Filter 2: Line Chart or Candlestick */}
                <div>
                  <Label htmlFor="chartType" className="mb-2 block">Type de Graphique</Label>
                  <Select
                    value={chartType}
                    onValueChange={(value: 'line' | 'candlestick') => setChartType(value)}
                  >
                    <SelectTrigger id="chartType" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="line">Line Chart</SelectItem>
                      <SelectItem value="candlestick">Candlestick</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Filter 3: Date Range */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="startDate" className="mb-2 block">
                      Date de début *
                    </Label>
                    <Input
                      id="startDate"
                      type="date"
                      value={startDate}
                      onChange={(e) => {
                        setStartDate(e.target.value)
                      }}
                      onBlur={handleDateChange}
                      required
                      className="w-full"
                    />
                  </div>
                  <div>
                    <Label htmlFor="endDate" className="mb-2 block">
                      Date de fin *
                    </Label>
                    <Input
                      id="endDate"
                      type="date"
                      value={endDate}
                      onChange={(e) => {
                        setEndDate(e.target.value)
                      }}
                      onBlur={handleDateChange}
                      required
                      max={new Date().toISOString().split('T')[0]}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>

              {/* Chart */}
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
    </div>
  )
}
