'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { TranslateModal } from '@/components/admin/TranslateModal'
import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'
import { ChevronDown, ChevronUp } from 'lucide-react'

interface CategoryI18n {
  id: string
  locale: string
  label: string
  translationStatus: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
}

interface Category {
  id: string
  slug: string
  label: string
  labelBase?: string
  order: number
  isActive: boolean
  i18n?: CategoryI18n[]
}

export default function AdminCategoriesPage() {
  const router = useRouter()
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedI18nCategories, setExpandedI18nCategories] = useState<Set<string>>(new Set())
  const [i18nLabels, setI18nLabels] = useState<Record<string, Record<string, string>>>({})
  const [i18nStatuses, setI18nStatuses] = useState<Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>>>({})
  const [showTranslateModal, setShowTranslateModal] = useState<string | null>(null)
  const [savingI18n, setSavingI18n] = useState<Record<string, boolean>>({})
  const [approving, setApproving] = useState<Record<string, string>>({})

  useEffect(() => {
    fetchCategories()
  }, [])

  const fetchCategories = async () => {
    try {
      const response = await fetch('/api/admin/article-categories?locale=fr')
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch categories')
      }

      const data = await response.json()
      setCategories(data.categories || [])
      
      // Initialize i18n labels and statuses
      const labels: Record<string, Record<string, string>> = {}
      const statuses: Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>> = {}
      
      data.categories.forEach((cat: Category) => {
        if (cat.i18n) {
          labels[cat.id] = {}
          statuses[cat.id] = {}
          cat.i18n.forEach((i18n) => {
            labels[cat.id][i18n.locale] = i18n.label
            statuses[cat.id][i18n.locale] = i18n.translationStatus
          })
        }
      })
      
      setI18nLabels(labels)
      setI18nStatuses(statuses)
    } catch (error) {
      console.error('Error fetching categories:', error)
      toastError('Failed to load categories')
    } finally {
      setLoading(false)
    }
  }

  const fetchCategoryI18n = async (categoryId: string) => {
    try {
      const response = await fetch(`/api/admin/article-categories/${categoryId}/i18n`)
      if (!response.ok) {
        throw new Error('Failed to fetch i18n')
      }
      const data = await response.json()
      
      setI18nLabels((prev) => {
        const newLabels = { ...prev }
        if (!newLabels[categoryId]) newLabels[categoryId] = {}
        data.i18n.forEach((i18n: CategoryI18n) => {
          newLabels[categoryId][i18n.locale] = i18n.label
        })
        return newLabels
      })
      
      setI18nStatuses((prev) => {
        const newStatuses = { ...prev }
        if (!newStatuses[categoryId]) newStatuses[categoryId] = {}
        data.i18n.forEach((i18n: CategoryI18n) => {
          newStatuses[categoryId][i18n.locale] = i18n.translationStatus
        })
        return newStatuses
      })
    } catch (error) {
      console.error('Error fetching category i18n:', error)
    }
  }

  const handleSaveI18nLabel = async (categoryId: string, locale: string) => {
    const label = i18nLabels[categoryId]?.[locale]
    if (!label || label.trim().length === 0) {
      toastError('Label cannot be empty')
      return
    }

    setSavingI18n((prev) => ({ ...prev, [categoryId]: true }))
    try {
      const response = await fetch(`/api/admin/article-categories/${categoryId}/i18n`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locale, label }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to save label')
      }

      toastSuccess('Label saved')
      await fetchCategoryI18n(categoryId)
    } catch (error: any) {
      toastError(error.message || 'Failed to save label')
    } finally {
      setSavingI18n((prev) => ({ ...prev, [categoryId]: false }))
    }
  }

  const handleApproveTranslation = async (categoryId: string, locale: string) => {
    setApproving((prev) => ({ ...prev, [`${categoryId}:${locale}`]: 'true' }))
    try {
      const response = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityType: 'ARTICLE_CATEGORY',
          entityId: categoryId,
          locale,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to approve translation')
      }

      toastSuccess('Translation approved')
      await fetchCategoryI18n(categoryId)
    } catch (error: any) {
      toastError(error.message || 'Failed to approve translation')
    } finally {
      setApproving((prev) => {
        const newApproving = { ...prev }
        delete newApproving[`${categoryId}:${locale}`]
        return newApproving
      })
    }
  }

  const toggleI18nExpanded = (categoryId: string) => {
    setExpandedI18nCategories((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(categoryId)) {
        newSet.delete(categoryId)
      } else {
        newSet.add(categoryId)
        fetchCategoryI18n(categoryId)
      }
      return newSet
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading categories...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Blog Categories</h1>
          <p className="text-sm text-gray-500 mt-1">Manage article categories and their localized labels</p>
        </div>
        <Link
          href="/admin/articles"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to Articles
        </Link>
      </div>

      {/* Categories Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {categories.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No categories yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Slug</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Order</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Active</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Label (FR)</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {categories.map((category) => (
                  <>
                    <tr
                      key={category.id}
                      className="border-b border-gray-100 hover:bg-gray-50"
                    >
                      <td className="py-3 px-4">
                        <span className="text-sm font-mono text-gray-600">{category.slug}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm">{category.order}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm">{category.isActive ? '✓' : '✗'}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm font-medium">{category.label}</span>
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => toggleI18nExpanded(category.id)}
                          className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700"
                        >
                          {expandedI18nCategories.has(category.id) ? 'Hide Labels' : 'Edit Labels'}
                        </button>
                      </td>
                    </tr>
                    {/* I18n Section (expandable) */}
                    <tr>
                      <td colSpan={5} className="p-0">
                        <div className={`overflow-hidden transition-all ${expandedI18nCategories.has(category.id) ? 'max-h-[500px]' : 'max-h-0'}`}>
                          <div className="px-4 py-4 bg-gray-50 border-t border-gray-200">
                            <div className="flex items-center justify-between mb-3">
                              <h4 className="text-sm font-semibold text-gray-700">Localized Labels</h4>
                              <button
                                onClick={() => toggleI18nExpanded(category.id)}
                                className="text-xs text-gray-500 hover:text-gray-700"
                              >
                                {expandedI18nCategories.has(category.id) ? (
                                  <ChevronUp className="w-4 h-4" />
                                ) : (
                                  <ChevronDown className="w-4 h-4" />
                                )}
                              </button>
                            </div>
                            
                            {expandedI18nCategories.has(category.id) && (
                              <div className="space-y-3">
                                {supportedLocales.map((locale) => {
                                  const currentLabel = i18nLabels[category.id]?.[locale] || ''
                                  const status = i18nStatuses[category.id]?.[locale] || 'ORIGINAL'
                                  const isSaving = savingI18n[category.id]
                                  const isApproving = approving[`${category.id}:${locale}`]
                                  
                                  return (
                                    <div key={locale} className="bg-white p-3 rounded border border-gray-200">
                                      <div className="flex items-center gap-2 mb-2">
                                        <span className="text-xs font-medium text-gray-700 uppercase">{locale}</span>
                                        {status === 'ORIGINAL' && (
                                          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">ORIGINAL</span>
                                        )}
                                        {status === 'MACHINE' && (
                                          <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-800 rounded">MACHINE</span>
                                        )}
                                        {status === 'APPROVED' && (
                                          <span className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded">APPROVED</span>
                                        )}
                                      </div>
                                      
                                      <div className="flex gap-2 mb-2">
                                        <input
                                          type="text"
                                          value={currentLabel}
                                          onChange={(e) => {
                                            setI18nLabels((prev) => ({
                                              ...prev,
                                              [category.id]: {
                                                ...prev[category.id],
                                                [locale]: e.target.value,
                                              },
                                            }))
                                          }}
                                          className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded"
                                          placeholder={`Label for ${locale.toUpperCase()}`}
                                        />
                                        <button
                                          onClick={() => handleSaveI18nLabel(category.id, locale)}
                                          disabled={isSaving || !currentLabel.trim()}
                                          className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                                        >
                                          {isSaving ? 'Saving...' : 'Save'}
                                        </button>
                                        {status === 'MACHINE' && (
                                          <button
                                            onClick={() => handleApproveTranslation(category.id, locale)}
                                            disabled={!!isApproving}
                                            className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                                          >
                                            {isApproving ? 'Approving...' : 'Approve'}
                                          </button>
                                        )}
                                      </div>
                                      
                                      <p className="text-xs text-gray-500">
                                        This label appears on the blog page for the selected language.
                                      </p>
                                    </div>
                                  )
                                })}
                                
                                <div className="pt-2 border-t border-gray-200">
                                  <button
                                    onClick={() => setShowTranslateModal(category.id)}
                                    className="px-4 py-2 text-sm bg-purple-600 text-white rounded hover:bg-purple-700"
                                  >
                                    Auto-translate
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Translate Modal */}
      {showTranslateModal && (
        <TranslateModal
          open={showTranslateModal !== null}
          onOpenChange={(open) => setShowTranslateModal(open ? showTranslateModal : null)}
          sourceLocale={defaultLocale}
          hasGlossary={false}
          onTranslate={async ({ sourceLocale, targetLocales, mode }) => {
            const response = await fetch('/api/admin/translate/article-category', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                categoryId: showTranslateModal,
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
            
            // Refresh i18n for this category
            await fetchCategoryI18n(showTranslateModal)
            
            return data
          }}
        />
      )}
    </div>
  )
}









