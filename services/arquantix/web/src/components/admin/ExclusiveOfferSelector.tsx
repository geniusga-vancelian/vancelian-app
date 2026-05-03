'use client'

import { useState, useEffect } from 'react'
import { X, Search, GripVertical } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ExclusiveOfferListItem {
  packagedProductId: string
  slug: string
  page: {
    id: string
    slug: string
    title: string | null
    urlPath: string
  } | null
  tags: string[]
  lendingSnapshot: {
    currentRaised: string | null
    targetSize: string | null
  } | null
}

interface ExclusiveOfferSelectorProps {
  selectedPackagedProductIds: string[]
  onChange: (ids: string[]) => void
  limit?: number
}

export function ExclusiveOfferSelector({
  selectedPackagedProductIds,
  onChange,
  limit = 3,
}: ExclusiveOfferSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [items, setItems] = useState<ExclusiveOfferListItem[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)

  const fetchSelected = async () => {
    try {
      const params = new URLSearchParams()
      params.set('sort', 'updated_desc')
      params.set('engineLinked', 'all')
      const response = await fetch(
        `/api/admin/packaged-products/exclusive-offers?${params.toString()}`,
      )
      if (!response.ok) throw new Error('Failed to fetch exclusive offers')
      const data = await response.json()
      const all: ExclusiveOfferListItem[] = data.items || []
      const selected = all.filter((it) =>
        selectedPackagedProductIds.includes(it.packagedProductId),
      )
      setItems((prev) => {
        const existing = new Set(prev.map((p) => p.packagedProductId))
        const merged = [...prev]
        for (const it of selected) {
          if (!existing.has(it.packagedProductId)) merged.push(it)
        }
        return merged
      })
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    if (selectedPackagedProductIds.length === 0) return
    const existing = items.map((p) => p.packagedProductId)
    const missing = selectedPackagedProductIds.filter((id) => !existing.includes(id))
    if (missing.length > 0) fetchSelected()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPackagedProductIds.join(',')])

  useEffect(() => {
    if (!isOpen) return
    const t = setTimeout(() => {
      void fetchList()
    }, 200)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, searchQuery])

  const fetchList = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('sort', 'featured_asc')
      params.set('engineLinked', 'all')
      if (searchQuery.trim()) params.set('q', searchQuery.trim())

      const response = await fetch(
        `/api/admin/packaged-products/exclusive-offers?${params.toString()}`,
      )
      if (!response.ok) throw new Error('Failed to fetch exclusive offers')

      const data = await response.json()
      const fetched: ExclusiveOfferListItem[] = data.items || []
      setItems((prev) => {
        const byId = new Map(prev.map((p) => [p.packagedProductId, p]))
        for (const it of fetched) {
          byId.set(it.packagedProductId, it)
        }
        return Array.from(byId.values())
      })
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (packagedProductId: string) => {
    if (selectedPackagedProductIds.includes(packagedProductId)) {
      onChange(selectedPackagedProductIds.filter((id) => id !== packagedProductId))
    } else if (selectedPackagedProductIds.length < limit) {
      onChange([...selectedPackagedProductIds, packagedProductId])
    }
  }

  const handleRemove = (packagedProductId: string) => {
    onChange(selectedPackagedProductIds.filter((id) => id !== packagedProductId))
  }

  const handleMove = (fromIndex: number, toIndex: number) => {
    const next = [...selectedPackagedProductIds]
    const [moved] = next.splice(fromIndex, 1)
    next.splice(toIndex, 0, moved)
    onChange(next)
  }

  const byId = new Map(items.map((it) => [it.packagedProductId, it]))
  const orderedSelected = selectedPackagedProductIds
    .map((id) => byId.get(id))
    .filter((it): it is ExclusiveOfferListItem => it != null)

  const available = items.filter((it) => !selectedPackagedProductIds.includes(it.packagedProductId))

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <label className="block text-sm font-medium text-gray-700">
          Offres exclusives sélectionnées ({selectedPackagedProductIds.length}/{limit})
        </label>
        <Button type="button" variant="outline" size="sm" onClick={() => setIsOpen(!isOpen)}>
          {isOpen ? 'Fermer' : 'Choisir des offres'}
        </Button>
      </div>

      {orderedSelected.length > 0 && (
        <div className="space-y-2">
          {orderedSelected.map((it, index) => {
            const title = it.page?.title || it.slug
            return (
              <div
                key={it.packagedProductId}
                className="flex items-center gap-2 p-3 bg-gray-50 rounded border"
              >
                <GripVertical className="w-4 h-4 text-gray-400" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{title}</p>
                  <p className="text-xs text-gray-500 truncate">{it.page?.urlPath || it.slug}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {index > 0 && (
                    <button
                      type="button"
                      onClick={() => handleMove(index, index - 1)}
                      className="text-gray-400 hover:text-gray-600"
                      title="Monter"
                    >
                      ↑
                    </button>
                  )}
                  {index < orderedSelected.length - 1 && (
                    <button
                      type="button"
                      onClick={() => handleMove(index, index + 1)}
                      className="text-gray-400 hover:text-gray-600"
                      title="Descendre"
                    >
                      ↓
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleRemove(it.packagedProductId)}
                    className="text-red-400 hover:text-red-600"
                    title="Retirer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-xl font-semibold">Offres exclusives (Vault Builder)</h2>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 border-b">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Rechercher par titre ou slug…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {loading ? (
                <div className="text-center py-8 text-gray-500">Chargement…</div>
              ) : available.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  {searchQuery ? 'Aucune offre trouvée.' : 'Aucune offre disponible.'}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {available.map((it) => {
                    const title = it.page?.title || it.slug
                    const selected = selectedPackagedProductIds.includes(it.packagedProductId)
                    const disabled = !selected && selectedPackagedProductIds.length >= limit
                    return (
                      <button
                        type="button"
                        key={it.packagedProductId}
                        disabled={disabled}
                        onClick={() => !disabled && handleSelect(it.packagedProductId)}
                        className={`text-left border-2 rounded-lg p-3 transition-all ${
                          selected
                            ? 'border-indigo-600 ring-2 ring-indigo-200'
                            : disabled
                              ? 'border-gray-200 opacity-50 cursor-not-allowed'
                              : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <p className="text-sm font-medium line-clamp-2">{title}</p>
                        <p className="text-xs text-gray-500 mt-1">{it.page?.urlPath || it.slug}</p>
                        {it.tags?.length > 0 && (
                          <p className="text-xs text-gray-400 mt-1">{it.tags.slice(0, 3).join(' · ')}</p>
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            <div className="p-4 border-t flex justify-end">
              <Button type="button" onClick={() => setIsOpen(false)}>
                Terminé
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
