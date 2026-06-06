'use client'

import { useEffect, useMemo, useState, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Plus, Save, ArrowLeft, Languages, FileText, Tag, Link2, Star, AlignLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CollapsibleAdminSection } from '@/components/admin/CollapsibleAdminSection'
import { MediaTile } from '@/components/admin/MediaTile'
import { ContentBlocksSection } from '@/components/admin/ContentBlocksSection'
import { MarkdownImportDialog } from '@/components/admin/MarkdownImportDialog'
import HelpHierarchyPicker from '@/components/admin/HelpHierarchyPicker'
import AcademyHierarchyPicker from '@/components/admin/AcademyHierarchyPicker'
import { ContentStatus, ArticleBlockType } from '@prisma/client'
import { supportedLocales, type Locale, defaultLocale } from '@/config/locales'
import { toastSuccess, toastError, toastWarning } from '@/lib/admin/toast'
import { exportArticleBlocksToMarkdown } from '@/lib/admin/markdownArticleBlocksBlueprint'
import { TranslateModal } from '@/components/admin/TranslateModal'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { PagePreviewPanel } from '@/components/admin/PagePreviewPanel'
import { adminMediaFileUrl } from '@/lib/admin/adminMediaFileUrl'
import {
  getDefaultBlockData,
  type AddableBlockType,
} from '@/lib/admin/articleBlockCatalog'
import { messageFromAdminApiError as sharedMessageFromAdminApiError } from '@/lib/admin/messageFromAdminApiError'
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
  articleType: ArticleTypeKey
  /** Champ serveur ; actualité entreprise (NEWS uniquement). */
  isCompanyNews?: boolean
  // -------- Champs HELP (Phase 3.3) --------
  // Pertinents uniquement quand `articleType === 'HELP'`.
  helpCollectionId?: string | null
  helpCategoryId?: string | null
  helpSlug?: string | null
  /** Tags regroupement (collection → sections). */
  collectionTags?: string[]
  allowAnchors?: boolean
  targetTags?: string[] | null
  // -------- Champs ACADEMY (Phase 4 — symétrique HELP) --------
  // Pertinents uniquement quand `articleType === 'ACADEMY'`.
  academyCollectionId?: string | null
  academyCategoryId?: string | null
  academySlug?: string | null
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

