'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Plus, Edit, Trash2, Eye, EyeOff, ChevronDown, ChevronUp, ArrowUp, ArrowDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { TranslateModal } from '@/components/admin/TranslateModal'
import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'
import { slugify } from '@/lib/utils/slugify'

interface CollectionI18n {
  id: string
  locale: string
  title: string
  subtitle?: string | null
  description?: string | null
  translationStatus: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
}

interface Collection {
  id: string
  slug: string
  iconKey: string
  colorHex: string
  order: number
  isPublished: boolean
  i18n?: CollectionI18n[]
  _count?: {
    categories: number
    articles?: number
  }
}

const COLLECTION_ICON_OPTIONS = [
  { value: 'article', label: 'Article' },
  { value: 'book', label: 'Book' },
  { value: 'help-circle', label: 'Help circle' },
  { value: 'account-balance', label: 'Account balance' },
  { value: 'shield', label: 'Shield' },
  { value: 'credit-card', label: 'Credit card' },
  { value: 'swap', label: 'Swap' },
  { value: 'trending-up', label: 'Trending up' },
]

function normalizeHexColor(value: string): string {
  const cleaned = value.trim().replace('#', '').toUpperCase()
  if (/^[0-9A-F]{6}$/.test(cleaned)) return `#${cleaned}`
  return '#0F172A'
}

