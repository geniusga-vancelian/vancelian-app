'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import ReactMarkdown from 'react-markdown'
import { Button } from '@/components/ui/button'
import { MediaField } from '@/components/admin/MediaField'
import { ContentStatus, ArticleBlockType } from '@prisma/client'
import { supportedLocales, type Locale, defaultLocale } from '@/config/locales'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { TranslateModal } from '@/components/admin/TranslateModal'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { MediaPicker } from '@/components/admin/MediaPicker'

interface Article {
  id: string
  slug: string
  status: ContentStatus
  publishedAt: string | null
  coverMediaId: string | null
  galleryMediaIds: string[] | null
  videoUrl: string | null
  categorySlugs: string[] | null
  documents: Array<{ mediaId: string; title: string }> | null
  isFeatured: boolean
  isHighlighted: boolean
  isMilestone: boolean
  coverTitle: string | null
  coverCredit: string | null
  coverSource: string | null
  authorName: string
  authorRole: string | null
  allowComments: boolean
  articleType: 'NEWS' | 'ANALYSIS'
  /** Champ serveur ; actualité entreprise (NEWS uniquement). */
  isCompanyNews?: boolean
  coverUrl: string
  projects?: Array<{
    id: string
    project: {
      id: string
      slug: string
      i18n: Array<{
        locale: string
        title: string
      }>
    }
  }>
  i18n: Array<{
    id: string
    locale: string
    title: string
    standfirst: string
    coverTitle: string | null
    metaTitle: string | null
    metaDescription: string | null
    translationStatus?: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
  }>
  blocks: Array<{
    id: string
    type: ArticleBlockType
    order: number
    data: any
  }>
}

