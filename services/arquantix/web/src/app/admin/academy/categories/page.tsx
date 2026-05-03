'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Trash2, Eye, EyeOff, ChevronDown, ChevronUp, ArrowUp, ArrowDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { TranslateModal } from '@/components/admin/TranslateModal'
import { supportedLocales, type Locale } from '@/config/locales'

interface CategoryI18n {
  id: string
  locale: string
  title: string
  description?: string | null
  translationStatus: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
}

interface Collection {
  id: string
  slug: string
  i18n?: Array<{ locale: string; title: string }>
}

interface Category {
  id: string
  slug: string
  order: number
  isPublished: boolean
  collectionId: string
  collection?: Collection
  i18n?: CategoryI18n[]
  _count?: {
    unifiedArticles?: number
  }
}

export default function AdminAcademyCategoriesPage() {
  const router = useRouter()
  const [categories, setCategories] = useState<Category[]>([])
  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCollection, setSelectedCollection] = useState<string>('')
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; categoryId: string | null }>({
    open: false,
    categoryId: null,
  })
  const [expandedI18n, setExpandedI18n] = useState<Set<string>>(new Set())
  const [i18nData, setI18nData] = useState<Record<string, Record<string, { title: string; description: string }>>>({})
  const [i18nStatuses, setI18nStatuses] = useState<Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>>>({})
  const [showTranslateModal, setShowTranslateModal] = useState<string | null>(null)
  const [savingI18n, setSavingI18n] = useState<Record<string, boolean>>({})
  const [approving, setApproving] = useState<Record<string, string>>({})
  const [showAddModal, setShowAddModal] = useState(false)
  const [newCategory, setNewCategory] = useState({ collectionId: '', slug: '', order: 0, isPublished: true })
  const [creating, setCreating] = useState(false)

  const fetchCollections = async () => {
    try {
      const response = await fetch('/api/admin/academy/collections')
      if (!response.ok) throw new Error('Failed to fetch academy collections')
      const data = await response.json()
      setCollections(data.collections || [])
      if (data.collections.length > 0 && !selectedCollection) {
        setSelectedCollection(data.collections[0].id)
      }
    } catch (error) {
      console.error('Error fetching academy collections:', error)
    }
  }

  const fetchCategories = async () => {
    if (!selectedCollection) {
      setCategories([])
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`/api/admin/academy/categories?collectionId=${selectedCollection}`)
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch academy categories')
      }

      const data = await response.json()
      setCategories(data.categories || [])

      const i18nMap: Record<string, Record<string, { title: string; description: string }>> = {}
      const statusMap: Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>> = {}

      data.categories.forEach((cat: Category) => {
        i18nMap[cat.id] = {}
        statusMap[cat.id] = {}
        cat.i18n?.forEach((i18n) => {
          i18nMap[cat.id][i18n.locale] = {
            title: i18n.title || '',
            description: i18n.description || '',
          }
          statusMap[cat.id][i18n.locale] = i18n.translationStatus
        })
      })

      setI18nData(i18nMap)
      setI18nStatuses(statusMap)
    } catch (error) {
      console.error('Error fetching academy categories:', error)
      toastError('Failed to fetch academy categories')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCollections()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    fetchCategories()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCollection])

  const handleDelete = async (categoryId: string) => {
    try {
      const response = await fetch(`/api/admin/academy/categories/${categoryId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete category')
      }

      toastSuccess('Category deleted successfully')
      fetchCategories()
    } catch (error) {
      const err = error as Error
      console.error('Error deleting category:', err)
      toastError(err.message || 'Failed to delete category')
    } finally {
      setDeleteDialog({ open: false, categoryId: null })
    }
  }

  const handleTogglePublish = async (category: Category) => {
    try {
      const response = await fetch(`/api/admin/academy/categories/${category.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isPublished: !category.isPublished }),
      })

      if (!response.ok) throw new Error('Failed to update category')

      toastSuccess(`Category ${!category.isPublished ? 'published' : 'unpublished'}`)
      fetchCategories()
    } catch (error) {
      console.error('Error toggling publish:', error)
      toastError('Failed to update category')
    }
  }

  const handleSaveI18n = async (categoryId: string, locale: string) => {
    setSavingI18n((prev) => ({ ...prev, [`${categoryId}-${locale}`]: true }))
    try {
      const data = i18nData[categoryId]?.[locale]
      if (!data) return

      const response = await fetch(`/api/admin/academy/categories/${categoryId}/i18n`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          locale,
          title: data.title,
          description: data.description || null,
        }),
      })

      if (!response.ok) throw new Error('Failed to save translation')

      toastSuccess('Translation saved')
      fetchCategories()
    } catch (error) {
      console.error('Error saving i18n:', error)
      toastError('Failed to save translation')
    } finally {
      setSavingI18n((prev) => ({ ...prev, [`${categoryId}-${locale}`]: false }))
    }
  }

  const handleApprove = async (categoryId: string, locale: string) => {
    setApproving((prev) => ({ ...prev, [`${categoryId}-${locale}`]: locale }))
    try {
      const response = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityType: 'ACADEMY_CATEGORY',
          entityId: categoryId,
          locale,
        }),
      })

      if (!response.ok) throw new Error('Failed to approve translation')

      toastSuccess('Translation approved')
      fetchCategories()
    } catch (error) {
      console.error('Error approving translation:', error)
      toastError('Failed to approve translation')
    } finally {
      setApproving((prev) => {
        const newState = { ...prev }
        delete newState[`${categoryId}-${locale}`]
        return newState
      })
    }
  }

  const handleCreate = async () => {
    if (!newCategory.slug.trim() || !newCategory.collectionId) {
      toastError('Slug and collection are required')
      return
    }

    setCreating(true)
    try {
      const response = await fetch('/api/admin/academy/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCategory),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to create category')
      }

      toastSuccess('Category created successfully')
      setShowAddModal(false)
      setNewCategory({ collectionId: selectedCollection, slug: '', order: 0, isPublished: true })
      fetchCategories()
    } catch (error) {
      const err = error as Error
      console.error('Error creating category:', err)
      toastError(err.message || 'Failed to create category')
    } finally {
      setCreating(false)
    }
  }

  const handleMoveOrder = async (categoryId: string, direction: 'up' | 'down') => {
    const category = categories.find((c) => c.id === categoryId)
    if (!category) return

    const filteredCategories = categories.filter((c) => c.collectionId === category.collectionId)
    const currentIndex = filteredCategories.findIndex((c) => c.id === categoryId)
    const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1

    if (targetIndex < 0 || targetIndex >= filteredCategories.length) return

    const targetCategory = filteredCategories[targetIndex]
    const newOrder = targetCategory.order

    try {
      await fetch(`/api/admin/academy/categories/${categoryId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: newOrder }),
      })

      await fetch(`/api/admin/academy/categories/${targetCategory.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: category.order }),
      })

      fetchCategories()
    } catch (error) {
      console.error('Error moving category:', error)
      toastError('Failed to reorder category')
    }
  }

  if (loading && !selectedCollection) {
    return <div className="text-center py-12">Loading...</div>
  }

  const filteredCategories = categories.filter((c) => c.collectionId === selectedCollection)

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Academy Categories</h1>
        <Button
          onClick={() => {
            setNewCategory({
              collectionId: selectedCollection,
              slug: '',
              order: 0,
              isPublished: true,
            })
            setShowAddModal(true)
          }}
          disabled={!selectedCollection}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Category
        </Button>
      </div>

      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Collection
        </label>
        <select
          value={selectedCollection}
          onChange={(e) => setSelectedCollection(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md"
        >
          <option value="">Select a collection</option>
          {collections.map((col) => (
            <option key={col.id} value={col.id}>
              {col.i18n?.find((i) => i.locale === 'fr')?.title || col.slug}
            </option>
          ))}
        </select>
      </div>

      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">Create Academy Category</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Collection *
                </label>
                <select
                  value={newCategory.collectionId}
                  onChange={(e) =>
                    setNewCategory({ ...newCategory, collectionId: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="">Select collection</option>
                  {collections.map((col) => (
                    <option key={col.id} value={col.id}>
                      {col.i18n?.find((i) => i.locale === 'fr')?.title || col.slug}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Slug *
                </label>
                <input
                  type="text"
                  value={newCategory.slug}
                  onChange={(e) =>
                    setNewCategory({ ...newCategory, slug: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="basics-investing"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Order
                </label>
                <input
                  type="number"
                  value={newCategory.order}
                  onChange={(e) =>
                    setNewCategory({ ...newCategory, order: parseInt(e.target.value) || 0 })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={newCategory.isPublished}
                  onChange={(e) =>
                    setNewCategory({ ...newCategory, isPublished: e.target.checked })
                  }
                  className="mr-2"
                />
                <label className="text-sm text-gray-700">Published</label>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <Button
                variant="outline"
                onClick={() => setShowAddModal(false)}
              >
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Order</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Slug</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Title (FR)</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Articles</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Translations</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredCategories.map((category) => {
              const frI18n = category.i18n?.find((i) => i.locale === 'fr')
              const hasI18nExpanded = expandedI18n.has(category.id)

              return (
                <tr key={category.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleMoveOrder(category.id, 'up')}
                        disabled={filteredCategories.findIndex((c) => c.id === category.id) === 0}
                        className="p-1 hover:bg-gray-100 rounded disabled:opacity-50"
                      >
                        <ArrowUp className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleMoveOrder(category.id, 'down')}
                        disabled={
                          filteredCategories.findIndex((c) => c.id === category.id) ===
                          filteredCategories.length - 1
                        }
                        className="p-1 hover:bg-gray-100 rounded disabled:opacity-50"
                      >
                        <ArrowDown className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {category.slug}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {frI18n?.title || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {category._count?.unifiedArticles || 0}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => handleTogglePublish(category)}
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        category.isPublished
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {category.isPublished ? (
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
                          if (newSet.has(category.id)) {
                            newSet.delete(category.id)
                          } else {
                            newSet.add(category.id)
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
                      {category.i18n?.length || 0} locales
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setDeleteDialog({ open: true, categoryId: category.id })}
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

        {filteredCategories.map((category) => {
          if (!expandedI18n.has(category.id)) return null

          return (
            <tr key={`i18n-${category.id}`} className="bg-gray-50">
              <td colSpan={7} className="px-6 py-4">
                <div className="space-y-4">
                  <h4 className="font-medium text-gray-900">Localized Labels</h4>
                  {supportedLocales.map((locale) => {
                    const data = i18nData[category.id]?.[locale] || {
                      title: '',
                      description: '',
                    }
                    const status = i18nStatuses[category.id]?.[locale] || 'ORIGINAL'
                    const isSaving = savingI18n[`${category.id}-${locale}`]
                    const isApproving = approving[`${category.id}-${locale}`] === locale

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
                                  `${category.id}-${locale}`
                                )
                              }
                            >
                              Auto-translate
                            </Button>
                            {status === 'MACHINE' && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleApprove(category.id, locale)}
                                disabled={isApproving}
                              >
                                {isApproving ? 'Approving...' : 'Approve'}
                              </Button>
                            )}
                            <Button
                              size="sm"
                              onClick={() => handleSaveI18n(category.id, locale)}
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
                                  [category.id]: {
                                    ...prev[category.id],
                                    [locale]: { ...data, title: e.target.value },
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
                                  [category.id]: {
                                    ...prev[category.id],
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

      {filteredCategories.length === 0 && selectedCollection && (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">No academy categories yet. Create one to get started.</p>
        </div>
      )}

      {!selectedCollection && (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">Please select a collection to view categories.</p>
        </div>
      )}

      <ConfirmDialog
        open={deleteDialog.open}
        onOpenChange={(open) =>
          setDeleteDialog({ open, categoryId: deleteDialog.categoryId })
        }
        title="Delete Academy Category"
        description="Are you sure you want to delete this academy category? This action cannot be undone."
        onConfirm={() => {
          if (deleteDialog.categoryId) {
            handleDelete(deleteDialog.categoryId)
          }
        }}
      />

      {showTranslateModal && (
        <TranslateModal
          open={!!showTranslateModal}
          onOpenChange={(open) => !open && setShowTranslateModal(null)}
          sourceLocale={showTranslateModal.split('-')[1] as Locale}
          onTranslate={async ({ sourceLocale, targetLocales, mode }) => {
            const response = await fetch('/api/admin/translate/academy-category', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                categoryId: showTranslateModal.split('-')[0],
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
            await fetchCategories()
            return data
          }}
        />
      )}
    </div>
  )
}