export default function AdminHelpCollectionsPage() {
  const router = useRouter()
  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; collectionId: string | null }>({
    open: false,
    collectionId: null,
  })
  const [expandedI18n, setExpandedI18n] = useState<Set<string>>(new Set())
  const [i18nData, setI18nData] = useState<Record<string, Record<string, { title: string; subtitle: string; description: string }>>>({})
  const [i18nStatuses, setI18nStatuses] = useState<Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>>>({})
  const [showTranslateModal, setShowTranslateModal] = useState<string | null>(null)
  const [savingI18n, setSavingI18n] = useState<Record<string, boolean>>({})
  const [approving, setApproving] = useState<Record<string, string>>({})
  const [showAddModal, setShowAddModal] = useState(false)
  const [newCollection, setNewCollection] = useState({
    title: '',
    subtitle: '',
    slug: '',
    iconKey: 'article',
    colorHex: '#0F172A',
    order: 0,
    isPublished: true,
  })
  const [creating, setCreating] = useState(false)
  const [checkingSlug, setCheckingSlug] = useState(false)
  const [styleSaving, setStyleSaving] = useState<Record<string, boolean>>({})

  const fetchCollections = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/admin/help/collections')
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch collections')
      }

      const data = await response.json()
      setCollections(data.collections || [])

      // Initialize i18n data
      const i18nMap: Record<string, Record<string, { title: string; subtitle: string; description: string }>> = {}
      const statusMap: Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>> = {}

      data.collections.forEach((col: Collection) => {
        i18nMap[col.id] = {}
        statusMap[col.id] = {}
        col.i18n?.forEach((i18n) => {
          i18nMap[col.id][i18n.locale] = {
            title: i18n.title || '',
            subtitle: i18n.subtitle || '',
            description: i18n.description || '',
          }
          statusMap[col.id][i18n.locale] = i18n.translationStatus
        })
      })

      setI18nData(i18nMap)
      setI18nStatuses(statusMap)
    } catch (error) {
      console.error('Error fetching collections:', error)
      toastError('Failed to fetch collections')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCollections()
  }, [])

  const handleDelete = async (collectionId: string) => {
    try {
      const response = await fetch(`/api/admin/help/collections/${collectionId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete collection')
      }

      toastSuccess('Collection deleted successfully')
      fetchCollections()
    } catch (error: any) {
      console.error('Error deleting collection:', error)
      toastError(error.message || 'Failed to delete collection')
    } finally {
      setDeleteDialog({ open: false, collectionId: null })
    }
  }

  const handleTogglePublish = async (collection: Collection) => {
    try {
      const response = await fetch(`/api/admin/help/collections/${collection.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isPublished: !collection.isPublished }),
      })

      if (!response.ok) throw new Error('Failed to update collection')

      toastSuccess(`Collection ${!collection.isPublished ? 'published' : 'unpublished'}`)
      fetchCollections()
    } catch (error) {
      console.error('Error toggling publish:', error)
      toastError('Failed to update collection')
    }
  }

  const handleSaveI18n = async (collectionId: string, locale: string) => {
    setSavingI18n((prev) => ({ ...prev, [`${collectionId}-${locale}`]: true }))
    try {
      const data = i18nData[collectionId]?.[locale]
      if (!data) return

      const response = await fetch(`/api/admin/help/collections/${collectionId}/i18n`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          locale,
          title: data.title,
          subtitle: data.subtitle || null,
          description: data.description || null,
        }),
      })

      if (!response.ok) throw new Error('Failed to save translation')

      toastSuccess('Translation saved')
      fetchCollections()
    } catch (error) {
      console.error('Error saving i18n:', error)
      toastError('Failed to save translation')
    } finally {
      setSavingI18n((prev) => ({ ...prev, [`${collectionId}-${locale}`]: false }))
    }
  }

  const handleApprove = async (collectionId: string, locale: string) => {
    setApproving((prev) => ({ ...prev, [`${collectionId}-${locale}`]: locale }))
    try {
      const response = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityType: 'HELP_COLLECTION',
          entityId: collectionId,
          locale,
        }),
      })

      if (!response.ok) throw new Error('Failed to approve translation')

      toastSuccess('Translation approved')
      fetchCollections()
    } catch (error) {
      console.error('Error approving translation:', error)
      toastError('Failed to approve translation')
    } finally {
      setApproving((prev) => {
        const newState = { ...prev }
        delete newState[`${collectionId}-${locale}`]
        return newState
      })
    }
  }

  const generateUniqueSlug = async (baseSlug: string): Promise<string> => {
    let slug = baseSlug
    let counter = 1

    while (true) {
      const response = await fetch(`/api/admin/help/collections/check-slug?slug=${encodeURIComponent(slug)}`)
      if (response.ok) {
        const data = await response.json()
        if (!data.exists) {
          return slug
        }
      }
      slug = `${baseSlug}-${counter}`
      counter++
    }
  }

  const handleTitleChange = async (title: string) => {
    setNewCollection({ ...newCollection, title })
    
    if (title.trim()) {
      setCheckingSlug(true)
      try {
        const baseSlug = slugify(title)
        const uniqueSlug = await generateUniqueSlug(baseSlug)
        setNewCollection((prev) => ({ ...prev, slug: uniqueSlug }))
      } catch (error) {
        console.error('Error generating slug:', error)
      } finally {
        setCheckingSlug(false)
      }
    }
  }

  const handleCreate = async () => {
    if (!newCollection.title.trim()) {
      toastError('Title is required')
      return
    }

    if (!newCollection.slug.trim()) {
      toastError('Slug is required')
      return
    }

    setCreating(true)
    try {
      const response = await fetch('/api/admin/help/collections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slug: newCollection.slug,
          title: newCollection.title,
          subtitle: newCollection.subtitle || null,
          iconKey: newCollection.iconKey,
          colorHex: normalizeHexColor(newCollection.colorHex),
          order: newCollection.order,
          isPublished: newCollection.isPublished,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to create collection')
      }

      toastSuccess('Collection created successfully')
      setShowAddModal(false)
      setNewCollection({
        title: '',
        subtitle: '',
        slug: '',
        iconKey: 'article',
        colorHex: '#0F172A',
        order: 0,
        isPublished: true,
      })
      fetchCollections()
    } catch (error: any) {
      console.error('Error creating collection:', error)
      toastError(error.message || 'Failed to create collection')
    } finally {
      setCreating(false)
    }
  }

  const handleMoveOrder = async (collectionId: string, direction: 'up' | 'down') => {
    const collection = collections.find((c) => c.id === collectionId)
    if (!collection) return

    const currentIndex = collections.findIndex((c) => c.id === collectionId)
    const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1

    if (targetIndex < 0 || targetIndex >= collections.length) return

    const targetCollection = collections[targetIndex]
    const newOrder = targetCollection.order

    try {
      await fetch(`/api/admin/help/collections/${collectionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: newOrder }),
      })

      await fetch(`/api/admin/help/collections/${targetCollection.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: collection.order }),
      })

      fetchCollections()
    } catch (error) {
      console.error('Error moving collection:', error)
      toastError('Failed to reorder collection')
    }
  }

  const handleSaveStyle = async (collection: Collection) => {
    setStyleSaving((prev) => ({ ...prev, [collection.id]: true }))
    try {
      const response = await fetch(`/api/admin/help/collections/${collection.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          iconKey: collection.iconKey,
          colorHex: normalizeHexColor(collection.colorHex),
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to save style')
      }

      toastSuccess('Collection style saved')
      fetchCollections()
    } catch (error: any) {
      toastError(error.message || 'Failed to save style')
    } finally {
      setStyleSaving((prev) => ({ ...prev, [collection.id]: false }))
    }
  }

  if (loading) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Collections</h1>
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Collection
        </Button>
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">Create Collection</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  value={newCollection.title}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="À propos de Shares"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={newCollection.subtitle}
                  onChange={(e) =>
                    setNewCollection({ ...newCollection, subtitle: e.target.value })
                  }
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="Petite description de la collection"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Slug {checkingSlug && <span className="text-xs text-gray-500">(generating...)</span>}
                </label>
                <input
                  type="text"
                  value={newCollection.slug}
                  onChange={(e) =>
                    setNewCollection({ ...newCollection, slug: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                  placeholder="Auto-generated from title"
                  readOnly
                />
                <p className="text-xs text-gray-500 mt-1">Auto-generated and unique</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Icon</label>
                  <select
                    value={newCollection.iconKey}
                    onChange={(e) => setNewCollection({ ...newCollection, iconKey: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    {COLLECTION_ICON_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Color</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={normalizeHexColor(newCollection.colorHex)}
                      onChange={(e) =>
                        setNewCollection({ ...newCollection, colorHex: normalizeHexColor(e.target.value) })
                      }
                      className="w-10 h-10 border border-gray-300 rounded-md"
                    />
                    <input
                      type="text"
                      value={newCollection.colorHex}
                      onChange={(e) => setNewCollection({ ...newCollection, colorHex: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono"
                    />
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Order
                </label>
                <input
                  type="number"
                  value={newCollection.order}
                  onChange={(e) =>
                    setNewCollection({ ...newCollection, order: parseInt(e.target.value) || 0 })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={newCollection.isPublished}
                  onChange={(e) =>
                    setNewCollection({ ...newCollection, isPublished: e.target.checked })
                  }
                  className="mr-2"
                />
                <label className="text-sm text-gray-700">Published</label>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <Button variant="outline" onClick={() => setShowAddModal(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Collections Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Order
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Slug
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Title (FR)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Style
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Categories / Articles
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Translations
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {collections.map((collection) => {
              const frI18n = collection.i18n?.find((i) => i.locale === 'fr')
              const hasI18nExpanded = expandedI18n.has(collection.id)

              return (
                <tr key={collection.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleMoveOrder(collection.id, 'up')}
                        disabled={collections.findIndex((c) => c.id === collection.id) === 0}
                        className="p-1 hover:bg-gray-100 rounded disabled:opacity-50"
                      >
                        <ArrowUp className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleMoveOrder(collection.id, 'down')}
                        disabled={
                          collections.findIndex((c) => c.id === collection.id) ===
                          collections.length - 1
                        }
                        className="p-1 hover:bg-gray-100 rounded disabled:opacity-50"
                      >
                        <ArrowDown className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {collection.slug}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {frI18n?.title || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <div className="flex items-center gap-2">
                      <select
                        value={collection.iconKey}
                        onChange={(e) =>
                          setCollections((prev) =>
                            prev.map((c) => (c.id === collection.id ? { ...c, iconKey: e.target.value } : c))
                          )
                        }
                        className="px-2 py-1 border border-gray-300 rounded-md text-xs"
                      >
                        {COLLECTION_ICON_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                      <input
                        type="color"
                        value={normalizeHexColor(collection.colorHex)}
                        onChange={(e) =>
                          setCollections((prev) =>
                            prev.map((c) =>
                              c.id === collection.id
                                ? { ...c, colorHex: normalizeHexColor(e.target.value) }
                                : c
                            )
                          )
                        }
                        className="w-8 h-8 border border-gray-300 rounded"
                      />
                      <button
                        onClick={() => handleSaveStyle(collection)}
                        className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50"
                        disabled={styleSaving[collection.id]}
                      >
                        {styleSaving[collection.id] ? '...' : 'Save'}
                      </button>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {collection._count?.categories || 0} cat. / {collection._count?.articles || 0} art.
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => handleTogglePublish(collection)}
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        collection.isPublished
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {collection.isPublished ? (
                        <>
                          <Eye className="w-3 h-3 mr-1" />
                          Published
                        </>
                      ) : (
                        <>
                          <EyeOff className="w-3 h-3 mr-1" />
                          Draft
                        </>
                      )}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() =>
                        setExpandedI18n((prev) => {
                          const newSet = new Set(prev)
                          if (newSet.has(collection.id)) {
                            newSet.delete(collection.id)
                          } else {
                            newSet.add(collection.id)
                          }
                          return newSet
                        })
                      }
                      className="text-sm text-indigo-600 hover:text-indigo-900"
                    >
                      {hasI18nExpanded ? (
                        <ChevronUp className="w-4 h-4 inline" />
                      ) : (
                        <ChevronDown className="w-4 h-4 inline" />
                      )}{' '}
                      {collection.i18n?.length || 0} locales
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setDeleteDialog({ open: true, collectionId: collection.id })}
                        className="text-red-600 hover:text-red-900"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {/* Expanded I18n Rows */}
        {collections.map((collection) => {
          if (!expandedI18n.has(collection.id)) return null

          return (
            <tr key={`i18n-${collection.id}`} className="bg-gray-50">
              <td colSpan={8} className="px-6 py-4">
                <div className="space-y-4">
                  <h4 className="font-medium text-gray-900">Localized Labels</h4>
                  {supportedLocales.map((locale) => {
                    const i18n = collection.i18n?.find((i) => i.locale === locale)
                    const data = i18nData[collection.id]?.[locale] || {
                      title: '',
                      subtitle: '',
                      description: '',
                    }
                    const status = i18nStatuses[collection.id]?.[locale] || 'ORIGINAL'
                    const isSaving = savingI18n[`${collection.id}-${locale}`]
                    const isApproving = approving[`${collection.id}-${locale}`] === locale

                    return (
                      <div
                        key={locale}
                        className="border border-gray-200 rounded-lg p-4 bg-white"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-700 uppercase">
                              {locale}
                            </span>
                            <span
                              className={`text-xs px-2 py-1 rounded ${
                                status === 'ORIGINAL'
                                  ? 'bg-blue-100 text-blue-800'
                                  : status === 'MACHINE'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-green-100 text-green-800'
                              }`}
                            >
                              {status}
                            </span>
                          </div>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                setShowTranslateModal(
                                  `${collection.id}-${locale}`
                                )
                              }
                            >
                              Auto-translate
                            </Button>
                            {status === 'MACHINE' && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleApprove(collection.id, locale)}
                                disabled={isApproving}
                              >
                                {isApproving ? 'Approving...' : 'Approve'}
                              </Button>
                            )}
                            <Button
                              size="sm"
                              onClick={() => handleSaveI18n(collection.id, locale)}
                              disabled={isSaving}
                            >
                              {isSaving ? 'Saving...' : 'Save'}
                            </Button>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">
                              Title *
                            </label>
                            <input
                              type="text"
                              value={data.title}
                              onChange={(e) => {
                                setI18nData((prev) => ({
                                  ...prev,
                                  [collection.id]: {
                                    ...prev[collection.id],
                                    [locale]: { ...data, title: e.target.value },
                                  },
                                }))
                              }}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">
                              Subtitle
                            </label>
                            <input
                              type="text"
                              value={data.subtitle}
                              onChange={(e) => {
                                setI18nData((prev) => ({
                                  ...prev,
                                  [collection.id]: {
                                    ...prev[collection.id],
                                    [locale]: { ...data, subtitle: e.target.value },
                                  },
                                }))
                              }}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">
                              Description
                            </label>
                            <textarea
                              value={data.description}
                              onChange={(e) => {
                                setI18nData((prev) => ({
                                  ...prev,
                                  [collection.id]: {
                                    ...prev[collection.id],
                                    [locale]: { ...data, description: e.target.value },
                                  },
                                }))
                              }}
                              rows={2}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            />
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </td>
            </tr>
          )
        })}
      </div>

      {collections.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">No collections yet. Create one to get started.</p>
        </div>
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteDialog.open}
        onOpenChange={(open) =>
          setDeleteDialog({ open, collectionId: deleteDialog.collectionId })
        }
        title="Delete Collection"
        description="Are you sure you want to delete this collection? This action cannot be undone."
        onConfirm={() => {
          if (deleteDialog.collectionId) {
            handleDelete(deleteDialog.collectionId)
          }
        }}
      />

      {/* Translate Modal */}
      {showTranslateModal && (
        <TranslateModal
          open={!!showTranslateModal}
          onOpenChange={(open) => !open && setShowTranslateModal(null)}
          sourceLocale={showTranslateModal.split('-')[1] as Locale}
          onTranslate={async ({ sourceLocale, targetLocales, mode }) => {
            const response = await fetch('/api/admin/translate/help-collection', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                collectionId: showTranslateModal.split('-')[0],
                sourceLocale,
                targetLocales,
                mode,
              }),
            })

            if (!response.ok) {
              const error = await response.json()
              throw new Error(error.error || 'Translation failed')
            }

            const data = await response.json()
            await fetchCollections()
            return data
          }}
        />
      )}
    </div>
  )
}

