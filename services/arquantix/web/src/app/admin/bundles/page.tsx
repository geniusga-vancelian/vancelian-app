'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { Plus, Trash2, Edit, Package } from 'lucide-react'

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
  }>
  created_at: string
  updated_at: string
}

export default function BundlesPage() {
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
  const [selectedInstrumentIds, setSelectedInstrumentIds] = useState<number[]>([])
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    // Check if user is authenticated
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          router.push('/admin/login')
          return
        }
        fetchBundles()
        fetchInstruments()
      })
      .catch(() => {
        router.push('/admin/login')
      })
  }, [router])

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

      setAvailableInstruments(data.instruments || [])
    } catch (error: any) {
      console.error('Error fetching instruments:', error)
      // If API doesn't exist yet, use empty array
      setAvailableInstruments([])
    }
  }

  const handleCreate = async () => {
    if (!newBundleName.trim()) {
      toastError('Le nom du bundle est requis')
      return
    }

    if (selectedInstrumentIds.length === 0) {
      toastError('Veuillez sélectionner au moins un instrument')
      return
    }

    setCreating(true)
    try {
      const response = await fetch('/api/bundles', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          name: newBundleName,
          description: newBundleDescription || null,
          instrument_ids: selectedInstrumentIds,
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
      setSelectedInstrumentIds([])
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
    setSelectedInstrumentIds(prev => {
      if (prev.includes(instrumentId)) {
        return prev.filter(id => id !== instrumentId)
      } else {
        return [...prev, instrumentId]
      }
    })
  }

  if (loading) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Bundles</h1>
        <div className="text-gray-500">Chargement...</div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Bundles</h1>
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
                    <div className="flex flex-wrap gap-2">
                      {bundle.instruments.map((inst) => (
                        <span
                          key={inst.id}
                          className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded"
                        >
                          {inst.symbol}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="pt-2 border-t">
                    <Link
                      href={`/admin/bundles/${bundle.id}`}
                      className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                    >
                      Voir détails →
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Bundle Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>Créer un Bundle</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nom du Bundle *
                  </label>
                  <input
                    type="text"
                    value={newBundleName}
                    onChange={(e) => setNewBundleName(e.target.value)}
                    placeholder="Ex: Crypto Portfolio, Diversified ETF..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Instruments ({selectedInstrumentIds.length} sélectionné{selectedInstrumentIds.length !== 1 ? 's' : ''})
                  </label>
                  {availableInstruments.length === 0 ? (
                    <p className="text-sm text-gray-500 py-4">
                      Aucun instrument disponible. Assurez-vous que les instruments sont créés dans Market Data.
                    </p>
                  ) : (
                    <div className="border border-gray-300 rounded-md p-4 max-h-64 overflow-y-auto">
                      <div className="space-y-2">
                        {availableInstruments.map((inst) => (
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

                <div className="flex justify-end gap-3 pt-4 border-t">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowCreateModal(false)
                      setNewBundleName('')
                      setNewBundleDescription('')
                      setSelectedInstrumentIds([])
                    }}
                  >
                    Annuler
                  </Button>
                  <Button
                    onClick={handleCreate}
                    disabled={creating || !newBundleName.trim() || selectedInstrumentIds.length === 0}
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

