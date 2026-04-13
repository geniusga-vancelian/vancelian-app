'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { MediaField } from '@/components/admin/MediaField'
import { ContentStatus } from '@prisma/client'
import { supportedLocales, type Locale, defaultLocale } from '@/config/locales'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { TranslateModal } from '@/components/admin/TranslateModal'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'

type HelpTagType = 'THEMATIC_CATEGORY' | 'INVESTMENT_TYPE' | 'EXCLUSIVE_OFFER'

type HelpArticleTag = {
  type: HelpTagType
  id: string
  slug: string
  label: string
}

type HelpTagOption = HelpArticleTag & {
  groupLabel: string
}

interface Article {
  id: string
  slug: string
  status: ContentStatus
  publishedAt: string | null
  coverMediaId: string | null
  authorName: string | null
  allowAnchors: boolean
  category?: {
    id: string
    slug: string
    collection?: {
      slug: string
    }
  }
  i18n: Array<{
    id: string
    locale: string
    title: string
    standfirst: string | null
    contentMarkdown: string | null
    metaTitle: string | null
    metaDescription: string | null
    translationStatus?: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
  }>
  targetTags?: HelpArticleTag[]
}

export default function AdminHelpArticleEditorPage() {
  const router = useRouter()
  const params = useParams()
  const articleId = (params?.id as string | undefined) ?? ''

  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selectedLocale, setSelectedLocale] = useState<Locale>(defaultLocale)
  const [showTranslateModal, setShowTranslateModal] = useState(false)
  const [approving, setApproving] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [tagOptions, setTagOptions] = useState<HelpTagOption[]>([])
  const [isAddTagOpen, setIsAddTagOpen] = useState(false)
  const [selectedTagKey, setSelectedTagKey] = useState('')
  const [i18nData, setI18nData] = useState({
    title: '',
    standfirst: '',
    contentMarkdown: '',
    metaTitle: '',
    metaDescription: '',
  })
  const [settings, setSettings] = useState({
    slug: '',
    authorName: '',
    coverMediaId: '',
    allowAnchors: true,
    publishedAt: '',
    targetTags: [] as HelpArticleTag[],
  })

  const fetchArticle = async () => {
    setLoading(true)
    try {
      const response = await fetch(
        `/api/admin/help/articles/${articleId}?locale=${selectedLocale}&t=${Date.now()}`,
        { cache: 'no-store' }
      )
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch article')
      }

      const data = await response.json()
      setArticle(data.article)

      const i18n = data.article.i18n[0]
      if (i18n) {
        setI18nData({
          title: i18n.title || '',
          standfirst: i18n.standfirst || '',
          contentMarkdown: i18n.contentMarkdown || '',
          metaTitle: i18n.metaTitle || '',
          metaDescription: i18n.metaDescription || '',
        })
      }

      setSettings({
        slug: data.article.slug,
        authorName: data.article.authorName || '',
        coverMediaId: data.article.coverMediaId || '',
        allowAnchors: data.article.allowAnchors ?? true,
        publishedAt: data.article.publishedAt
          ? new Date(data.article.publishedAt).toISOString().slice(0, 16)
          : '',
        targetTags: Array.isArray(data.article.targetTags) ? data.article.targetTags : [],
      })
    } catch (error) {
      console.error('Error fetching article:', error)
      toastError('Failed to fetch article')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (articleId) {
      fetchArticle()
    }
  }, [articleId, selectedLocale])

  useEffect(() => {
    const fetchTagOptions = async () => {
      try {
        const response = await fetch(
          `/api/admin/help/tag-options?locale=${selectedLocale}&t=${Date.now()}`,
          { cache: 'no-store' }
        )
        if (!response.ok) {
          if (response.status === 401) {
            router.push('/admin/login')
            return
          }
          throw new Error('Failed to fetch tag options')
        }
        const data = await response.json()
        setTagOptions(Array.isArray(data.options) ? data.options : [])
      } catch (error) {
        console.error('Error fetching tag options:', error)
        setTagOptions([])
      }
    }
    fetchTagOptions()
  }, [router, selectedLocale])

  const handleSaveSettings = async () => {
    if (!article) return

    setSaving(true)
    try {
      let tagsErrorMessage: string | null = null
      let settingsErrorMessage: string | null = null

      const tagResponse = await fetch(`/api/admin/help/articles/${articleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          targetTags: settings.targetTags,
        }),
      })
      if (!tagResponse.ok) {
        const error = await tagResponse.json()
        tagsErrorMessage = error.error || 'Failed to save tags'
      } else {
        const tagData = await tagResponse.json()
        if (Array.isArray(tagData?.article?.targetTags)) {
          setSettings((prev) => ({ ...prev, targetTags: tagData.article.targetTags }))
        }
      }

      const payload: any = {
        slug: settings.slug,
        authorName: settings.authorName || null,
        coverMediaId: settings.coverMediaId || null,
        allowAnchors: settings.allowAnchors,
        publishedAt: settings.publishedAt ? new Date(settings.publishedAt).toISOString() : null,
      }

      const response = await fetch(`/api/admin/help/articles/${articleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const error = await response.json()
        settingsErrorMessage = error.error || 'Failed to save settings'
      }

      if (tagsErrorMessage || settingsErrorMessage) {
        const parts = [tagsErrorMessage, settingsErrorMessage].filter(Boolean)
        toastError(`Settings partially saved: ${parts.join(' | ')}`)
      } else {
        toastSuccess('Settings saved')
      }
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveContent = async () => {
    if (!article) return

    if (!i18nData.title.trim()) {
      toastError('Title is required')
      return
    }

    setSaving(true)
    try {
      // Persist tags with content save as well, so user workflow is consistent.
      const settingsResponse = await fetch(`/api/admin/help/articles/${articleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          targetTags: settings.targetTags,
        }),
      })
      if (!settingsResponse.ok) {
        const error = await settingsResponse.json()
        throw new Error(error.error || 'Failed to save tags')
      }

      const response = await fetch(`/api/admin/help/articles/${articleId}/i18n`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          locale: selectedLocale,
          ...i18nData,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to save content')
      }

      toastSuccess('Content saved')
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to save content')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    try {
      const response = await fetch(`/api/admin/help/articles/${articleId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete article')
      }

      toastSuccess('Article deleted')
      router.push('/admin/help/articles')
    } catch (error: any) {
      toastError(error.message || 'Failed to delete article')
    }
  }

  const handlePublish = async () => {
    try {
      const response = await fetch(`/api/admin/help/articles/${articleId}/publish`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to publish article')
      }

      toastSuccess('Article published')
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to publish article')
    }
  }

  const handleUnpublish = async () => {
    try {
      const response = await fetch(`/api/admin/help/articles/${articleId}/unpublish`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to unpublish article')
      }

      toastSuccess('Article unpublished')
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to unpublish article')
    }
  }

  if (loading) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (!article) {
    return <div className="text-center py-12">Article not found</div>
  }

  const currentI18n = article.i18n.find((i) => i.locale === selectedLocale)
  const selectedTagKeys = new Set(settings.targetTags.map((tag) => `${tag.type}:${tag.id}`))
  const availableTagOptions = tagOptions.filter((option) => !selectedTagKeys.has(`${option.type}:${option.id}`))

  const addSelectedTag = () => {
    if (!selectedTagKey) return
    const option = availableTagOptions.find((item) => `${item.type}:${item.id}` === selectedTagKey)
    if (!option) return
    setSettings((prev) => ({
      ...prev,
      targetTags: [
        ...prev.targetTags,
        { type: option.type, id: option.id, slug: option.slug, label: option.label },
      ],
    }))
    setSelectedTagKey('')
    setIsAddTagOpen(false)
  }

  const removeTag = (type: HelpTagType, id: string) => {
    setSettings((prev) => ({
      ...prev,
      targetTags: prev.targetTags.filter((tag) => !(tag.type === type && tag.id === id)),
    }))
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/admin/help/articles" className="text-indigo-600 hover:text-indigo-900 mb-2 inline-block">
            ← Back to Articles
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Edit Article</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowDeleteDialog(true)}>
            Delete
          </Button>
          {article.status === 'PUBLISHED' ? (
            <Button variant="outline" onClick={handleUnpublish}>
              Unpublish
            </Button>
          ) : (
            <Button onClick={handlePublish}>Publish</Button>
          )}
        </div>
      </div>

      {/* Locale Selector */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">Locale:</label>
            <select
              value={selectedLocale}
              onChange={(e) => setSelectedLocale(e.target.value as Locale)}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              {supportedLocales.map((loc) => (
                <option key={loc} value={loc}>
                  {loc.toUpperCase()}
                </option>
              ))}
            </select>
            {currentI18n && (
              <span
                className={`text-xs px-2 py-1 rounded ${
                  currentI18n.translationStatus === 'ORIGINAL'
                    ? 'bg-blue-100 text-blue-800'
                    : currentI18n.translationStatus === 'MACHINE'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-green-100 text-green-800'
                }`}
              >
                {currentI18n.translationStatus}
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowTranslateModal(true)}
            >
              Auto-translate
            </Button>
            {currentI18n?.translationStatus === 'MACHINE' && (
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  setApproving(true)
                  try {
                    const response = await fetch('/api/admin/translate/approve', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        entityType: 'HELP_ARTICLE',
                        entityId: articleId,
                        locale: selectedLocale,
                      }),
                    })
                    if (!response.ok) throw new Error('Failed to approve')
                    toastSuccess('Translation approved')
                    await fetchArticle()
                  } catch (error) {
                    toastError('Failed to approve translation')
                  } finally {
                    setApproving(false)
                  }
                }}
                disabled={approving}
              >
                {approving ? 'Approving...' : 'Approve'}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Settings */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Settings</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Slug</label>
            <input
              type="text"
              value={settings.slug}
              onChange={(e) => setSettings({ ...settings, slug: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Author Name</label>
            <input
              type="text"
              value={settings.authorName}
              onChange={(e) => setSettings({ ...settings, authorName: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cover Image</label>
            <MediaField
              value={settings.coverMediaId || undefined}
              onChange={(mediaId) => setSettings({ ...settings, coverMediaId: mediaId || '' })}
              allowClear
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Published At (datetime-local)
            </label>
            <input
              type="datetime-local"
              value={settings.publishedAt}
              onChange={(e) => setSettings({ ...settings, publishedAt: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={settings.allowAnchors}
              onChange={(e) => setSettings({ ...settings, allowAnchors: e.target.checked })}
              className="mr-2"
            />
            <label className="text-sm text-gray-700">Allow anchors (TOC)</label>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">Tags</label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsAddTagOpen((prev) => !prev)}
              >
                Add a tag
              </Button>
            </div>

            {settings.targetTags.length > 0 ? (
              <div className="flex flex-wrap gap-2 mb-3">
                {settings.targetTags.map((tag) => (
                  <span
                    key={`${tag.type}:${tag.id}`}
                    className="inline-flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1 text-xs text-indigo-700"
                  >
                    <span className="font-medium">{tag.label}</span>
                    <span className="text-indigo-400">({tag.type})</span>
                    <button
                      type="button"
                      onClick={() => removeTag(tag.type, tag.id)}
                      className="text-indigo-500 hover:text-indigo-700"
                      aria-label={`Remove tag ${tag.label}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500 mb-3">No tags selected for this article.</p>
            )}

            {isAddTagOpen && (
              <div className="flex items-center gap-2">
                <select
                  value={selectedTagKey}
                  onChange={(e) => setSelectedTagKey(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="">Select a tag source...</option>
                  {availableTagOptions.map((option) => (
                    <option key={`${option.type}:${option.id}`} value={`${option.type}:${option.id}`}>
                      [{option.groupLabel}] {option.label}
                    </option>
                  ))}
                </select>
                <Button type="button" onClick={addSelectedTag} disabled={!selectedTagKey}>
                  Add
                </Button>
              </div>
            )}
          </div>
        </div>
        <div className="mt-4">
          <Button onClick={handleSaveSettings} disabled={saving}>
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>
      </div>

      {/* Header Content */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Header Content ({selectedLocale.toUpperCase()})</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
            <input
              type="text"
              value={i18nData.title}
              onChange={(e) => setI18nData({ ...i18nData, title: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Standfirst</label>
            <textarea
              value={i18nData.standfirst}
              onChange={(e) => setI18nData({ ...i18nData, standfirst: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Article Content (Markdown)
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Write the full article in one markdown textarea. Rendered as markdown in Flutter app.
            </p>
            <textarea
              value={i18nData.contentMarkdown}
              onChange={(e) => setI18nData({ ...i18nData, contentMarkdown: e.target.value })}
              rows={16}
              className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
              placeholder="# Heading\n\nYour paragraph in **markdown**..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Meta Title</label>
            <input
              type="text"
              value={i18nData.metaTitle}
              onChange={(e) => setI18nData({ ...i18nData, metaTitle: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Meta Description</label>
            <textarea
              value={i18nData.metaDescription}
              onChange={(e) => setI18nData({ ...i18nData, metaDescription: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <Button onClick={handleSaveContent} disabled={saving}>
          {saving ? 'Saving...' : 'Save Content'}
        </Button>
      </div>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Article"
        description="Are you sure you want to delete this article? This action cannot be undone."
        onConfirm={handleDelete}
      />

      {/* Translate Modal */}
      {showTranslateModal && (
        <TranslateModal
          open={showTranslateModal}
          onOpenChange={setShowTranslateModal}
          sourceLocale={selectedLocale}
          onTranslate={async ({ sourceLocale, targetLocales, mode }) => {
            const response = await fetch('/api/admin/translate/help-article', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                articleId,
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
            await fetchArticle()
            return data
          }}
        />
      )}
    </div>
  )
}