/** Alias local : la fonction est définie dans `@/lib/admin/messageFromAdminApiError` (extraction Lot E). */
const messageFromAdminApiError = sharedMessageFromAdminApiError

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
  const [showMarkdownImport, setShowMarkdownImport] = useState(false)
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
  const [galleryMediaMap, setGalleryMediaMap] = useState<Record<string, { url: string; filename: string }>>({})
  const [documentMediaMap, setDocumentMediaMap] = useState<Record<string, { url: string; filename: string }>>({})
  const [isFeatured, setIsFeatured] = useState(false)
  const [isHighlighted, setIsHighlighted] = useState(false)
  const [isMilestone, setIsMilestone] = useState(false)
  const [showFeaturedConfirm, setShowFeaturedConfirm] = useState(false)
  const [blocksDraft, setBlocksDraft] = useState<Article['blocks']>([])
  const [blocksDirty, setBlocksDirty] = useState(false)

  // Aperçu live (split éditeur ↔ preview iframe — même méthodologie que le page builder)
  const [previewLocale, setPreviewLocale] = useState<Locale>(defaultLocale)
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'mobile'>('desktop')
  const [previewReloadEpoch, setPreviewReloadEpoch] = useState(0)

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
      const rawTags = data.article?.collectionTags
      const collectionTags = Array.isArray(rawTags)
        ? rawTags.filter((x: unknown): x is string => typeof x === 'string')
        : []
      setArticle({
        ...data.article,
        collectionTags,
        articleType: normalizeArticleType(data.article?.articleType),
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

  /**
   * Sauvegarde unifiée : envoie d'abord le payload complet des settings
   * (slug, cover, gallery, video, categories, documents, flags éditoriaux,
   * publishedAt) puis l'i18n du locale courant et les blocs modifiés.
   * Remplace les boutons « Save Settings » / « Save Content » séparés.
   */
  const handleSaveAll = async () => {
    if (!article) return
    setSaving(true)
    try {
      const settingsPayload: any = {
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
      if (typeof isFeatured === 'boolean') settingsPayload.isFeatured = isFeatured
      if (typeof isHighlighted === 'boolean') settingsPayload.isHighlighted = isHighlighted
      if (typeof isMilestone === 'boolean') settingsPayload.isMilestone = isMilestone

      // Champs HELP : envoyés systématiquement (l'API les ignore / clear si
      // articleType ≠ HELP, voir route handler).
      if (article.articleType === 'HELP') {
        settingsPayload.helpCollectionId = article.helpCollectionId ?? null
        settingsPayload.helpSlug = article.helpSlug ?? null
        settingsPayload.collectionTags = Array.isArray(article.collectionTags)
          ? article.collectionTags
          : []
        settingsPayload.allowAnchors =
          typeof article.allowAnchors === 'boolean' ? article.allowAnchors : true
        settingsPayload.targetTags =
          Array.isArray(article.targetTags) && article.targetTags.length > 0
            ? article.targetTags
            : null
      }

      // Champs ACADEMY (Phase 4 — symétrique HELP) : même logique.
      if (article.articleType === 'ACADEMY') {
        settingsPayload.academyCollectionId = article.academyCollectionId ?? null
        settingsPayload.academySlug = article.academySlug ?? null
        settingsPayload.collectionTags = Array.isArray(article.collectionTags)
          ? article.collectionTags
          : []
        settingsPayload.allowAnchors =
          typeof article.allowAnchors === 'boolean' ? article.allowAnchors : true
        settingsPayload.targetTags =
          Array.isArray(article.targetTags) && article.targetTags.length > 0
            ? article.targetTags
            : null
      }

      const settingsResponse = await fetch(`/api/admin/articles/${articleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsPayload),
      })
      if (!settingsResponse.ok) {
        const error = await settingsResponse.json()
        const details = error.issues
          ? error.issues.map((issue: any) => `${issue.path.join('.')}: ${issue.message}`).join(', ')
          : error.message || messageFromAdminApiError(error, 'Failed to save settings')
        throw new Error(details || 'Failed to save settings')
      }

      // Seul le titre est requis ; le standfirst est optionnel.
      const hasRequiredI18nFields = i18nData.title.trim().length > 0
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
          i18nErrorMessage = error.issues
            ? error.issues.map((issue: any) => `${issue.path.join('.')}: ${issue.message}`).join(', ')
            : messageFromAdminApiError(error, 'Failed to save content')
        }
      } else {
        i18nErrorMessage = 'Title is required to save localized content.'
      }

      let blocksErrorMessage: string | null = null
      if (blocksDirty) {
        try {
          const changedBlocks = blocksDraft.filter((draftBlock) => {
            const originalBlock = article.blocks.find((b) => b.id === draftBlock.id)
            if (!originalBlock) return false
            return JSON.stringify(originalBlock.data ?? {}) !== JSON.stringify(draftBlock.data ?? {})
          })
          for (const block of changedBlocks) {
            const response = await fetch(`/api/admin/articles/${articleId}/blocks/${block.id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ data: block.data ?? {}, locale: selectedLocale }),
            })
            if (!response.ok) {
              const error = await response.json()
              throw new Error(messageFromAdminApiError(error, `Failed to save block ${block.id}`))
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
        toastSuccess('All changes saved')
      }
      setPreviewReloadEpoch((n) => n + 1)
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to save changes')
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
        throw new Error(messageFromAdminApiError(error, 'Failed to publish article'))
      }

      const data = await response.json()
      if (data.warning) {
        toastError(data.warning)
      } else {
        toastSuccess('Article published')
      }
      setPreviewReloadEpoch((n) => n + 1)
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
        throw new Error(messageFromAdminApiError(error, 'Failed to unpublish article'))
      }

      toastSuccess('Article set to draft')
      setPreviewReloadEpoch((n) => n + 1)
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
        throw new Error(messageFromAdminApiError(error, 'Failed to delete article'))
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
        throw new Error(messageFromAdminApiError(error, 'Failed to approve translation'))
      }
      toastSuccess('Translation approved')
      setPreviewReloadEpoch((n) => n + 1)
      await fetchArticle()
    } catch (error: any) {
      toastError(error.message || 'Failed to approve translation')
    } finally {
      setApproving(false)
    }
  }

  /**
   * Conservé pour rétro-compat / API utilisée par d'autres handlers internes.
   * L'UI principale d'ajout passe désormais par la page modale dédiée
   * `/admin/articles/[id]/add-block` (cf. lot bouton Link).
   */
  const handleAddBlock = async (type: AddableBlockType) => {
    if (!article) return
    try {
      const response = await fetch(`/api/admin/articles/${articleId}/blocks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type,
          data: getDefaultBlockData(type),
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(messageFromAdminApiError(error, 'Failed to add block'))
      }

      toastSuccess('Block added')
      setPreviewReloadEpoch((n) => n + 1)
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
        throw new Error(messageFromAdminApiError(error, 'Failed to delete block'))
      }

      toastSuccess('Block deleted')
      setPreviewReloadEpoch((n) => n + 1)
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

  /** Fusion champs (éditeurs type Vault = patch partiel). */
  const handlePatchBlock = (blockId: string, patch: Record<string, unknown>) => {
    setBlocksDraft((prev) =>
      prev.map((block) => {
        if (block.id !== blockId) return block
        const base =
          block.data && typeof block.data === 'object' && !Array.isArray(block.data)
            ? (block.data as Record<string, unknown>)
            : {}
        return { ...block, data: { ...base, ...patch } }
      })
    )
    setBlocksDirty(true)
  }

  const handleExportArticleBlocksMarkdown = () => {
    if (!article || blocksDraft.length === 0) {
      toastWarning('Aucun bloc à exporter.')
      return
    }
    const markdown = exportArticleBlocksToMarkdown(
      blocksDraft.map((block) => ({
        type: block.type,
        data:
          block.data != null && typeof block.data === 'object' && !Array.isArray(block.data)
            ? (block.data as Record<string, unknown>)
            : {},
      })),
      selectedLocale,
    )
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `article-blocks-${article.slug}-${selectedLocale}.md`
    anchor.click()
    URL.revokeObjectURL(url)
    toastSuccess('Export Markdown téléchargé.')
  }

  const handleApplyArticleBlocksMarkdownImport = async (
    importedBlocks: Array<{ type: ArticleBlockType; data: Record<string, unknown> }>,
  ) => {
    if (!article) return
    setSaving(true)
    try {
      for (const block of article.blocks) {
        const response = await fetch(`/api/admin/articles/${articleId}/blocks/${block.id}`, {
          method: 'DELETE',
        })
        if (!response.ok) {
          const error = await response.json()
          throw new Error(messageFromAdminApiError(error, 'Failed to delete existing block'))
        }
      }

      for (let order = 0; order < importedBlocks.length; order++) {
        const block = importedBlocks[order]!
        const response = await fetch(`/api/admin/articles/${articleId}/blocks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: block.type,
            data: block.data,
            order,
          }),
        })
        if (!response.ok) {
          const error = await response.json()
          throw new Error(messageFromAdminApiError(error, `Failed to import block ${order + 1}`))
        }
      }

      toastSuccess(`${importedBlocks.length} bloc(s) importé(s).`)
      setPreviewReloadEpoch((n) => n + 1)
      await fetchArticle()
    } catch (error: unknown) {
      toastError(error instanceof Error ? error.message : 'Import Content Blocks impossible')
    } finally {
      setSaving(false)
    }
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
        throw new Error(messageFromAdminApiError(error, 'Failed to reorder blocks'))
      }

      toastSuccess('Blocks reordered')
      setPreviewReloadEpoch((n) => n + 1)
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

  const previewUrl = articleId
    ? `/preview/article/${encodeURIComponent(articleId)}?locale=${encodeURIComponent(previewLocale)}`
    : ''
  const previewBaseTitle = i18nData.title?.trim() || article.slug || 'Article'
  const previewPanelTitle = `${previewBaseTitle} (${previewLocale.toUpperCase()})`
  const previewToolbar = {
    locale: previewLocale,
    onLocaleChange: setPreviewLocale,
    device: previewDevice,
    onDeviceChange: setPreviewDevice,
  }

  return (
    <section className="lg:grid lg:grid-cols-2 lg:items-start lg:gap-6 lg:divide-x lg:divide-slate-200">
      <div className="space-y-3 lg:min-w-0 lg:pr-6">
      {/* Sticky compact header + actions globales */}
      <div className="sticky top-0 z-20 -mx-2 mb-1 border-b border-gray-200 bg-white/95 px-2 py-2 backdrop-blur">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/admin/articles"
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-900"
            title="Back to Articles"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Articles
          </Link>
          <h1 className="text-base font-semibold text-gray-900">Edit Article</h1>
          <span
            className={`inline-flex px-2 py-0.5 text-[10px] font-semibold rounded-full ${ARTICLE_TYPES[article.articleType].badgeClassName}`}
          >
            {ARTICLE_TYPES[article.articleType].label}
          </span>
          <span
            className={`inline-flex px-2 py-0.5 text-[10px] font-semibold rounded-full ${
              article.status === 'PUBLISHED' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
            }`}
          >
            {article.status}
          </span>

          <span className="mx-1 h-4 w-px bg-gray-200" aria-hidden />

          {/* Locale d'édition + traduction inline */}
          <div className="flex items-center gap-1.5">
            <Languages className="h-3.5 w-3.5 text-gray-500" />
            <select
              value={selectedLocale}
              onChange={(e) => setSelectedLocale(e.target.value as Locale)}
              className="rounded border border-gray-300 px-1.5 py-0.5 text-xs"
              title="Edit locale"
            >
              {supportedLocales.map((locale) => (
                <option key={locale} value={locale}>
                  {locale.toUpperCase()}
                </option>
              ))}
            </select>
            {translationStatus && (
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                  translationStatus === 'ORIGINAL'
                    ? 'bg-gray-100 text-gray-700'
                    : translationStatus === 'MACHINE'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-green-100 text-green-800'
                }`}
                title="Translation status"
              >
                {translationStatus}
              </span>
            )}
            {translationStatus === 'MACHINE' && (
              <button
                onClick={handleApproveTranslation}
                disabled={approving}
                className="rounded bg-green-600 px-2 py-0.5 text-[10px] font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {approving ? '…' : 'Approve'}
              </button>
            )}
            {currentI18n && (
              <button
                onClick={() => setShowTranslateModal(true)}
                disabled={saving}
                className="rounded bg-purple-600 px-2 py-0.5 text-[10px] font-medium text-white hover:bg-purple-700 disabled:opacity-50"
                title="Auto-translate"
              >
                Auto-translate
              </button>
            )}
          </div>

          <div className="ml-auto flex items-center gap-1.5">
            <Button
              onClick={handleSaveAll}
              disabled={saving}
              size="sm"
              className="bg-indigo-600 hover:bg-indigo-700"
              title="Save all changes (settings + content + blocks)"
            >
              <Save className="mr-1 h-3.5 w-3.5" />
              {saving ? 'Saving…' : 'Save'}
            </Button>
            {article.status === 'DRAFT' ? (
              <Button
                onClick={handlePublish}
                disabled={saving}
                size="sm"
                className="bg-green-600 hover:bg-green-700"
              >
                Publish
              </Button>
            ) : (
              <Button
                onClick={() => setShowUnpublishDialog(true)}
                disabled={saving}
                size="sm"
                className="bg-orange-600 hover:bg-orange-700"
              >
                Set to Draft
              </Button>
            )}
            <Button
              onClick={() => setShowDeleteDialog(true)}
              disabled={saving}
              size="sm"
              variant="ghost"
              className="text-red-600 hover:bg-red-50 hover:text-red-700"
            >
              Delete
            </Button>
          </div>
        </div>
      </div>

      {/* Settings Section */}
      <CollapsibleAdminSection
        title="Settings"
        icon={<FileText className="h-3.5 w-3.5" />}
        summary={`slug: ${article.slug || '—'} · ${article.authorName || 'no author'}`}
      >
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Slug</label>
              <input
                type="text"
                value={article.slug}
                onChange={(e) => setArticle({ ...article, slug: e.target.value })}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Article Type</label>
              <div className="flex flex-wrap items-center gap-1.5">
                <select
                  value={article.articleType}
                  onChange={(e) => {
                    const next = e.target.value as ArticleTypeKey
                    if (next !== 'NEWS') setIsCompanyNews(false)
                    setArticle({
                      ...article,
                      articleType: next,
                      isCompanyNews: next === 'NEWS' ? article.isCompanyNews : false,
                    })
                  }}
                  className="px-2 py-1 text-xs border border-gray-300 rounded bg-white"
                >
                  {ARTICLE_TYPE_KEYS.map((key) => (
                    <option key={key} value={key}>
                      {ARTICLE_TYPES[key].label}
                    </option>
                  ))}
                </select>
                <span
                  className={`px-2 py-0.5 text-[10px] font-semibold rounded-full ${ARTICLE_TYPES[article.articleType].badgeClassName}`}
                  title={ARTICLE_TYPES[article.articleType].description}
                >
                  {ARTICLE_TYPES[article.articleType].label}
                </span>
                {article.articleType === 'NEWS' && (
                  <label className="flex items-center gap-1 text-xs text-gray-700 cursor-pointer">
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
                    Company news
                  </label>
                )}
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Author Name</label>
              <input
                type="text"
                value={article.authorName}
                onChange={(e) => setArticle({ ...article, authorName: e.target.value })}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Author Role</label>
              <input
                type="text"
                value={article.authorRole || ''}
                onChange={(e) => setArticle({ ...article, authorRole: e.target.value || null })}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
              />
            </div>
          </div>

          {article.articleType === 'HELP' && (
            <HelpHierarchyPicker
              value={{
                helpCollectionId: article.helpCollectionId ?? null,
                helpSlug: article.helpSlug ?? null,
                collectionTags: Array.isArray(article.collectionTags)
                  ? article.collectionTags
                  : [],
                allowAnchors:
                  typeof article.allowAnchors === 'boolean' ? article.allowAnchors : true,
              }}
              onChange={(next) =>
                setArticle({
                  ...article,
                  helpCollectionId: next.helpCollectionId,
                  helpSlug: next.helpSlug,
                  collectionTags: next.collectionTags,
                  allowAnchors: next.allowAnchors,
                })
              }
            />
          )}

          {article.articleType === 'ACADEMY' && (
            <AcademyHierarchyPicker
              value={{
                academyCollectionId: article.academyCollectionId ?? null,
                academySlug: article.academySlug ?? null,
                collectionTags: Array.isArray(article.collectionTags)
                  ? article.collectionTags
                  : [],
                allowAnchors:
                  typeof article.allowAnchors === 'boolean' ? article.allowAnchors : true,
              }}
              onChange={(next) =>
                setArticle({
                  ...article,
                  academyCollectionId: next.academyCollectionId,
                  academySlug: next.academySlug,
                  collectionTags: next.collectionTags,
                  allowAnchors: next.allowAnchors,
                })
              }
            />
          )}

          <div className="flex items-start gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Cover</label>
              {article.coverMediaId ? (
                <MediaTile
                  variant="filled"
                  mediaId={article.coverMediaId}
                  onChange={(id) => setArticle({ ...article, coverMediaId: id || null })}
                  onRemove={() => setArticle({ ...article, coverMediaId: null })}
                  index={0}
                  total={1}
                  size={80}
                  pickerKind="image"
                  pickerTitle="Sélectionner une cover"
                />
              ) : (
                <MediaTile
                  variant="add"
                  size={80}
                  pickerKind="image"
                  pickerTitle="Sélectionner une cover"
                  onSelect={(id) => setArticle({ ...article, coverMediaId: id })}
                />
              )}
            </div>
            <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Cover Credit</label>
                <input
                  type="text"
                  value={article.coverCredit || ''}
                  onChange={(e) => setArticle({ ...article, coverCredit: e.target.value || null })}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                  placeholder="THÉO GIACOMETTI / HANS LUCAS"
                  maxLength={120}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Cover Source</label>
                <input
                  type="text"
                  value={article.coverSource || ''}
                  onChange={(e) => setArticle({ ...article, coverSource: e.target.value || null })}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                  placeholder="LE MONDE"
                  maxLength={120}
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Publication Datetime</label>
            <div className="flex gap-1.5">
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
                className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded"
              />
              <button
                onClick={() => setArticle({ ...article, publishedAt: new Date().toISOString() })}
                className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs hover:bg-gray-200"
              >
                Now
              </button>
            </div>
          </div>
        </div>
      </CollapsibleAdminSection>

      {/* Categories Section — blog tags + investment categories */}
      {article && (articleBlogCategories.length > 0 || availableCategories.length > 0) && (
        <CollapsibleAdminSection
          title="Categories & tags"
          icon={<Tag className="h-3.5 w-3.5" />}
          summary={`${categorySlugs.length} sélectionnée${categorySlugs.length > 1 ? 's' : ''}`}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {articleBlogCategories.length > 0 && (
              <div>
                <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                  Blog / editorial tags
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {articleBlogCategories.map((cat) => {
                    const checked = categorySlugs.includes(cat.slug)
                    return (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => {
                          if (checked) {
                            setCategorySlugs(categorySlugs.filter((s) => s !== cat.slug))
                          } else {
                            setCategorySlugs([...categorySlugs, cat.slug])
                          }
                        }}
                        className={`rounded-full border px-2 py-0.5 text-xs font-medium transition ${
                          checked
                            ? 'border-indigo-600 bg-indigo-600 text-white'
                            : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                        }`}
                        title={cat.slug}
                      >
                        {cat.label}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
            {availableCategories.length > 0 && (
              <div>
                <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                  Investment / offer categories
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {availableCategories.map((cat) => {
                    const checked = categorySlugs.includes(cat.slug)
                    return (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => {
                          if (checked) {
                            setCategorySlugs(categorySlugs.filter((s) => s !== cat.slug))
                          } else {
                            setCategorySlugs([...categorySlugs, cat.slug])
                          }
                        }}
                        className={`rounded-full border px-2 py-0.5 text-xs font-medium transition ${
                          checked
                            ? 'border-emerald-600 bg-emerald-600 text-white'
                            : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        {cat.label}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </CollapsibleAdminSection>
      )}

      {/* Related (Projects, Assets, Vaults) Section */}
      {article && (
        <div ref={relatedSectionRef}>
        <CollapsibleAdminSection
          title="Related"
          icon={<Link2 className="h-3.5 w-3.5" />}
          summary={`${linkedProjects.length} projets · ${linkedLinks.filter(l => l.kind === 'ASSET').length} assets · ${linkedLinks.filter(l => l.kind === 'VAULT').length} vaults`}
        >
          <div className="relative space-y-2">
            <input
              type="text"
              value={relatedSearch}
              onChange={(e) => setRelatedSearch(e.target.value)}
              onFocus={() => { if (relatedOptions.length > 0) setRelatedOptionsOpen(true) }}
              placeholder="Rechercher un projet, un asset (ex. BTC) ou un vault…"
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
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
                          throw new Error(messageFromAdminApiError(err, 'Erreur'))
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
                          throw new Error(messageFromAdminApiError(err, 'Erreur'))
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
                          throw new Error(messageFromAdminApiError(err, 'Erreur'))
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
        </CollapsibleAdminSection>
        </div>
      )}

      {/* Editorial Settings Section */}
      {article && (
        <CollapsibleAdminSection
          title="Editorial Settings"
          icon={<Star className="h-3.5 w-3.5" />}
          summary={[
            isFeatured ? 'Featured' : null,
            isHighlighted ? 'Highlighted' : null,
            isMilestone ? 'Milestone' : null,
          ].filter(Boolean).join(' · ') || 'aucun flag'}
        >
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <label
              className="flex cursor-pointer items-center justify-between gap-2 rounded border border-gray-200 px-2 py-1.5"
              title="Only one featured article is allowed. This will replace the current featured article."
            >
              <span className="text-xs font-medium text-gray-700">Featured</span>
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
                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
            </label>
            <label
              className="flex cursor-pointer items-center justify-between gap-2 rounded border border-gray-200 px-2 py-1.5"
              title="Appears in the mosaic section on the blog page."
            >
              <span className="text-xs font-medium text-gray-700">Highlighted</span>
              <input
                type="checkbox"
                checked={isHighlighted}
                onChange={(e) => setIsHighlighted(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
            </label>
            <label
              className="flex cursor-pointer items-center justify-between gap-2 rounded border border-gray-200 px-2 py-1.5"
              title="Mark this article as a milestone."
            >
              <span className="text-xs font-medium text-gray-700">Milestone</span>
              <input
                type="checkbox"
                checked={isMilestone}
                onChange={(e) => setIsMilestone(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
            </label>
          </div>
        </CollapsibleAdminSection>
      )}

      {/* Header Content Section */}
      <CollapsibleAdminSection
        title={`Header Content (${selectedLocale.toUpperCase()})`}
        icon={<AlignLeft className="h-3.5 w-3.5" />}
        summary={i18nData.title?.trim() || 'untitled'}
        defaultOpen
      >
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Title *</label>
            <input
              type="text"
              value={i18nData.title}
              onChange={(e) => setI18nData({ ...i18nData, title: e.target.value })}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-base font-semibold"
              placeholder="Article Title"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Standfirst <span className="text-gray-400">(optionnel)</span>
            </label>
            <textarea
              value={i18nData.standfirst}
              onChange={(e) => setI18nData({ ...i18nData, standfirst: e.target.value })}
              rows={2}
              className="w-full rounded border border-gray-300 px-2 py-1 text-sm italic"
              placeholder="Short introduction..."
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Cover Title <span className="text-gray-400">(sous l'image de couverture)</span>
            </label>
            <textarea
              value={i18nData.coverTitle}
              onChange={(e) => setI18nData({ ...i18nData, coverTitle: e.target.value })}
              rows={2}
              className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
              placeholder="Caption text..."
              maxLength={240}
            />
          </div>
          <details className="rounded border border-gray-200 bg-gray-50">
            <summary className="cursor-pointer px-2 py-1 text-xs font-medium text-gray-700">
              SEO · Meta Title & Meta Description
            </summary>
            <div className="space-y-2 p-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Meta Title</label>
                <input
                  type="text"
                  value={i18nData.metaTitle || ''}
                  onChange={(e) => setI18nData({ ...i18nData, metaTitle: e.target.value })}
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Meta Description</label>
                <textarea
                  value={i18nData.metaDescription || ''}
                  onChange={(e) => setI18nData({ ...i18nData, metaDescription: e.target.value })}
                  rows={2}
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                />
              </div>
            </div>
          </details>
        </div>
      </CollapsibleAdminSection>

      {/* Blocks Section — déléguée au composant réutilisable. */}
      <ContentBlocksSection
        blocks={blocksDraft}
        entityId={articleId}
        saving={saving}
        onUpdateBlock={handleUpdateBlock}
        onPatchBlock={handlePatchBlock}
        onDeleteBlock={handleDeleteBlock}
        onReorderBlocks={handleReorderBlocks}
        onClickExportMarkdown={handleExportArticleBlocksMarkdown}
        onClickImportMarkdown={() => setShowMarkdownImport(true)}
        onClickAddBlock={async () => {
          // Sauvegarde tout (settings + i18n + blocs modifiés) avant de
          // naviguer vers la page modale d'ajout : sinon toute édition en
          // cours serait perdue au retour. handleSaveAll gère ses propres
          // toasts d'erreur ; on navigue malgré tout pour ne pas bloquer
          // l'utilisateur (l'API rejouera idempotente au save suivant).
          await handleSaveAll()
          router.push(`/admin/articles/${encodeURIComponent(articleId)}/add-block`)
        }}
      />

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
              throw new Error(messageFromAdminApiError(error, 'Translation failed'))
            }

            const data = await response.json()
            return data
          }}
        />
      )}

      <MarkdownImportDialog
        open={showMarkdownImport}
        onOpenChange={setShowMarkdownImport}
        articleId={articleId}
        locale={selectedLocale}
        currentBlockCount={blocksDraft.length}
        onApplied={async () => {
          toastSuccess('Import Markdown appliqué')
          setPreviewReloadEpoch((n) => n + 1)
          await fetchArticle()
        }}
        onAppliedBlocks={handleApplyArticleBlocksMarkdownImport}
      />

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

      </div>

      <div className="hidden min-h-0 min-w-0 flex-col lg:sticky lg:top-2 lg:flex lg:h-[calc(100dvh-5rem)] lg:max-h-[calc(100dvh-5rem)] lg:pl-6">
        <PagePreviewPanel
          title={previewPanelTitle}
          previewUrl={previewUrl}
          dismissible={false}
          toolbar={previewToolbar}
          reloadEpoch={previewReloadEpoch}
          className="min-h-0 flex-1"
        />
      </div>
    </section>
  )
}

