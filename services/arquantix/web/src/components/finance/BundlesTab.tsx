'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { Plus, Trash2, Package } from 'lucide-react'

interface Bundle {
  id: string
  name: string
  description: string | null
  instrument_ids: number[]
  instruments?: Array<{
    id: number
    symbol: string
    name: string | null
    asset_class: string
    weight?: number | null
    weight_pct?: number | null
  }>
  created_at: string
  updated_at: string
}

export function BundlesTab() {
  const router = useRouter()
  const [bundles, setBundles] = useState<Bundle[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  // Create modal state
  const [newBundleName, setNewBundleName] = useState('')
  const [newBundleDescription, setNewBundleDescription] = useState('')
  const [availableInstruments, setAvailableInstruments] = useState<Array<{ id: number; symbol: string; name: string | null; asset_class: string }>>([])
  const [selectedInstruments, setSelectedInstruments] = useState<Map<number, number>>(new Map()) // Map<instrument_id, allocation_percentage>
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    console.log('[BundlesTab] Component mounted, fetching bundles...')
    fetchBundles()
    fetchInstruments()
  }, [])

  const fetchBundles = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/bundles', {
        credentials: 'include',
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || data.detail || `Failed to fetch bundles (${response.status})`)
      }

      // Backend returns array directly, but frontend API might wrap it in { bundles: [...] }
      // Handle both cases
      const bundlesArray = Array.isArray(data) ? data : (data.bundles || [])
      
      console.log('[BundlesTab] Fetched bundles:', { 
        isArray: Array.isArray(data), 
        hasBundles: !!data.bundles, 
        count: bundlesArray.length,
        bundles: bundlesArray 
      })
      
      setBundles(bundlesArray)
    } catch (error: any) {
      console.error('Error fetching bundles:', error)
      toastError(error.message || 'Failed to load bundles')
      setBundles([])
    } finally {
      setLoading(false)
    }
  }

  const fetchInstruments = async () => {
    try {
      const response = await fetch('/api/market-data/instruments?is_active=true', {
        credentials: 'include',
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch instruments')
      }

      // Handle both formats: { instruments: [...] } or array directly
      const instrumentsArray = Array.isArray(data) ? data : (data.instruments || [])
      
      setAvailableInstruments(instrumentsArray)
    } catch (error: any) {
      console.error('Error fetching instruments:', error)
      setAvailableInstruments([])
    }
  }

  const handleCreate = async () => {
    if (!newBundleName.trim()) {
      toastError('Le nom du bundle est requis')
      return
    }

    if (selectedInstruments.size === 0) {
      toastError('Veuillez sélectionner au moins un instrument')
      return
    }

    const totalAllocation = getTotalAllocation()
    if (!isAllocationValid()) {
      toastError(`L'allocation totale doit être de 100%. Actuellement: ${totalAllocation.toFixed(2)}%`)
      return
    }

    setCreating(true)
    try {
      const instrumentIds = Array.from(selectedInstruments.keys())
      
      // Convert Map to object with numeric keys for allocations
      // Note: JSON.stringify will convert numeric keys to strings, but backend handles both
      const allocationsObj: { [key: number]: number } = {}
      selectedInstruments.forEach((allocation, instrumentId) => {
        allocationsObj[instrumentId] = allocation
      })
      
      const response = await fetch('/api/bundles', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          name: newBundleName,
          description: newBundleDescription || null,
          instrument_ids: instrumentIds,
          allocations: allocationsObj, // Send allocations as { instrument_id: percentage }
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to create bundle')
      }

      toastSuccess('Bundle créé avec succès')
      setShowCreateModal(false)
      setNewBundleName('')
      setNewBundleDescription('')
      setSelectedInstruments(new Map())
      await fetchBundles()
    } catch (error: any) {
      console.error('Error creating bundle:', error)
      toastError(error.message || 'Failed to create bundle')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (bundleId: string) => {
    setDeleting(true)
    try {
      const response = await fetch(`/api/bundles/${bundleId}`, {
        method: 'DELETE',
        credentials: 'include',
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to delete bundle')
      }

      toastSuccess('Bundle supprimé avec succès')
      setShowDeleteDialog(null)
      await fetchBundles()
    } catch (error: any) {
      console.error('Error deleting bundle:', error)
      toastError(error.message || 'Failed to delete bundle')
    } finally {
      setDeleting(false)
    }
  }

  const toggleInstrument = (instrumentId: number) => {
    setSelectedInstruments(prev => {
      const newMap = new Map(prev)
      if (newMap.has(instrumentId)) {
        newMap.delete(instrumentId)
      } else {
        // Add instrument with 0 allocation (will need to be set by user)
        newMap.set(instrumentId, 0)
      }
      return newMap
    })
  }

  const updateAllocation = (instrumentId: number, allocation: number) => {
    setSelectedInstruments(prev => {
      const newMap = new Map(prev)
      // Ensure allocation is between 0 and 100
      const validAllocation = Math.max(0, Math.min(100, allocation))
      newMap.set(instrumentId, validAllocation)
      return newMap
    })
  }

  const getTotalAllocation = (): number => {
    let total = 0
    selectedInstruments.forEach((allocation) => {
      total += allocation
    })
    return total
  }

  const isAllocationValid = (): boolean => {
    const total = getTotalAllocation()
    return Math.abs(total - 100) < 0.01 // Allow small floating point errors
  }

  if (loading) {
    return (
      <div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-6">Bundles</h2>
        <div className="text-gray-500">Chargement...</div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Bundles</h2>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Créer un Bundle
        </Button>
      </div>

      {bundles.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Aucun bundle</h3>
            <p className="text-gray-600 mb-4">
              Créez votre premier bundle pour grouper des instruments ensemble
            </p>
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Créer un Bundle
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {bundles.map((bundle) => (
            <Card key={bundle.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg mb-1">{bundle.name}</CardTitle>
                    {bundle.description && (
                      <p className="text-sm text-gray-600 mt-1">{bundle.description}</p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowDeleteDialog(bundle.id)}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-sm">
                    <span className="font-medium text-gray-700">
                      {bundle.instruments?.length || bundle.instrument_ids.length} instrument{bundle.instruments?.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  {bundle.instruments && bundle.instruments.length > 0 && (
                    <div className="space-y-3">
                      {/* Allocation */}
                      <div>
                        <div className="text-xs font-medium text-gray-600 uppercase tracking-wide mb-2">
                          Allocation
                        </div>
                        <div className="space-y-1.5">
                          {bundle.instruments.map((inst) => {
                            const weight = inst.weight_pct !== null && inst.weight_pct !== undefined 
                              ? inst.weight_pct 
                              : (inst.weight !== null && inst.weight !== undefined ? inst.weight : null)
                            
                            return (
                              <div
                                key={inst.id}
                                className="flex items-center justify-between text-sm py-1"
                              >
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-gray-900">{inst.symbol}</span>
                                  {inst.name && (
                                    <span className="text-xs text-gray-500">({inst.name})</span>
                                  )}
                                </div>
                                {weight !== null ? (
                                  <span className="font-semibold text-indigo-600">
                                    {weight.toFixed(1)}%
                                  </span>
                                ) : (
                                  <span className="text-xs text-gray-400">—</span>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                      {/* Composition (tags) */}
                      <div className="pt-2 border-t">
                        <div className="text-xs font-medium text-gray-600 uppercase tracking-wide mb-2">
                          Composition
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {bundle.instruments.map((inst) => (
                            <span
                              key={inst.id}
                              className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded capitalize"
                            >
                              {inst.symbol}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Bundle Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-white">
            <CardHeader className="bg-white border-b">
              <CardTitle className="text-xl font-semibold text-gray-900">Créer un Bundle</CardTitle>
            </CardHeader>
            <CardContent className="bg-white">
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nom du Bundle *
                  </label>
                  <input
                    type="text"
                    value={newBundleName}
                    onChange={(e) => setNewBundleName(e.target.value)}
                    placeholder="Ex: Crypto Portfolio, Diversified ETF..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description (optionnel)
                  </label>
                  <textarea
                    value={newBundleDescription}
                    onChange={(e) => setNewBundleDescription(e.target.value)}
                    placeholder="Description du bundle..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Instruments et Allocations ({selectedInstruments.size} sélectionné{selectedInstruments.size !== 1 ? 's' : ''})
                  </label>
                  {availableInstruments.length === 0 ? (
                    <p className="text-sm text-gray-500 py-4">
                      Aucun instrument disponible. Assurez-vous que les instruments sont créés dans Market Data.
                    </p>
                  ) : (
                    <div className="border border-gray-300 rounded-md bg-white">
                      <div className="space-y-2 p-4 max-h-96 overflow-y-auto">
                        {availableInstruments.map((inst) => {
                          const isSelected = selectedInstruments.has(inst.id)
                          const allocation = selectedInstruments.get(inst.id) || 0
                          
                          return (
                            <div
                              key={inst.id}
                              className={`p-3 rounded-md border ${isSelected ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 bg-white'}`}
                            >
                              <div className="flex items-center gap-3">
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleInstrument(inst.id)}
                                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                />
                                <div className="flex-1">
                                  <span className="font-medium text-gray-900">{inst.symbol}</span>
                                  {inst.name && (
                                    <span className="text-sm text-gray-600 ml-2">({inst.name})</span>
                                  )}
                                  <span className="text-xs text-gray-500 ml-2 capitalize">
                                    {inst.asset_class}
                                  </span>
                                </div>
                                {isSelected && (
                                  <div className="flex items-center gap-2">
                                    <label className="text-sm text-gray-700 whitespace-nowrap">
                                      Allocation (%):
                                    </label>
                                    <input
                                      type="number"
                                      min="0"
                                      max="100"
                                      step="0.1"
                                      value={allocation}
                                      onChange={(e) => updateAllocation(inst.id, parseFloat(e.target.value) || 0)}
                                      className="w-20 px-2 py-1 border border-gray-300 rounded-md bg-white text-gray-900 text-sm"
                                      placeholder="0"
                                    />
                                    <span className="text-sm text-gray-600">%</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                      {selectedInstruments.size > 0 && (
                        <div className="border-t border-gray-300 p-4 bg-gray-50">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-gray-700">
                              Allocation totale:
                            </span>
                            <span className={`text-lg font-semibold ${isAllocationValid() ? 'text-green-600' : 'text-red-600'}`}>
                              {getTotalAllocation().toFixed(2)}%
                            </span>
                          </div>
                          {!isAllocationValid() && (
                            <p className="text-sm text-red-600 mt-2">
                              L'allocation totale doit être exactement de 100%. 
                              Il manque {Math.abs(100 - getTotalAllocation()).toFixed(2)}% pour atteindre 100%.
                            </p>
                          )}
                          {isAllocationValid() && (
                            <p className="text-sm text-green-600 mt-2">
                              ✓ L'allocation totale est de 100%. Vous pouvez valider le bundle.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowCreateModal(false)
                      setNewBundleName('')
                      setNewBundleDescription('')
                      setSelectedInstruments(new Map())
                    }}
                  >
                    Annuler
                  </Button>
                  <Button
                    onClick={handleCreate}
                    disabled={creating || !newBundleName.trim() || selectedInstruments.size === 0 || !isAllocationValid()}
                    className={!isAllocationValid() ? 'opacity-50 cursor-not-allowed' : ''}
                  >
                    {creating ? 'Création...' : 'Créer Bundle'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={!!showDeleteDialog}
        onOpenChange={(open) => !open && setShowDeleteDialog(null)}
        onConfirm={async () => {
          if (showDeleteDialog) {
            await handleDelete(showDeleteDialog)
          }
        }}
        title="Supprimer le Bundle"
        description="Êtes-vous sûr de vouloir supprimer ce bundle ? Cette action est irréversible."
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        destructive={true}
      />
    </div>
  )
}

