'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { MultiBacktestChart } from '@/components/backtests/MultiBacktestChart'
import { BacktestListResponse, BacktestCompareResponse, BacktestRunListItem } from '@/components/backtests/types'
import { Search, Play, ExternalLink } from 'lucide-react'

export default function CompareBacktestsPage() {
  const router = useRouter()

  // State
  const [runs, setRuns] = useState<BacktestRunListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [selectedRunIds, setSelectedRunIds] = useState<Set<number>>(new Set())
  const [compareData, setCompareData] = useState<BacktestCompareResponse | null>(null)
  const [loadingCompare, setLoadingCompare] = useState(false)
  const [alignMode, setAlignMode] = useState<'intersection' | 'union'>('intersection')

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [strategyFilter, setStrategyFilter] = useState<string>('')
  const [limit] = useState(50)
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    // Check authentication
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          router.push('/admin/login')
          return
        }
        loadRuns()
      })
      .catch(() => {
        router.push('/admin/login')
      })
  }, [router, statusFilter, strategyFilter, searchQuery, offset])

  const loadRuns = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (statusFilter) params.append('status', statusFilter)
      if (strategyFilter) params.append('strategy_type', strategyFilter)
      if (searchQuery) params.append('q', searchQuery)
      params.append('limit', limit.toString())
      params.append('offset', offset.toString())

      const response = await fetch(`/api/backtests?${params.toString()}`, {
        credentials: 'include',
      })

      if (!response.ok) {
        const errorData = await response.json()
        toastError(`Erreur lors du chargement: ${errorData.error || 'Unknown error'}`)
        return
      }

      const data: BacktestListResponse = await response.json()
      setRuns(data.runs)
      setTotal(data.total)
    } catch (error: any) {
      console.error('Error loading runs:', error)
      toastError(`Erreur: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const toggleRunSelection = (runId: number) => {
    setSelectedRunIds(prev => {
      const next = new Set(prev)
      if (next.has(runId)) {
        next.delete(runId)
      } else {
        if (next.size >= 10) {
          toastError('Maximum 10 backtests sélectionnables')
          return prev
        }
        next.add(runId)
      }
      return next
    })
  }

  const handleCompare = async () => {
    if (selectedRunIds.size === 0) {
      toastError('Veuillez sélectionner au moins un backtest')
      return
    }

    setLoadingCompare(true)
    try {
      const response = await fetch('/api/backtests/compare', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          run_ids: Array.from(selectedRunIds),
          align_mode: alignMode,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        toastError(`Erreur lors de la comparaison: ${errorData.error || 'Unknown error'}`)
        return
      }

      const data: BacktestCompareResponse = await response.json()
      setCompareData(data)
      toastSuccess('Comparaison effectuée avec succès')
    } catch (error: any) {
      console.error('Error comparing runs:', error)
      toastError(`Erreur: ${error.message}`)
    } finally {
      setLoadingCompare(false)
    }
  }

  const handleOpenRun = (runId: number) => {
    // Navigate to backtests page (existing page) - we'll need to check if it supports viewing a specific run
    // For now, just navigate to the backtests page
    router.push(`/admin/backtests?run_id=${runId}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Comparer des Backtests</h1>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Backtests Library */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Bibliothèque de Backtests</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Search */}
              <div>
                <Label htmlFor="search">Rechercher</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    id="search"
                    placeholder="Nom ou ID..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              {/* Filters */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="status-filter">Statut</Label>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger id="status-filter">
                      <SelectValue placeholder="Tous" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Tous</SelectItem>
                      <SelectItem value="SUCCESS">Success</SelectItem>
                      <SelectItem value="FAILED">Failed</SelectItem>
                      <SelectItem value="PENDING">Pending</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="strategy-filter">Stratégie</Label>
                  <Select value={strategyFilter} onValueChange={setStrategyFilter}>
                    <SelectTrigger id="strategy-filter">
                      <SelectValue placeholder="Tous" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Tous</SelectItem>
                      <SelectItem value="equal_weight">Equal Weight</SelectItem>
                      <SelectItem value="momentum">Momentum</SelectItem>
                      <SelectItem value="bundle_strategy">Bundle Strategy</SelectItem>
                      <SelectItem value="CPPI">CPPI</SelectItem>
                      <SelectItem value="CORE_SATELLITE">Core-Satellite</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Selected count */}
              {selectedRunIds.size > 0 && (
                <div className="text-sm text-gray-600 bg-blue-50 p-2 rounded">
                  {selectedRunIds.size} backtest{selectedRunIds.size > 1 ? 's' : ''} sélectionné{selectedRunIds.size > 1 ? 's' : ''} (max 10)
                </div>
              )}

              {/* Compare button */}
              <Button
                onClick={handleCompare}
                disabled={selectedRunIds.size === 0 || loadingCompare}
                className="w-full"
                size="lg"
              >
                <Play className="w-4 h-4 mr-2" />
                {loadingCompare ? 'Comparaison en cours...' : 'Comparer'}
              </Button>

              {/* Align mode toggle */}
              <div className="flex items-center gap-2">
                <Label htmlFor="align-mode">Mode d'alignement:</Label>
                <Select value={alignMode} onValueChange={(v: 'intersection' | 'union') => setAlignMode(v)}>
                  <SelectTrigger id="align-mode" className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="intersection">Intersection</SelectItem>
                    <SelectItem value="union">Union</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Runs list */}
              <div className="border border-gray-300 rounded-md max-h-[600px] overflow-y-auto">
                {loading ? (
                  <div className="p-4 text-center text-gray-500">Chargement...</div>
                ) : runs.length === 0 ? (
                  <div className="p-4 text-center text-gray-500">Aucun backtest trouvé</div>
                ) : (
                  <div className="divide-y divide-gray-200">
                    {runs.map((run) => (
                      <label
                        key={run.id}
                        className="flex items-start gap-3 p-3 hover:bg-gray-50 cursor-pointer"
                      >
                        <Checkbox
                          checked={selectedRunIds.has(run.id)}
                          onCheckedChange={() => toggleRunSelection(run.id)}
                          disabled={!selectedRunIds.has(run.id) && selectedRunIds.size >= 10}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-sm">{run.name}</span>
                            <span className={`text-xs px-2 py-1 rounded ${
                              run.status === 'SUCCESS' ? 'bg-green-100 text-green-800' :
                              run.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                              'bg-yellow-100 text-yellow-800'
                            }`}>
                              {run.status}
                            </span>
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            <div>Stratégie: <span className="capitalize">{run.strategy_type}</span></div>
                            <div>Période: {run.start_date} - {run.end_date}</div>
                            {run.universe_label && (
                              <div>Univers: {run.universe_label}</div>
                            )}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Pagination */}
              {total > limit && (
                <div className="flex items-center justify-between text-sm">
                  <div className="text-gray-600">
                    {offset + 1}-{Math.min(offset + limit, total)} sur {total}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setOffset(Math.max(0, offset - limit))}
                      disabled={offset === 0}
                    >
                      Précédent
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setOffset(offset + limit)}
                      disabled={offset + limit >= total}
                    >
                      Suivant
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Comparison Results */}
        <div className="space-y-6">
          {compareData ? (
            <>
              {/* Chart */}
              <Card>
                <CardHeader>
                  <CardTitle>Comparaison NAV (base100)</CardTitle>
                </CardHeader>
                <CardContent>
                  <MultiBacktestChart data={compareData} />
                </CardContent>
              </Card>

              {/* Stats Table */}
              <Card>
                <CardHeader>
                  <CardTitle>Statistiques Comparatives</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nom</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stratégie</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Univers</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Perf. Annuelle</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Max DD</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Sharpe</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Calmar</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {Object.entries(compareData.runs).map(([runId, runMeta]) => {
                          const stats = compareData.stats[runId]
                          return (
                            <tr key={runId}>
                              <td className="px-4 py-3 text-sm font-medium text-gray-900">{runMeta.name}</td>
                              <td className="px-4 py-3 text-sm text-gray-700 capitalize">{runMeta.strategy_type}</td>
                              <td className="px-4 py-3 text-sm text-gray-700">{runMeta.universe_label || '-'}</td>
                              <td className="px-4 py-3 text-sm text-gray-700 text-right">
                                {stats ? (stats.annualized_performance * 100).toFixed(2) + '%' : '-'}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-700 text-right">
                                {stats ? (stats.max_drawdown * 100).toFixed(2) + '%' : '-'}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-700 text-right">
                                {stats ? stats.sharpe_ratio.toFixed(2) : '-'}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-700 text-right">
                                {stats && stats.calmar_ratio != null ? stats.calmar_ratio.toFixed(2) : '-'}
                              </td>
                              <td className="px-4 py-3 text-sm text-center">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleOpenRun(parseInt(runId))}
                                >
                                  <ExternalLink className="w-4 h-4" />
                                </Button>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-gray-500">Sélectionnez des backtests pour comparer</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
