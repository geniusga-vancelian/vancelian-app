'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Plus, Search, Trash2, Eye, EyeOff, Edit } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ContentStatus } from '@prisma/client'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { defaultLocale } from '@/config/locales'
import { slugify } from '@/lib/utils/slugify'

interface Article {
  id: string
  slug: string
  status: ContentStatus
  publishedAt: string | null
  createdAt: string
  updatedAt: string
  title: string
  locale: string
  category?: {
    id: string
    slug: string
    i18n?: Array<{ locale: string; title: string }>
    collection?: {
      slug: string
      i18n?: Array<{ locale: string; title: string }>
    }
  }
}

interface Category {
  id: string
  slug: string
  collectionId: string
  i18n?: Array<{ locale: string; title: string }>
  collection?: {
    slug: string
    i18n?: Array<{ locale: string; title: string }>
  }
}

interface Collection {
  id: string
  slug: string
  i18n?: Array<{ locale: string; title: string }>
}

export default function AdminHelpArticlesPage() {
  const router = useRouter()
  const [articles, setArticles] = useState<Article[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<ContentStatus | 'ALL'>('ALL')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedCollection, setSelectedCollection] = useState<string>('')
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; articleId: string | null }>({
    open: false,
    articleId: null,
  })
  const [showAddModal, setShowAddModal] = useState(false)
  const [newArticle, setNewArticle] = useState({ title: '', categoryId: '', slug: '', collectionId: '' })
  const [creating, setCreating] = useState(false)
  const [modalCategories, setModalCategories] = useState<Category[]>([])
  const [checkingSlug, setCheckingSlug] = useState(false)

  const fetchCollections = async () => {
    try {
      const response = await fetch('/api/admin/help/collections')
      if (!response.ok) throw new Error('Failed to fetch collections')
      const data = await response.json()
      setCollections(data.collections || [])
    } catch (error) {
      console.error('Error fetching collections:', error)
    }
  }

  const fetchCategories = async (collectionId?: string) => {
    const targetCollectionId = collectionId || selectedCollection
    if (!targetCollectionId) {
      setCategories([])
      return []
    }
    try {
      const response = await fetch(`/api/admin/help/categories?collectionId=${targetCollectionId}`)
      if (!response.ok) throw new Error('Failed to fetch categories')
      const data = await response.json()
      const fetchedCategories = data.categories || []
      setCategories(fetchedCategories)
      return fetchedCategories
    } catch (error) {
      console.error('Error fetching categories:', error)
      return []
    }
  }

  const fetchAllCategories = async () => {
    try {
      const response = await fetch('/api/admin/help/categories')
      if (!response.ok) {
        console.error('Failed to fetch categories:', response.status, response.statusText)
        throw new Error('Failed to fetch categories')
      }
      const data = await response.json()
      const allCategories = data.categories || []
      console.log('Fetched all categories:', allCategories.length)
      setModalCategories(allCategories)
      return allCategories
    } catch (error) {
      console.error('Error fetching all categories:', error)
      toastError('Failed to load categories')
      return []
    }
  }

  const generateUniqueSlug = async (baseSlug: string, categoryId: string): Promise<string> => {
    let slug = baseSlug
    let counter = 1

    while (true) {
      const response = await fetch(`/api/admin/help/articles/check-slug?slug=${encodeURIComponent(slug)}&categoryId=${categoryId}`)
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
    setNewArticle({ ...newArticle, title })
    
    if (title.trim() && newArticle.categoryId) {
      setCheckingSlug(true)
      try {
        const baseSlug = slugify(title)
        const uniqueSlug = await generateUniqueSlug(baseSlug, newArticle.categoryId)
        setNewArticle((prev) => ({ ...prev, slug: uniqueSlug }))
      } catch (error) {
        console.error('Error generating slug:', error)
      } finally {
        setCheckingSlug(false)
      }
    }
  }

  const fetchArticles = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (selectedCategory) params.set('categoryId', selectedCategory)
      if (statusFilter !== 'ALL') params.set('status', statusFilter)
      params.set('locale', defaultLocale)

      const response = await fetch(`/api/admin/help/articles?${params.toString()}`)
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch articles')
      }

      const data = await response.json()
      let filtered = data.articles || []

      // Client-side search filter
      if (searchQuery) {
        filtered = filtered.filter((article: Article) =>
          article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          article.slug.toLowerCase().includes(searchQuery.toLowerCase())
        )
      }

      setArticles(filtered)
    } catch (error) {
      console.error('Error fetching articles:', error)
      toastError('Failed to fetch articles')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCollections()
  }, [])

  useEffect(() => {
    if (selectedCollection) {
      fetchCategories(selectedCollection)
    } else {
      setCategories([])
    }
  }, [selectedCollection])

  useEffect(() => {
    fetchArticles()
  }, [selectedCategory, statusFilter, searchQuery])

  useEffect(() => {
    if (showAddModal) {
      // Load categories when modal opens or when collection changes
      const loadCategories = async () => {
        console.log('Loading categories, collectionId:', newArticle.collectionId)
        let cats: Category[] = []
        if (newArticle.collectionId) {
          cats = await fetchCategories(newArticle.collectionId)
        } else {
          cats = await fetchAllCategories()
        }
        console.log('Loaded categories:', cats.length, cats)
        setModalCategories(cats)
      }
      loadCategories()
    } else {
      // Reset modal state when closing
      setNewArticle({ title: '', categoryId: '', slug: '', collectionId: '' })
      setModalCategories([])
    }
  }, [showAddModal, newArticle.collectionId])

  const handleCreate = async () => {
    if (!newArticle.title.trim()) {
      toastError('Title is required')
      return
    }

    if (!newArticle.categoryId) {
      toastError('Category is required')
      return
    }

    if (!newArticle.slug.trim()) {
      toastError('Slug is required')
      return
    }

    setCreating(true)
    try {
      const response = await fetch('/api/admin/help/articles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          categoryId: newArticle.categoryId,
          slug: newArticle.slug,
          title: newArticle.title,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to create article')
      }

      const data = await response.json()
      router.push(`/admin/help/articles/${data.article.id}`)
    } catch (error: any) {
      console.error('Error creating article:', error)
      toastError(error.message || 'Failed to create article')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteDialog.articleId) return

    try {
      const response = await fetch(`/api/admin/help/articles/${deleteDialog.articleId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete article')
      }

      toastSuccess('Article deleted')
      setDeleteDialog({ open: false, articleId: null })
      fetchArticles()
    } catch (error: any) {
      toastError(error.message || 'Failed to delete article')
    }
  }

  const handlePublish = async (articleId: string) => {
    try {
      const response = await fetch(`/api/admin/help/articles/${articleId}/publish`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to publish article')
      }

      toastSuccess('Article published')
      fetchArticles()
    } catch (error: any) {
      toastError(error.message || 'Failed to publish article')
    }
  }

  const handleUnpublish = async (articleId: string) => {
    try {
      const response = await fetch(`/api/admin/help/articles/${articleId}/unpublish`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to unpublish article')
      }

      toastSuccess('Article unpublished')
      fetchArticles()
    } catch (error: any) {
      toastError(error.message || 'Failed to unpublish article')
    }
  }

  if (loading && !selectedCollection) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Help Articles</h1>
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Article
        </Button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Collection
            </label>
            <select
              value={selectedCollection}
              onChange={(e) => {
                setSelectedCollection(e.target.value)
                setSelectedCategory('')
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All collections</option>
              {collections.map((col) => (
                <option key={col.id} value={col.id}>
                  {col.i18n?.find((i) => i.locale === 'fr')?.title || col.slug}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              disabled={!selectedCollection}
            >
              <option value="">All categories</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.i18n?.find((i) => i.locale === 'fr')?.title || cat.slug}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ContentStatus | 'ALL')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="ALL">All</option>
              <option value="DRAFT">Draft</option>
              <option value="PUBLISHED">Published</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search articles..."
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={(e) => {
          // Close modal if clicking on backdrop
          if (e.target === e.currentTarget) {
            setShowAddModal(false)
          }
        }}>
          <div className="bg-white rounded-lg p-6 w-full max-w-md relative z-50" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-xl font-semibold mb-4">Create Article</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  value={newArticle.title}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="Titre de l'article"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Collection (optional)
                </label>
                <select
                  value={newArticle.collectionId}
                  onChange={async (e) => {
                    const collectionId = e.target.value
                    console.log('Collection changed:', collectionId)
                    setNewArticle((prev) => ({ ...prev, collectionId, categoryId: '' }))
                    // Load categories for the selected collection
                    if (collectionId) {
                      const cats = await fetchCategories(collectionId)
                      console.log('Categories loaded for collection:', cats.length)
                      setModalCategories(cats)
                    } else {
                      const cats = await fetchAllCategories()
                      console.log('All categories loaded:', cats.length)
                      setModalCategories(cats)
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="">All collections</option>
                  {collections.map((col) => (
                    <option key={col.id} value={col.id}>
                      {col.i18n?.find((i) => i.locale === 'fr')?.title || col.slug}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category *
                </label>
                <select
                  value={newArticle.categoryId}
                  onChange={(e) => {
                    const categoryId = e.target.value
                    console.log('Category selected:', categoryId, 'from options:', modalCategories.length)
                    setNewArticle((prev) => {
                      const updated = { ...prev, categoryId }
                      // Regenerate slug if title exists and category is selected
                      if (updated.title.trim() && categoryId) {
                        // Trigger slug generation after state update
                        setTimeout(() => {
                          handleTitleChange(updated.title)
                        }, 100)
                      }
                      return updated
                    })
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  style={{ pointerEvents: 'auto', zIndex: 10 }}
                >
                  <option value="">Select category</option>
                  {modalCategories.length > 0 ? (
                    modalCategories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.i18n?.find((i) => i.locale === 'fr')?.title || cat.slug}
                        {cat.collection?.i18n?.[0]?.title && ` (${cat.collection.i18n[0].title})`}
                      </option>
                    ))
                  ) : (
                    <option value="" disabled>No categories available</option>
                  )}
                </select>
                {modalCategories.length === 0 && showAddModal && (
                  <p className="text-xs text-gray-500 mt-1">Loading categories...</p>
                )}
                {modalCategories.length > 0 && (
                  <p className="text-xs text-gray-500 mt-1">
                    {modalCategories.length} categor{modalCategories.length > 1 ? 'ies' : 'y'} available
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Slug {checkingSlug && <span className="text-xs text-gray-500">(generating...)</span>}
                </label>
                <input
                  type="text"
                  value={newArticle.slug}
                  onChange={(e) =>
                    setNewArticle({ ...newArticle, slug: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                  placeholder="Auto-generated from title"
                  readOnly
                />
                <p className="text-xs text-gray-500 mt-1">Auto-generated and unique</p>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <Button variant="outline" onClick={() => setShowAddModal(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleCreate} 
                disabled={creating || !newArticle.title.trim() || !newArticle.categoryId || !newArticle.slug.trim()}
              >
                {creating ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Articles Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Title
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Collection / Category
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Updated
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {articles.map((article) => (
              <tr key={article.id}>
                <td className="px-6 py-4">
                  <Link
                    href={`/admin/help/articles/${article.id}`}
                    className="text-sm font-medium text-indigo-600 hover:text-indigo-900"
                  >
                    {article.title || article.slug}
                  </Link>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {article.category?.collection?.i18n?.[0]?.title || article.category?.collection?.slug || '-'} /{' '}
                  {article.category?.i18n?.[0]?.title || article.category?.slug || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <button
                    onClick={() =>
                      article.status === 'PUBLISHED'
                        ? handleUnpublish(article.id)
                        : handlePublish(article.id)
                    }
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      article.status === 'PUBLISHED'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {article.status === 'PUBLISHED' ? (
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
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(article.updatedAt).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div className="flex justify-end gap-2">
                    <Link
                      href={`/admin/help/articles/${article.id}`}
                      className="text-indigo-600 hover:text-indigo-900"
                    >
                      <Edit className="w-4 h-4" />
                    </Link>
                    <button
                      onClick={() => setDeleteDialog({ open: true, articleId: article.id })}
                      className="text-red-600 hover:text-red-900"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {articles.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No articles found.</p>
          </div>
        )}
      </div>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteDialog.open}
        onOpenChange={(open) =>
          setDeleteDialog({ open, articleId: deleteDialog.articleId })
        }
        title="Delete Article"
        description="Are you sure you want to delete this article? This action cannot be undone."
        onConfirm={handleDelete}
      />
    </div>
  )
}

