'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Plus, Search, Edit, Trash2, Eye, EyeOff, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ContentStatus } from '@prisma/client'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import CreateHelpArticleModal from '@/components/admin/CreateHelpArticleModal'
import CreateAcademyArticleModal from '@/components/admin/CreateAcademyArticleModal'
import { defaultLocale } from '@/config/locales'
import {
  ARTICLE_TYPES,
  ARTICLE_TYPE_KEYS,
  type ArticleTypeKey,
  normalizeArticleType,
} from '@/lib/admin/articleTypes'

interface Article {
  id: string
  slug: string
  status: ContentStatus
  publishedAt: string | null
  createdAt: string
  updatedAt: string
  authorName: string
  authorRole: string | null
  coverUrl: string
  title: string
  locale: string
  isFeatured: boolean
  isHighlighted: boolean
  articleType: ArticleTypeKey
}

export default function AdminArticlesPage() {
  const router = useRouter()
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<ContentStatus | 'ALL'>('ALL')
  const [localeFilter, setLocaleFilter] = useState<string>(defaultLocale)
  const [typeFilter, setTypeFilter] = useState<ArticleTypeKey | 'ALL'>('ALL')
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; articleId: string | null }>({
    open: false,
    articleId: null,
  })
  const [helpCreateOpen, setHelpCreateOpen] = useState(false)
  const [academyCreateOpen, setAcademyCreateOpen] = useState(false)
  const [createMenuOpen, setCreateMenuOpen] = useState(false)
  const createMenuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!createMenuOpen) return
    const onClick = (e: MouseEvent) => {
      if (!createMenuRef.current) return
      if (!createMenuRef.current.contains(e.target as Node)) setCreateMenuOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setCreateMenuOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [createMenuOpen])

  const fetchArticles = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (searchQuery) params.set('search', searchQuery)
      if (statusFilter !== 'ALL') params.set('status', statusFilter)
      if (typeFilter !== 'ALL') params.set('articleType', typeFilter)
      params.set('locale', localeFilter)

      const response = await fetch(`/api/admin/articles?${params.toString()}`)
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch articles')
      }

      const data = await response.json()
      setArticles(
        (data.articles || []).map((article: any) => ({
          ...article,
          articleType: normalizeArticleType(article?.articleType),
        }))
      )
    } catch (error) {
      console.error('Error fetching articles:', error)
      toastError('Failed to fetch articles')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchArticles()
  }, [searchQuery, statusFilter, localeFilter, typeFilter, router])

  const handleCreateArticle = async (articleType: ArticleTypeKey) => {
    if (articleType === 'HELP') {
      // HELP nécessite collection + category + helpSlug → modal dédié
      // (Phase 3.3.C). Ne pas faire un POST direct.
      setHelpCreateOpen(true)
      return
    }
    if (articleType === 'ACADEMY') {
      // ACADEMY nécessite collection + category + academySlug → modal dédié
      // (Phase 4 — symétrique HELP). Ne pas faire un POST direct.
      setAcademyCreateOpen(true)
      return
    }
    try {
      const descriptor = ARTICLE_TYPES[articleType]
      const slug = `${descriptor.slugPrefix}-${Date.now()}`
      const response = await fetch('/api/admin/articles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slug,
          authorName: 'Author',
          articleType,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to create article')
      }

      const data = await response.json()
      router.push(`/admin/articles/${data.article.id}`)
    } catch (error: any) {
      toastError(error.message || 'Failed to create article')
    }
  }

  const handlePublish = async (articleId: string) => {
    try {
      const response = await fetch(`/api/admin/articles/${articleId}/publish`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to publish article')
      }

      const data = await response.json()
      if (data.warning) {
        toastError(data.warning)
      } else {
        toastSuccess('Article published')
      }
      fetchArticles()
    } catch (error: any) {
      toastError(error.message || 'Failed to publish article')
    }
  }

  const handleUnpublish = async (articleId: string) => {
    try {
      const response = await fetch(`/api/admin/articles/${articleId}/unpublish`, {
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

  const handleDelete = async () => {
    if (!deleteDialog.articleId) return

    try {
      const response = await fetch(`/api/admin/articles/${deleteDialog.articleId}`, {
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading articles...</div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Articles</h1>
        <div className="relative" ref={createMenuRef}>
          <Button
            type="button"
            onClick={() => setCreateMenuOpen((o) => !o)}
            aria-haspopup="menu"
            aria-expanded={createMenuOpen}
          >
            <Plus className="w-4 h-4 mr-2" />
            Nouvel article
            <ChevronDown className="w-4 h-4 ml-2" />
          </Button>
          {createMenuOpen && (
            <div
              role="menu"
              className="absolute right-0 top-full z-50 mt-1 w-72 rounded-md border border-gray-200 bg-white p-1 shadow-lg"
            >
              {ARTICLE_TYPE_KEYS.map((key) => {
                const descriptor = ARTICLE_TYPES[key]
                return (
                  <button
                    key={key}
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setCreateMenuOpen(false)
                      handleCreateArticle(key)
                    }}
                    className="flex w-full flex-col items-start gap-0.5 rounded-sm px-2 py-1.5 text-left hover:bg-gray-100"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-1.5 py-0.5 text-[10px] font-semibold rounded ${descriptor.badgeClassName}`}
                      >
                        {descriptor.label}
                      </span>
                      <span className="text-sm font-medium">{descriptor.createLabel}</span>
                    </div>
                    <span className="text-xs text-gray-500 leading-tight">{descriptor.description}</span>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search by title..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as ArticleTypeKey | 'ALL')}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="ALL">All Types</option>
            {ARTICLE_TYPE_KEYS.map((key) => (
              <option key={key} value={key}>
                {ARTICLE_TYPES[key].label}
              </option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as ContentStatus | 'ALL')}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="ALL">All Status</option>
            <option value="DRAFT">Draft</option>
            <option value="PUBLISHED">Published</option>
          </select>
          <select
            value={localeFilter}
            onChange={(e) => setLocaleFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="fr">FR</option>
            <option value="en">EN</option>
            <option value="ar">AR</option>
            <option value="it">IT</option>
          </select>
        </div>
      </div>

      {/* Featured & Highlighted Articles */}
      {(articles.some((a) => a.isFeatured || a.isHighlighted)) && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mb-6">
          <div className="bg-indigo-50 px-6 py-3 border-b border-indigo-200">
            <h2 className="text-lg font-semibold text-indigo-900">Featured & Highlighted Articles</h2>
            <p className="text-sm text-indigo-700">Articles prominently displayed on the blog page</p>
          </div>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cover
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Author
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Published
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {articles
                .filter((a) => a.isFeatured || a.isHighlighted)
                .sort((a, b) => {
                  // Featured first, then highlighted
                  if (a.isFeatured && !b.isFeatured) return -1
                  if (!a.isFeatured && b.isFeatured) return 1
                  return 0
                })
                .map((article) => (
                  <tr key={article.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      {article.coverUrl ? (
                        <img
                          src={article.coverUrl}
                          alt={article.title}
                          className="w-16 h-16 object-cover rounded"
                        />
                      ) : (
                        <div className="w-16 h-16 bg-gray-200 rounded flex items-center justify-center text-gray-400 text-xs">
                          No image
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-medium text-gray-900">{article.title}</div>
                        {article.isFeatured && (
                          <span className="px-2 py-0.5 text-xs font-semibold bg-yellow-100 text-yellow-800 rounded-full">
                            Featured
                          </span>
                        )}
                        {article.isHighlighted && (
                          <span className="px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-800 rounded-full">
                            Highlighted
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-gray-500">{article.slug}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{article.authorName}</div>
                      {article.authorRole && (
                        <div className="text-sm text-gray-500">{article.authorRole}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-semibold rounded-full ${ARTICLE_TYPES[article.articleType].badgeClassName}`}
                      >
                        {ARTICLE_TYPES[article.articleType].label}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          article.status === 'PUBLISHED'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {article.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {article.publishedAt
                        ? new Date(article.publishedAt).toLocaleDateString()
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end gap-2">
                        <Link
                          href={`/admin/articles/${article.id}`}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          <Edit className="w-4 h-4" />
                        </Link>
                        {article.status === 'DRAFT' ? (
                          <button
                            onClick={() => handlePublish(article.id)}
                            className="text-green-600 hover:text-green-900"
                            title="Publish"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleUnpublish(article.id)}
                            className="text-orange-600 hover:text-orange-900"
                            title="Unpublish"
                          >
                            <EyeOff className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => setDeleteDialog({ open: true, articleId: article.id })}
                          className="text-red-600 hover:text-red-900"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Other Articles */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-6 py-3 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">All Articles</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cover
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Title
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Author
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Published
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {articles.filter((a) => !a.isFeatured && !a.isHighlighted).length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                  {articles.length === 0
                    ? 'No articles found. Create your first article!'
                    : 'No other articles. All articles are featured or highlighted.'}
                </td>
              </tr>
            ) : (
              articles
                .filter((a) => !a.isFeatured && !a.isHighlighted)
                .map((article) => (
                  <tr key={article.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      {article.coverUrl ? (
                        <img
                          src={article.coverUrl}
                          alt={article.title}
                          className="w-16 h-16 object-cover rounded"
                        />
                      ) : (
                        <div className="w-16 h-16 bg-gray-200 rounded flex items-center justify-center text-gray-400 text-xs">
                          No image
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">{article.title}</div>
                      <div className="text-sm text-gray-500">{article.slug}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{article.authorName}</div>
                      {article.authorRole && (
                        <div className="text-sm text-gray-500">{article.authorRole}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-semibold rounded-full ${ARTICLE_TYPES[article.articleType].badgeClassName}`}
                      >
                        {ARTICLE_TYPES[article.articleType].label}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          article.status === 'PUBLISHED'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {article.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {article.publishedAt
                        ? new Date(article.publishedAt).toLocaleDateString()
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end gap-2">
                        <Link
                          href={`/admin/articles/${article.id}`}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          <Edit className="w-4 h-4" />
                        </Link>
                        {article.status === 'DRAFT' ? (
                          <button
                            onClick={() => handlePublish(article.id)}
                            className="text-green-600 hover:text-green-900"
                            title="Publish"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleUnpublish(article.id)}
                            className="text-orange-600 hover:text-orange-900"
                            title="Unpublish"
                          >
                            <EyeOff className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => setDeleteDialog({ open: true, articleId: article.id })}
                          className="text-red-600 hover:text-red-900"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={deleteDialog.open}
        onOpenChange={(open) => setDeleteDialog({ open, articleId: null })}
        title="Delete Article"
        description="This action will permanently delete the article and all its content. This cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={handleDelete}
        destructive
      />

      <CreateHelpArticleModal
        open={helpCreateOpen}
        onClose={() => {
          setHelpCreateOpen(false)
          fetchArticles()
        }}
      />

      <CreateAcademyArticleModal
        open={academyCreateOpen}
        onClose={() => {
          setAcademyCreateOpen(false)
          fetchArticles()
        }}
      />
    </div>
  )
}