export default function AdminArticleEditorPage() {
  const router = useRouter()
  const params = useParams()
  const articleId = (params?.id as string | undefined) ?? ''

  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selectedLocale, setSelectedLocale] = useState<Locale>(defaultLocale)
  const [showTranslateModal, setShowTranslateModal] = useState(false)
  const [hasGlossary, setHasGlossary] = useState(false)
  const [approving, setApproving] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showUnpublishDialog, setShowUnpublishDialog] = useState(false)
  const [i18nData, setI18nData] = useState({
    title: '',
    standfirst: '',
    coverTitle: '',
    metaTitle: '',
    metaDescription: '',
  })
  const [galleryMediaIds, setGalleryMediaIds] = useState<string[]>([])
  const [videoUrl, setVideoUrl] = useState<string>('')
  const [categorySlugs, setCategorySlugs] = useState<string[]>([])
  const [availableCategories, setAvailableCategories] = useState<Array<{ id: string; slug: string; label: string }>>([])
  const [articleBlogCategories, setArticleBlogCategories] = useState<Array<{ id: string; slug: string; label: string }>>([])
  const [isCompanyNews, setIsCompanyNews] = useState(false)
  const [linkedProjects, setLinkedProjects] = useState<Array<{ id: string; projectId: string; project: { id: string; slug: string; i18n: Array<{ locale: string; title: string }> } }>>([])
  const [linkedLinks, setLinkedLinks] = useState<Array<{ id: string; kind: string; targetId: string; label: string }>>([])
  const [allProjects, setAllProjects] = useState<Array<{ id: string; slug: string; i18n: Array<{ locale: string; title: string }> }>>([])
  const [projectSearch, setProjectSearch] = useState('')
  const [relatedSearch, setRelatedSearch] = useState('')
  const [relatedOptions, setRelatedOptions] = useState<Array<{ type: string; id?: string; symbol?: string; slug?: string; label: string }>>([])
  const [relatedOptionsOpen, setRelatedOptionsOpen] = useState(false)
  const [relatedSearchDebounce, setRelatedSearchDebounce] = useState<NodeJS.Timeout | null>(null)
  const relatedSectionRef = useRef<HTMLDivElement>(null)
  const [documents, setDocuments] = useState<Array<{ mediaId: string; title: string }>>([])
  const [isGalleryPickerOpen, setIsGalleryPickerOpen] = useState(false)
  const [isDocumentPickerOpen, setIsDocumentPickerOpen] = useState(false)
  const [galleryMediaMap, setGalleryMediaMap] = useState<Record<string, { url: string; filename: string }>>({})
  const [documentMediaMap, setDocumentMediaMap] = useState<Record<string, { url: string; filename: string }>>({})
  const [isFeatured, setIsFeatured] = useState(false)
  const [isHighlighted, setIsHighlighted] = useState(false)
  const [isMilestone, setIsMilestone] = useState(false)
  const [showFeaturedConfirm, setShowFeaturedConfirm] = useState(false)
  const [blocksDraft, setBlocksDraft] = useState<Article['blocks']>([])
  const [blocksDirty, setBlocksDirty] = useState(false)

  useEffect(() => {
    if (!articleId) return
    fetchArticle()
    fetchProjects()
    fetchLinkedLinks()
  }, [articleId])

  useEffect(() => {
    fetchCategories()
  }, [selectedLocale])

  useEffect(() => {
    if (!article) return
    const i18n = article.i18n.find((i) => i.locale === selectedLocale)
    if (i18n) {
      setI18nData({
        title: i18n.title || '',
        standfirst: i18n.standfirst || '',
        coverTitle: i18n.coverTitle || '',
        metaTitle: i18n.metaTitle || '',
        metaDescription: i18n.metaDescription || '',
      })
    } else {
      setI18nData({
        title: '',
        standfirst: '',
        coverTitle: '',
        metaTitle: '',
        metaDescription: '',
      })
    }
  }, [article, selectedLocale])

  // Refetch article when locale changes to get localized blocks
  useEffect(() => {
    if (article && !loading) {
      fetchArticle()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLocale])

  useEffect(() => {
    fetch('/api/admin/settings/translation')
      .then((res) => res.json())
      .then((data) => {
        setHasGlossary(!!data.settings?.translationGlossary)
      })
      .catch(() => setHasGlossary(false))
  }, [])

  const fetchArticle = async () => {
    try {
      const response = await fetch(`/api/admin/articles/${articleId}?locale=${selectedLocale}`)
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        if (response.status === 404) {
          router.push('/admin/articles')
          return
        }
        throw new Error('Failed to fetch article')
      }

      const data = await response.json()
      setArticle({
        ...data.article,
        articleType: data.article?.articleType === 'ANALYSIS' ? 'ANALYSIS' : 'NEWS',
        isCompanyNews: data.article?.isCompanyNews === true,
      })
      setIsCompanyNews(data.article?.isCompanyNews === true)
      setBlocksDraft(Array.isArray(data.article?.blocks) ? data.article.blocks : [])
      setBlocksDirty(false)
      // Update local state from article
      if (data.article) {
        setGalleryMediaIds(Array.isArray(data.article.galleryMediaIds) ? data.article.galleryMediaIds : [])
        setVideoUrl(data.article.videoUrl || '')
        setCategorySlugs(Array.isArray(data.article.categorySlugs) ? data.article.categorySlugs : [])
        setLinkedProjects(data.article.projects || [])
        setDocuments(Array.isArray(data.article.documents) ? data.article.documents : [])
        setIsFeatured(data.article.isFeatured || false)
        setIsHighlighted(data.article.isHighlighted || false)
        setIsMilestone(data.article.isMilestone || false)
        // Fetch media info for gallery and documents
        if (data.article.galleryMediaIds?.length) {
          fetchMediaInfo(data.article.galleryMediaIds, setGalleryMediaMap)
        }
        if (data.article.documents?.length) {
          const docMediaIds = data.article.documents.map((d: any) => d.mediaId)
          fetchMediaInfo(docMediaIds, setDocumentMediaMap)
        }
      }
    } catch (error) {
      console.error('Error fetching article:', error)
      toastError('Failed to fetch article')
    } finally {
      setLoading(false)
    }
  }

  const fetchCategories = async () => {
    try {
      const [invRes, blogRes] = await Promise.all([
        fetch('/api/admin/investment-categories'),
        fetch(`/api/admin/article-categories?locale=${encodeURIComponent(selectedLocale)}`),
      ])
      if (invRes.ok) {
        const data = await invRes.json()
        setAvailableCategories(data.categories || [])
      }
      if (blogRes.ok) {
        const data = await blogRes.json()
        setArticleBlogCategories(data.categories || [])
      }
    } catch (error) {
      console.error('Error fetching categories:', error)
    }
  }

  const fetchProjects = async () => {
    try {
      const response = await fetch('/api/admin/projects')
      if (response.ok) {
        const data = await response.json()
        setAllProjects(data.projects || [])
      }
    } catch (error) {
      console.error('Error fetching projects:', error)
    }
  }

  const fetchMediaInfo = async (mediaIds: string[], setter: React.Dispatch<React.SetStateAction<Record<string, { url: string; filename: string }>>>) => {
    try {
      const response = await fetch('/api/admin/media')
      if (response.ok) {
        const data = await response.json()
        const map: Record<string, { url: string; filename: string }> = {}
        mediaIds.forEach((id) => {
          const media = data.media?.find((m: any) => m.id === id)
          if (media) {
            map[id] = { url: media.url, filename: media.filename }
          }
        })
        setter(map)
      }
    } catch (error) {
      console.error('Error fetching media info:', error)
    }
  }

  const fetchLinkedProjects = async () => {
    if (!articleId) return
    try {
      const response = await fetch(`/api/admin/articles/${articleId}/projects`)
      if (response.ok) {
        const data = await response.json()
        setLinkedProjects(data.projects || [])
      }
    } catch (error) {
      console.error('Error fetching linked projects:', error)
    }
  }

  const fetchLinkedLinks = async () => {
    if (!articleId) return
    try {
      const response = await fetch(`/api/admin/articles/${articleId}/links`)
      if (response.ok) {
        const data = await response.json()
        setLinkedLinks(data.links || [])
      }
    } catch (error) {
      console.error('Error fetching linked links:', error)
    }
  }

  // Debounced search for related (projects, assets, vaults)
  useEffect(() => {
    if (relatedSearchDebounce) clearTimeout(relatedSearchDebounce)
    const t = setTimeout(async () => {
      const q = relatedSearch.trim()
      if (!q && relatedSearch.length > 0) {
        setRelatedOptions([])
        setRelatedOptionsOpen(false)
        return
      }
      try {
        const response = await fetch(`/api/admin/articles/related-search?q=${encodeURIComponent(q)}&limit=15`)
        if (response.ok) {
          const data = await response.json()
          const opts = (data.options || []).filter((opt: any) => {
            if (opt.type === 'project') return !linkedProjects.some((lp) => lp.projectId === opt.id)
            if (opt.type === 'asset') return !linkedLinks.some((l) => l.kind === 'ASSET' && l.targetId === opt.symbol)
            if (opt.type === 'vault') return !linkedLinks.some((l) => l.kind === 'VAULT' && l.targetId === opt.slug)
            return true
          })
          setRelatedOptions(opts)
          setRelatedOptionsOpen(opts.length > 0)
        } else {
          setRelatedOptions([])
          setRelatedOptionsOpen(false)
        }
      } catch {
        setRelatedOptions([])
        setRelatedOptionsOpen(false)
      }
    }, 300)
    setRelatedSearchDebounce(t)
    return () => { if (t) clearTimeout(t) }
  }, [relatedSearch, linkedProjects, linkedLinks])

  // Fermer la liste Related au clic en dehors (pas au blur, pour que le clic sur une option soit pris en compte)
  useEffect(() => {
    if (!relatedOptionsOpen) return
    const handleMouseDown = (e: MouseEvent) => {
      const target = e.target as Node
      if (relatedSectionRef.current && !relatedSectionRef.current.contains(target)) {
        setRelatedOptionsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [relatedOptionsOpen])

  const handleSaveSettings = async () => {
    if (!article) return

    setSaving(true)
    try {
      const payload: any = {
        slug: article.slug,
        coverMediaId:
          article.coverMediaId && String(article.coverMediaId).trim() !== ''
            ? article.coverMediaId
            : null,
        galleryMediaIds: galleryMediaIds.length > 0 ? galleryMediaIds : null,
        videoUrl: videoUrl || null,
        categorySlugs: categorySlugs.length > 0 ? categorySlugs : null,
        documents: documents.length > 0 ? documents : null,
        coverCredit: article.coverCredit,
        coverSource: article.coverSource,
        authorName: article.authorName,
        authorRole: article.authorRole,
        allowComments: article.allowComments,
        articleType: article.articleType,
        isCompanyNews: article.articleType === 'NEWS' ? isCompanyNews : false,
        publishedAt: article.publishedAt ? new Date(article.publishedAt).toISOString() : null,
      }

      // Only include isFeatured and isHighlighted if they are explicitly set
      if (typeof isFeatured === 'boolean') {
        payload.isFeatured = isFeatured
      }
      if (typeof isHighlighted === 'boolean') {
        payload.isHighlighted = isHighlighted
      }
      if (typeof isMilestone === 'boolean') {
        payload.isMilestone = isMilestone
      }

      const response = await fetch(`/api/admin/articles/${articleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const error = await response.json()
        const details = error.issues
          ? error.issues.map((issue: any) => `${issue.path.join('.')}: ${issue.message}`).join(', ')
          : error.message || error.error
        throw new Error(details || 'Failed to save settings')
      }

      toastSuccess('Settings saved')
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveContent = async () => {
    if (!article) return

    setSaving(true)
    try {
      // Save editorial flags first with a minimal payload.
      // This avoids unrelated settings validation issues blocking milestone persistence.
      const settingsPayload: any = {}

      // Only include isFeatured and isHighlighted if they are explicitly set
      if (typeof isFeatured === 'boolean') {
        settingsPayload.isFeatured = isFeatured
      }
      if (typeof isHighlighted === 'boolean') {
        settingsPayload.isHighlighted = isHighlighted
      }
      if (typeof isMilestone === 'boolean') {
        settingsPayload.isMilestone = isMilestone
      }
      settingsPayload.articleType = article.articleType
      settingsPayload.isCompanyNews = article.articleType === 'NEWS' ? isCompanyNews : false

      const settingsResponse = await fetch(`/api/admin/articles/${articleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsPayload),
      })

      if (!settingsResponse.ok) {
        const error = await settingsResponse.json()
        const details = error.issues
          ? error.issues.map((issue: any) => `${issue.path.join('.')}: ${issue.message}`).join(', ')
          : error.message || error.error
        throw new Error(details || 'Failed to save settings')
      }

      // Save localized content after settings.
      // If i18n validation fails, settings remain persisted.
      const hasRequiredI18nFields = i18nData.title.trim().length > 0 && i18nData.standfirst.trim().length > 0
      let i18nErrorMessage: string | null = null

      if (hasRequiredI18nFields) {
        const i18nResponse = await fetch(`/api/admin/articles/${articleId}/i18n`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            locale: selectedLocale,
            title: i18nData.title,
            standfirst: i18nData.standfirst,
            coverTitle: i18nData.coverTitle || undefined,
            metaTitle: i18nData.metaTitle || undefined,
            metaDescription: i18nData.metaDescription || undefined,
          }),
        })

        if (!i18nResponse.ok) {
          const error = await i18nResponse.json()
          console.error('Save i18n content error:', error)
          i18nErrorMessage = error.issues
            ? error.issues.map((issue: any) => `${issue.path.join('.')}: ${issue.message}`).join(', ')
            : error.error || 'Failed to save content'
        }
      } else {
        i18nErrorMessage = 'Title and Standfirst are required to save localized content.'
      }

      let blocksErrorMessage: string | null = null
      if (blocksDirty) {
        try {
          // Persist edited block drafts only when user explicitly clicks Save Content.
          const changedBlocks = blocksDraft.filter((draftBlock) => {
            const originalBlock = article.blocks.find((b) => b.id === draftBlock.id)
            if (!originalBlock) return false
            return JSON.stringify(originalBlock.data ?? {}) !== JSON.stringify(draftBlock.data ?? {})
          })

          for (const block of changedBlocks) {
            const response = await fetch(`/api/admin/articles/${articleId}/blocks/${block.id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ data: block.data }),
            })

            if (!response.ok) {
              const error = await response.json()
              throw new Error(error.error || `Failed to save block ${block.id}`)
            }
          }
        } catch (error: any) {
          blocksErrorMessage = error?.message || 'Failed to save article blocks'
        }
      }

      if (i18nErrorMessage || blocksErrorMessage) {
        const parts = [i18nErrorMessage, blocksErrorMessage].filter(Boolean)
        toastError(`Settings saved, but content was not fully updated: ${parts.join(' | ')}`)
      } else {
        toastSuccess('Content saved')
      }
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to save content')
    } finally {
      setSaving(false)
    }
  }

  const handlePublish = async () => {
    if (!article) return

    setSaving(true)
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
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'An error occurred')
    } finally {
      setSaving(false)
    }
  }

  const handleUnpublish = async () => {
    if (!article) return

    setSaving(true)
    try {
      const response = await fetch(`/api/admin/articles/${articleId}/unpublish`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to unpublish article')
      }

      toastSuccess('Article set to draft')
      await fetchArticle()
      setShowUnpublishDialog(false)
    } catch (error: any) {
      toastError(error.message || 'An error occurred')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!article) return

    setSaving(true)
    try {
      const response = await fetch(`/api/admin/articles/${articleId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete article')
      }

      toastSuccess('Article deleted')
      router.push('/admin/articles')
    } catch (error: any) {
      toastError(error.message || 'An error occurred')
      setSaving(false)
    }
  }

  const handleApproveTranslation = async () => {
    if (!article) return
    setApproving(true)
    try {
      const res = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityType: 'ARTICLE',
          entityId: article.id,
          locale: selectedLocale,
        }),
      })
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.error || 'Failed to approve translation')
      }
      toastSuccess('Translation approved')
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to approve translation')
    } finally {
      setApproving(false)
    }
  }

  const handleAddBlock = async (type: ArticleBlockType) => {
    if (!article) return

    const defaultData: any = {
      HEADING: { text: '' },
      PARAGRAPH: { text: '' },
      QUOTE: { text: '', author: '' },
      BULLET_LIST: { items: [''] },
      IMAGE: { mediaId: '', caption: '' },
      VIDEO: { url: '', caption: '' },
      DOCUMENT: { mediaId: '', title: '' },
    }

    try {
      const response = await fetch(`/api/admin/articles/${articleId}/blocks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type,
          data: defaultData[type] || {},
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to add block')
      }

      toastSuccess('Block added')
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to add block')
    }
  }

  const handleDeleteBlock = async (blockId: string) => {
    if (!confirm('Delete this block?')) return

    try {
      const response = await fetch(`/api/admin/articles/${articleId}/blocks/${blockId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete block')
      }

      toastSuccess('Block deleted')
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to delete block')
    }
  }

  const handleUpdateBlock = (blockId: string, data: any) => {
    setBlocksDraft((prev) =>
      prev.map((block) => (block.id === blockId ? { ...block, data } : block))
    )
    setBlocksDirty(true)
  }

  const handleReorderBlocks = async (blockIds: string[]) => {
    try {
      const response = await fetch(`/api/admin/articles/${articleId}/blocks/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orderedBlockIds: blockIds }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to reorder blocks')
      }

      toastSuccess('Blocks reordered')
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to reorder blocks')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading article...</div>
      </div>
    )
  }

  if (!article) {
    return null
  }

  const currentI18n = article.i18n.find((i) => i.locale === selectedLocale)
  const translationStatus = currentI18n?.translationStatus

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <Link href="/admin/articles" className="text-indigo-600 hover:text-indigo-900 mb-2 inline-block">
            ← Back to Articles
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Edit Article</h1>
          <div className="mt-2">
            <span
              className={`inline-flex px-2.5 py-1 text-xs font-semibold rounded-full ${
                article.articleType === 'ANALYSIS'
                  ? 'bg-purple-100 text-purple-800'
                  : 'bg-sky-100 text-sky-800'
              }`}
            >
              {article.articleType === 'ANALYSIS' ? 'Analysis' : 'News'}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <span
            className={`px-3 py-1 text-sm font-semibold rounded-full ${
              article.status === 'PUBLISHED'
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
            }`}
          >
            {article.status}
          </span>
          {article.status === 'DRAFT' ? (
            <Button onClick={handlePublish} disabled={saving} className="bg-green-600 hover:bg-green-700">
              Publish
            </Button>
          ) : (
            <Button
              onClick={() => setShowUnpublishDialog(true)}
              disabled={saving}
              className="bg-orange-600 hover:bg-orange-700"
            >
              Set to Draft
            </Button>
          )}
          <Button
            onClick={() => setShowDeleteDialog(true)}
            disabled={saving}
            className="bg-red-600 hover:bg-red-700"
          >
            Delete
          </Button>
        </div>
      </div>

      {/* Translation Controls - Global for entire article */}
      {article && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-medium text-gray-700">Language & Translation</h3>
            <div className="flex gap-2 items-center">
              <select
                value={selectedLocale}
                onChange={(e) => setSelectedLocale(e.target.value as Locale)}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm"
              >
                {supportedLocales.map((locale) => (
                  <option key={locale} value={locale}>
                    {locale.toUpperCase()}
                  </option>
                ))}
              </select>
              {translationStatus && (
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-1 text-xs font-semibold rounded ${
                      translationStatus === 'ORIGINAL'
                        ? 'bg-gray-100 text-gray-700'
                        : translationStatus === 'MACHINE'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-green-100 text-green-800'
                    }`}
                  >
                    {translationStatus}
                  </span>
                  {translationStatus === 'MACHINE' && (
                    <button
                      onClick={handleApproveTranslation}
                      disabled={approving}
                      className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                    >
                      {approving ? 'Approving...' : 'Approve'}
                    </button>
                  )}
                </div>
              )}
              {currentI18n && (
                <button
                  onClick={() => setShowTranslateModal(true)}
                  disabled={saving}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 text-sm"
                >
                  Auto-translate
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Settings Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Settings</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Slug</label>
            <input
              type="text"
              value={article.slug}
              onChange={(e) => setArticle({ ...article, slug: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Article Type</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setArticle({ ...article, articleType: 'NEWS' })}
                className={`px-4 py-2 rounded-md border text-sm font-medium ${
                  article.articleType === 'NEWS'
                    ? 'bg-sky-600 border-sky-600 text-white'
                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                News
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsCompanyNews(false)
                  setArticle({ ...article, articleType: 'ANALYSIS', isCompanyNews: false })
                }}
                className={`px-4 py-2 rounded-md border text-sm font-medium ${
                  article.articleType === 'ANALYSIS'
                    ? 'bg-purple-600 border-purple-600 text-white'
                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                Analysis
              </button>
            </div>
            {article.articleType === 'NEWS' && (
              <label className="mt-4 flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isCompanyNews}
                  onChange={(e) => {
                    const v = e.target.checked
                    setIsCompanyNews(v)
                    setArticle({ ...article, isCompanyNews: v })
                  }}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-sm text-gray-700">
                  Actualité entreprise (Company news / Vancelian)
                </span>
              </label>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Author Name</label>
            <input
              type="text"
              value={article.authorName}
              onChange={(e) => setArticle({ ...article, authorName: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Author Role</label>
            <input
              type="text"
              value={article.authorRole || ''}
              onChange={(e) => setArticle({ ...article, authorRole: e.target.value || null })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Cover Image
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Optional. Select an image for the article cover.
            </p>
            <MediaField
              value={article.coverMediaId || undefined}
              onChange={(mediaId) => {
                setArticle({ ...article, coverMediaId: mediaId || null })
              }}
              label=""
              allowClear
              preview
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Cover Credit
            </label>
            <input
              type="text"
              value={article.coverCredit || ''}
              onChange={(e) => setArticle({ ...article, coverCredit: e.target.value || null })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="THÉO GIACOMETTI / HANS LUCAS"
              maxLength={120}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Cover Source
            </label>
            <input
              type="text"
              value={article.coverSource || ''}
              onChange={(e) => setArticle({ ...article, coverSource: e.target.value || null })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="LE MONDE"
              maxLength={120}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Publication Datetime
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Used on the public article page. Can be edited even when published.
            </p>
            <div className="flex gap-2">
              <input
                type="datetime-local"
                value={
                  article.publishedAt
                    ? new Date(article.publishedAt).toISOString().slice(0, 16)
                    : ''
                }
                onChange={(e) => {
                  const value = e.target.value
                  setArticle({
                    ...article,
                    publishedAt: value ? new Date(value).toISOString() : null,
                  })
                }}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
              />
              <button
                onClick={() => {
                  setArticle({ ...article, publishedAt: new Date().toISOString() })
                }}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 text-sm"
              >
                Set to now
              </button>
            </div>
          </div>
          <Button onClick={handleSaveSettings} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700">
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>
      </div>

      {/* Header Media Section */}
      {article && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Header Media</h2>
          <div className="space-y-6">
            {/* Cover Image (already in Settings) */}
            <div>
              <p className="text-sm text-gray-600 mb-4">
                Cover image is required and managed in Settings section above.
              </p>
            </div>

            {/* Video */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Video (Optional)
              </label>
              <p className="text-xs text-gray-500 mb-2">
                If set, video replaces cover in article view. Cover still used for cards. YouTube/Vimeo URLs only.
              </p>
              <div className="flex gap-2">
                <input
                  type="url"
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="https://www.youtube.com/watch?v=..."
                />
                {videoUrl && (
                  <button
                    onClick={() => setVideoUrl('')}
                    className="px-4 py-2 bg-red-100 text-red-700 rounded-md hover:bg-red-200"
                  >
                    Clear
                  </button>
                )}
              </div>
              {videoUrl && (
                <div className="mt-3">
                  <div className="aspect-video bg-gray-100 rounded border border-gray-300 overflow-hidden">
                    <iframe
                      src={videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be')
                        ? `https://www.youtube.com/embed/${videoUrl.includes('watch?v=') ? videoUrl.split('watch?v=')[1].split('&')[0] : videoUrl.split('/').pop()}`
                        : videoUrl.includes('vimeo.com')
                        ? `https://player.vimeo.com/video/${videoUrl.split('/').pop()}`
                        : videoUrl}
                      className="w-full h-full"
                      allowFullScreen
                      title="Video preview"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Gallery */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Gallery (Optional)
              </label>
              <p className="text-xs text-gray-500 mb-2">
                Add images to create a carousel. Cover image will be first slide automatically.
              </p>
              <button
                onClick={() => setIsGalleryPickerOpen(true)}
                className="px-4 py-2 bg-indigo-100 text-indigo-700 rounded-md hover:bg-indigo-200 mb-3"
              >
                Add to Gallery
              </button>
              {galleryMediaIds.length > 0 && (
                <div className="space-y-2">
                  {galleryMediaIds.map((mediaId, index) => (
                    <div key={mediaId} className="flex items-center gap-3 border border-gray-200 rounded p-2">
                      {galleryMediaMap[mediaId] && (
                        <img
                          src={galleryMediaMap[mediaId].url}
                          alt={galleryMediaMap[mediaId].filename}
                          className="w-16 h-16 object-cover rounded"
                        />
                      )}
                      <div className="flex-1">
                        <p className="text-sm font-medium">{galleryMediaMap[mediaId]?.filename || mediaId}</p>
                      </div>
                      <div className="flex gap-1">
                        {index > 0 && (
                          <button
                            onClick={() => {
                              const newOrder = [...galleryMediaIds]
                              ;[newOrder[index], newOrder[index - 1]] = [newOrder[index - 1], newOrder[index]]
                              setGalleryMediaIds(newOrder)
                            }}
                            className="px-2 py-1 text-gray-600 hover:text-gray-900"
                          >
                            ↑
                          </button>
                        )}
                        {index < galleryMediaIds.length - 1 && (
                          <button
                            onClick={() => {
                              const newOrder = [...galleryMediaIds]
                              ;[newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]]
                              setGalleryMediaIds(newOrder)
                            }}
                            className="px-2 py-1 text-gray-600 hover:text-gray-900"
                          >
                            ↓
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setGalleryMediaIds(galleryMediaIds.filter((id) => id !== mediaId))
                            const newMap = { ...galleryMediaMap }
                            delete newMap[mediaId]
                            setGalleryMediaMap(newMap)
                          }}
                          className="px-2 py-1 text-red-600 hover:text-red-900"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Categories Section — blog tags + investment categories */}
      {article && (articleBlogCategories.length > 0 || availableCategories.length > 0) && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Categories & tags</h2>
          {articleBlogCategories.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Blog / editorial tags</h3>
              <div className="space-y-2">
                {articleBlogCategories.map((cat) => (
                  <label key={cat.id} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={categorySlugs.includes(cat.slug)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setCategorySlugs([...categorySlugs, cat.slug])
                        } else {
                          setCategorySlugs(categorySlugs.filter((s) => s !== cat.slug))
                        }
                      }}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-sm text-gray-700">{cat.label}</span>
                    <span className="text-xs text-gray-400">({cat.slug})</span>
                  </label>
                ))}
              </div>
            </div>
          )}
          {availableCategories.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-600 mb-2">Investment / offer categories</h3>
              <div className="space-y-2">
                {availableCategories.map((cat) => (
                  <label key={cat.id} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={categorySlugs.includes(cat.slug)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setCategorySlugs([...categorySlugs, cat.slug])
                        } else {
                          setCategorySlugs(categorySlugs.filter((s) => s !== cat.slug))
                        }
                      }}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-sm text-gray-700">{cat.label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Related (Projects, Assets, Vaults) Section */}
      {article && (
        <div ref={relatedSectionRef} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Related</h2>
          <p className="text-sm text-gray-500 mb-4">
            Liez cet article à des projets, des assets crypto ou des vaults. Saisissez un mot-clé pour rechercher.
          </p>
          <div className="relative space-y-4">
            <input
              type="text"
              value={relatedSearch}
              onChange={(e) => setRelatedSearch(e.target.value)}
              onFocus={() => { if (relatedOptions.length > 0) setRelatedOptionsOpen(true) }}
              placeholder="Rechercher un projet, un asset (ex. BTC) ou un vault…"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
            {relatedOptionsOpen && relatedOptions.length > 0 && (
              <div className="absolute z-10 w-full mt-0 border border-gray-200 rounded-md bg-white shadow-lg max-h-56 overflow-y-auto">
                {relatedOptions.map((opt, idx) => {
                  const handleSelect = async () => {
                    try {
                      if (opt.type === 'project' && opt.id) {
                        const res = await fetch(`/api/admin/articles/${articleId}/projects`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ projectId: opt.id }),
                        })
                        if (!res.ok) {
                          const err = await res.json()
                          throw new Error(err.error || 'Erreur')
                        }
                        await fetchLinkedProjects()
                        toastSuccess('Projet lié')
                      } else if (opt.type === 'asset' && opt.symbol) {
                        const res = await fetch(`/api/admin/articles/${articleId}/links`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ kind: 'ASSET', targetId: opt.symbol }),
                        })
                        if (!res.ok) {
                          const err = await res.json()
                          throw new Error(err.error || 'Erreur')
                        }
                        await fetchLinkedLinks()
                        toastSuccess('Asset lié')
                      } else if (opt.type === 'vault' && opt.slug) {
                        const res = await fetch(`/api/admin/articles/${articleId}/links`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ kind: 'VAULT', targetId: opt.slug }),
                        })
                        if (!res.ok) {
                          const err = await res.json()
                          throw new Error(err.error || 'Erreur')
                        }
                        await fetchLinkedLinks()
                        toastSuccess('Vault lié')
                      }
                      setRelatedSearch('')
                      setRelatedOptions([])
                      setRelatedOptionsOpen(false)
                    } catch (err: any) {
                      toastError(err.message || 'Échec de la liaison')
                    }
                  }
                  return (
                  <button
                    key={opt.type + (opt.id ?? opt.symbol ?? opt.slug ?? '') + idx}
                    type="button"
                    onMouseDown={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      handleSelect()
                    }}
                    className="w-full text-left px-4 py-2 hover:bg-gray-100 border-b border-gray-100 last:border-0 flex items-center gap-2 cursor-pointer"
                  >
                    <span className="text-xs font-medium text-gray-500 uppercase bg-gray-100 px-1.5 py-0.5 rounded">
                      {opt.type === 'project' ? 'Projet' : opt.type === 'asset' ? 'Asset' : 'Vault'}
                    </span>
                    <span>{opt.label}</span>
                  </button>
                  )
                })}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              {linkedProjects.map((lp) => {
                const title = lp.project.i18n[0]?.title || lp.project.slug
                return (
                  <span
                    key={lp.id}
                    className="inline-flex items-center gap-1 rounded-full bg-indigo-50 text-indigo-800 px-3 py-1 text-sm"
                  >
                    <span className="text-xs font-medium text-indigo-500">Projet</span>
                    {title}
                    <button
                      type="button"
                      onClick={async () => {
                        if (!confirm('Retirer ce projet ?')) return
                        try {
                          const res = await fetch(`/api/admin/articles/${articleId}/projects/${lp.projectId}`, { method: 'DELETE' })
                          if (res.ok) {
                            await fetchLinkedProjects()
                            toastSuccess('Projet retiré')
                          } else throw new Error((await res.json()).error)
                        } catch (e: any) {
                          toastError(e.message || 'Erreur')
                        }
                      }}
                      className="ml-1 text-indigo-600 hover:text-indigo-900"
                    >
                      ×
                    </button>
                  </span>
                )
              })}
              {linkedLinks.filter((l) => l.kind === 'ASSET').map((l) => (
                <span
                  key={l.id}
                  className="inline-flex items-center gap-1 rounded-full bg-amber-50 text-amber-800 px-3 py-1 text-sm"
                >
                  <span className="text-xs font-medium text-amber-600">Asset</span>
                  {l.label}
                  <button
                    type="button"
                    onClick={async () => {
                      if (!confirm('Retirer cet asset ?')) return
                      try {
                        const res = await fetch(`/api/admin/articles/${articleId}/links/${l.id}`, { method: 'DELETE' })
                        if (res.ok) {
                          await fetchLinkedLinks()
                          toastSuccess('Asset retiré')
                        } else throw new Error((await res.json()).error)
                      } catch (e: any) {
                        toastError(e.message || 'Erreur')
                      }
                    }}
                    className="ml-1 text-amber-600 hover:text-amber-900"
                  >
                    ×
                  </button>
                </span>
              ))}
              {linkedLinks.filter((l) => l.kind === 'VAULT').map((l) => (
                <span
                  key={l.id}
                  className="inline-flex items-center gap-1 rounded-full bg-emerald-50 text-emerald-800 px-3 py-1 text-sm"
                >
                  <span className="text-xs font-medium text-emerald-600">Vault</span>
                  {l.label}
                  <button
                    type="button"
                    onClick={async () => {
                      if (!confirm('Retirer ce vault ?')) return
                      try {
                        const res = await fetch(`/api/admin/articles/${articleId}/links/${l.id}`, { method: 'DELETE' })
                        if (res.ok) {
                          await fetchLinkedLinks()
                          toastSuccess('Vault retiré')
                        } else throw new Error((await res.json()).error)
                      } catch (e: any) {
                        toastError(e.message || 'Erreur')
                      }
                    }}
                    className="ml-1 text-emerald-600 hover:text-emerald-900"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Editorial Settings Section */}
      {article && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Editorial Settings</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Featured Article
                </label>
                <p className="text-xs text-gray-500">
                  Only one featured article is allowed. This will replace the current featured article.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={isFeatured}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setShowFeaturedConfirm(true)
                    } else {
                      setIsFeatured(false)
                    }
                  }}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
              </label>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Highlighted Article
                </label>
                <p className="text-xs text-gray-500">
                  Appears in the mosaic section on the blog page.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={isHighlighted}
                  onChange={(e) => setIsHighlighted(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
              </label>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Milestone Articles
                </label>
                <p className="text-xs text-gray-500">
                  Activated or not (true/false) to mark this article as a milestone.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={isMilestone}
                  onChange={(e) => setIsMilestone(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Documents Section */}
      {article && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Documents (PDF)</h2>
          <button
            onClick={() => setIsDocumentPickerOpen(true)}
            className="px-4 py-2 bg-indigo-100 text-indigo-700 rounded-md hover:bg-indigo-200 mb-3"
          >
            Attach PDF
          </button>
          {documents.length > 0 && (
            <div className="space-y-2">
              {documents.map((doc, index) => (
                <div key={index} className="flex items-center justify-between border border-gray-200 rounded p-2">
                  <div className="flex items-center gap-3">
                    {documentMediaMap[doc.mediaId] && (
                      <div className="w-10 h-10 bg-gray-200 rounded flex items-center justify-center">
                        <span className="text-xs">PDF</span>
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-medium">{doc.title || documentMediaMap[doc.mediaId]?.filename || doc.mediaId}</p>
                      {documentMediaMap[doc.mediaId] && (
                        <a
                          href={documentMediaMap[doc.mediaId].url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-indigo-600 hover:underline"
                        >
                          Download
                        </a>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setDocuments(documents.filter((_, i) => i !== index))
                    }}
                    className="text-red-600 hover:text-red-900 text-sm"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Header Content Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Header Content</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Title *</label>
            <input
              type="text"
              value={i18nData.title}
              onChange={(e) => setI18nData({ ...i18nData, title: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-2xl font-bold"
              placeholder="Article Title"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Standfirst *</label>
            <textarea
              value={i18nData.standfirst}
              onChange={(e) => setI18nData({ ...i18nData, standfirst: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md italic"
              placeholder="Short introduction..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Cover Title</label>
            <p className="text-xs text-gray-500 mb-2">
              Displayed below the cover image on the article page
            </p>
            <textarea
              value={i18nData.coverTitle}
              onChange={(e) => setI18nData({ ...i18nData, coverTitle: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="Caption text..."
              maxLength={240}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Meta Title</label>
            <input
              type="text"
              value={i18nData.metaTitle || ''}
              onChange={(e) => setI18nData({ ...i18nData, metaTitle: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Meta Description</label>
            <textarea
              value={i18nData.metaDescription || ''}
              onChange={(e) => setI18nData({ ...i18nData, metaDescription: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
        </div>
      </div>

      {/* Blocks Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Article Blocks</h2>
          <div className="flex gap-2">
            <Button onClick={() => handleAddBlock(ArticleBlockType.HEADING)} variant="outline" size="sm">
              + Heading
            </Button>
            <Button onClick={() => handleAddBlock(ArticleBlockType.PARAGRAPH)} variant="outline" size="sm">
              + Paragraph
            </Button>
            <Button onClick={() => handleAddBlock(ArticleBlockType.QUOTE)} variant="outline" size="sm">
              + Quote
            </Button>
            <Button onClick={() => handleAddBlock(ArticleBlockType.BULLET_LIST)} variant="outline" size="sm">
              + List
            </Button>
            <Button onClick={() => handleAddBlock(ArticleBlockType.IMAGE)} variant="outline" size="sm">
              + Image
            </Button>
            <Button onClick={() => handleAddBlock(ArticleBlockType.VIDEO)} variant="outline" size="sm">
              + Video
            </Button>
            <Button onClick={() => handleAddBlock(ArticleBlockType.DOCUMENT)} variant="outline" size="sm">
              + Document
            </Button>
          </div>
        </div>

        <div className="space-y-4">
          {blocksDraft.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No blocks yet. Add your first block!</p>
          ) : (
            blocksDraft.map((block, index) => (
              <div key={block.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">{block.type}</span>
                  <div className="flex gap-2">
                    {index > 0 && (
                      <button
                        onClick={() => {
                          const newOrder = [...blocksDraft]
                          ;[newOrder[index], newOrder[index - 1]] = [newOrder[index - 1], newOrder[index]]
                          handleReorderBlocks(newOrder.map((b) => b.id))
                        }}
                        className="text-gray-600 hover:text-gray-900"
                      >
                        ↑
                      </button>
                    )}
                    {index < blocksDraft.length - 1 && (
                      <button
                        onClick={() => {
                          const newOrder = [...blocksDraft]
                          ;[newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]]
                          handleReorderBlocks(newOrder.map((b) => b.id))
                        }}
                        className="text-gray-600 hover:text-gray-900"
                      >
                        ↓
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteBlock(block.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Delete
                    </button>
                  </div>
                </div>
                {block.type === ArticleBlockType.HEADING && (
                  <input
                    type="text"
                    value={(block.data as any).text || ''}
                    onChange={(e) =>
                      handleUpdateBlock(block.id, { ...block.data, text: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-xl font-bold"
                    placeholder="Heading text"
                  />
                )}
                {block.type === ArticleBlockType.PARAGRAPH && (
                  <div className="space-y-3">
                    <textarea
                      value={(block.data as any).text || ''}
                      onChange={(e) =>
                        handleUpdateBlock(block.id, { ...block.data, text: e.target.value })
                      }
                      rows={6}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
                      placeholder="Paragraph text (Markdown supported)"
                    />
                    <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
                      <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
                        Markdown preview
                      </div>
                      {(block.data as any).text?.trim() ? (
                        <div className="space-y-2 text-sm text-gray-900">
                          <ReactMarkdown
                            components={{
                              p: ({ children }) => <p className="leading-7">{children}</p>,
                              h1: ({ children }) => <h1 className="text-2xl font-bold">{children}</h1>,
                              h2: ({ children }) => <h2 className="text-xl font-bold">{children}</h2>,
                              h3: ({ children }) => <h3 className="text-lg font-semibold">{children}</h3>,
                              ul: ({ children }) => <ul className="list-disc pl-5 space-y-1">{children}</ul>,
                              ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1">{children}</ol>,
                              li: ({ children }) => <li>{children}</li>,
                              blockquote: ({ children }) => (
                                <blockquote className="border-l-4 border-gray-300 pl-3 italic text-gray-700">
                                  {children}
                                </blockquote>
                              ),
                              a: ({ href, children }) => (
                                <a
                                  href={href}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-indigo-600 underline"
                                >
                                  {children}
                                </a>
                              ),
                              code: ({ children }) => (
                                <code className="rounded bg-gray-200 px-1 py-0.5 font-mono text-xs">
                                  {children}
                                </code>
                              ),
                            }}
                          >
                            {(block.data as any).text}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">Preview will appear here.</p>
                      )}
                    </div>
                  </div>
                )}
                {block.type === ArticleBlockType.QUOTE && (
                  <div className="space-y-2">
                    <textarea
                      value={(block.data as any).text || ''}
                      onChange={(e) =>
                        handleUpdateBlock(block.id, { ...block.data, text: e.target.value })
                      }
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md italic"
                      placeholder="Quote text"
                    />
                    <input
                      type="text"
                      value={(block.data as any).author || ''}
                      onChange={(e) =>
                        handleUpdateBlock(block.id, { ...block.data, author: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="Author (optional)"
                    />
                  </div>
                )}
                {block.type === ArticleBlockType.BULLET_LIST && (
                  <div className="space-y-2">
                    {((block.data as any).items || ['']).map((item: string, i: number) => (
                      <input
                        key={i}
                        type="text"
                        value={item}
                        onChange={(e) => {
                          const items = [...((block.data as any).items || [])]
                          items[i] = e.target.value
                          handleUpdateBlock(block.id, { ...block.data, items })
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                        placeholder={`Item ${i + 1}`}
                      />
                    ))}
                    <button
                      onClick={() => {
                        const items = [...((block.data as any).items || [])]
                        items.push('')
                        handleUpdateBlock(block.id, { ...block.data, items })
                      }}
                      className="text-sm text-indigo-600 hover:text-indigo-900"
                    >
                      + Add item
                    </button>
                  </div>
                )}
                {block.type === ArticleBlockType.IMAGE && (
                  <div className="space-y-2">
                    <MediaField
                      value={(block.data as any).mediaId || undefined}
                      onChange={(mediaId) =>
                        handleUpdateBlock(block.id, { ...block.data, mediaId: mediaId || '' })
                      }
                      label="Image"
                      allowClear
                      preview
                    />
                    <input
                      type="text"
                      value={(block.data as any).caption || ''}
                      onChange={(e) =>
                        handleUpdateBlock(block.id, { ...block.data, caption: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="Caption"
                    />
                  </div>
                )}
                {block.type === ArticleBlockType.VIDEO && (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={(block.data as any).url || ''}
                      onChange={(e) =>
                        handleUpdateBlock(block.id, { ...block.data, url: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="Video URL (YouTube/Vimeo)"
                    />
                    <input
                      type="text"
                      value={(block.data as any).caption || ''}
                      onChange={(e) =>
                        handleUpdateBlock(block.id, { ...block.data, caption: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="Caption"
                    />
                  </div>
                )}
                {block.type === ArticleBlockType.DOCUMENT && (
                  <div className="space-y-2">
                    <MediaField
                      value={(block.data as any).mediaId || undefined}
                      onChange={(mediaId) =>
                        handleUpdateBlock(block.id, { ...block.data, mediaId: mediaId || '' })
                      }
                      label="Document (PDF)"
                      allowClear
                    />
                    <input
                      type="text"
                      value={(block.data as any).title || ''}
                      onChange={(e) =>
                        handleUpdateBlock(block.id, { ...block.data, title: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="Document title"
                    />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Translate Modal */}
      {currentI18n && (
        <TranslateModal
          open={showTranslateModal}
          onOpenChange={setShowTranslateModal}
          sourceLocale={selectedLocale}
          hasGlossary={hasGlossary}
          onTranslate={async ({ sourceLocale, targetLocales, mode }) => {
            const response = await fetch('/api/admin/translate/article', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                articleId: article.id,
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
            return data
          }}
        />
      )}

      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={(open) => setShowDeleteDialog(open)}
        title="Delete Article"
        description="This action will permanently delete the article and all its content. This cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={handleDelete}
        destructive
      />

      <ConfirmDialog
        open={showUnpublishDialog}
        onOpenChange={(open) => setShowUnpublishDialog(open)}
        title="Set Article to Draft"
        description="This will unpublish the article. It will no longer be visible on the public site."
        confirmLabel="Set to Draft"
        cancelLabel="Cancel"
        onConfirm={handleUnpublish}
      />

      <ConfirmDialog
        open={showFeaturedConfirm}
        onOpenChange={setShowFeaturedConfirm}
        title="Set as Featured Article"
        description="This will replace the current featured article. Only one article can be featured at a time."
        confirmLabel="Confirm"
        cancelLabel="Cancel"
        onConfirm={async () => {
          setIsFeatured(true)
          setShowFeaturedConfirm(false)
        }}
      />

      {/* Gallery Media Picker */}
      <MediaPicker
        isOpen={isGalleryPickerOpen}
        onClose={() => setIsGalleryPickerOpen(false)}
        onSelect={(media) => {
          if (!galleryMediaIds.includes(media.id)) {
            setGalleryMediaIds([...galleryMediaIds, media.id])
            setGalleryMediaMap({ ...galleryMediaMap, [media.id]: { url: media.url, filename: media.filename } })
          }
          setIsGalleryPickerOpen(false)
        }}
        title="Select Image for Gallery"
      />

      {/* Document Media Picker */}
      <MediaPicker
        isOpen={isDocumentPickerOpen}
        onClose={() => setIsDocumentPickerOpen(false)}
        onSelect={(media) => {
          const title = prompt('Document title:')
          if (title) {
            setDocuments([...documents, { mediaId: media.id, title }])
            setDocumentMediaMap({ ...documentMediaMap, [media.id]: { url: media.url, filename: media.filename } })
          }
          setIsDocumentPickerOpen(false)
        }}
        title="Select PDF Document"
      />

      {/* Save Content Button - Bottom of page */}
      <div className="mt-6 flex justify-end">
        <Button onClick={handleSaveContent} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700">
          {saving ? 'Saving...' : 'Save Content'}
        </Button>
      </div>
    </div>
  )
}

