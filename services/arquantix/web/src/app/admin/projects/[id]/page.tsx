'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { MediaField } from '@/components/admin/MediaField'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { ContentStatus } from '@prisma/client'
import { supportedLocales, type Locale, defaultLocale } from '@/config/locales'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { TranslateModal } from '@/components/admin/TranslateModal'

interface InvestmentCategoryOption {
  id: string
  slug: string
  label: string
}

interface KeyInformationCategoryOption {
  id: string
  key: string
  label: string
  infoTitle?: string | null
  infoContent?: string | null
}

interface Project {
  id: string
  slug: string
  status: ContentStatus
  coverMediaId: string | null
  heroMediaId: string | null
  youtubeUrl: string | null
  investmentCategory: string | null
  coverMedia: {
    id: string
    url: string
    filename: string
  } | null
  heroMedia: {
    id: string
    url: string
    filename: string
  } | null
  i18n: Array<{
    id: string
    locale: string
    title: string
    location: string | null
    shortDescription: string | null
    description: string | null
    descriptionLinks?: Array<{
      label: string
      url: string
    }> | null
    metaTitle: string | null
    metaDescription: string | null
    competitiveAdvantages?: {
      title?: string | null
      rows?: Array<{
        icon: string
        iconBackgroundColor: string
        title: string
        description: string
      }>
    } | null
    howItWorks?: {
      title?: string | null
      content?: string | null
      links?: Array<{
        label: string
        url: string
      }>
    } | null
    keyInformation?: {
      title?: string | null
      rows?: Array<{
        categoryKey: string
        label: string
        value: string
        showInfoIcon?: boolean
        infoTitle?: string | null
        infoContent?: string | null
      }>
    } | null
    faq?: {
      enableTagRedirect?: boolean
      tagRedirectLabel?: string | null
      items?: Array<{
        articleId: string
        articleSlug: string
        collectionSlug: string
        categorySlug: string
        question: string
        standfirst?: string | null
      }>
    } | null
    translationStatus?: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
  }>
  gallery: Array<{
    id: string
    order: number
    media: {
      id: string
      url: string
      filename: string
    }
  }>
}

type CompetitiveAdvantageRow = {
  icon: string
  iconBackgroundColor: string
  category: 'content' | 'work' | 'note' | 'success' | 'danger'
  title: string
  description: string
}

const COMPETITIVE_ADVANTAGE_CATEGORY_OPTIONS = [
  { value: 'content', label: 'Contenu (blanc)' },
  { value: 'work', label: 'Travail (jaune)' },
  { value: 'note', label: 'Note informative (bleu clair)' },
  { value: 'success', label: 'Succès (vert)' },
  { value: 'danger', label: 'Danger / Alerte (rouge)' },
] as const

type CompetitiveAdvantagesConfig = {
  title: string
  rows: CompetitiveAdvantageRow[]
}

type HowItWorksLink = {
  label: string
  url: string
}

type DescriptionLinkRow = {
  label: string
  url: string
}

type ProjectFaqArticleRow = {
  articleId: string
  articleSlug: string
  collectionSlug: string
  categorySlug: string
  question: string
  standfirst: string
}

type ProjectFaqConfig = {
  enableTagRedirect: boolean
  tagRedirectLabel: string
  items: ProjectFaqArticleRow[]
}

type ProjectFaqOption = ProjectFaqArticleRow

type HowItWorksConfig = {
  title: string
  content: string
  links: HowItWorksLink[]
}

type KeyInformationRow = {
  categoryKey: string
  label: string
  value: string
  showInfoIcon: boolean
  infoTitle: string
  infoContent: string
}

type KeyInformationConfig = {
  title: string
  rows: KeyInformationRow[]
}

const COMPETITIVE_ADVANTAGE_ICON_OPTIONS = [
  { value: 'assignment_turned_in_rounded', label: 'Validation' },
  { value: 'favorite_rounded', label: 'Favorite' },
  { value: 'trending_up_rounded', label: 'Trending up' },
  { value: 'apartment_rounded', label: 'Building' },
  { value: 'check_circle_rounded', label: 'Check circle' },
  { value: 'insights_rounded', label: 'Insights' },
] as const

export default function AdminProjectEditorPage() {
  const router = useRouter()
  const params = useParams()
  const projectId = (params?.id as string | undefined) ?? ''
  const blockProjectBasedEo = process.env.NEXT_PUBLIC_ADMIN_BLOCK_PROJECT_BASED_EO === 'true'

  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [investmentCategories, setInvestmentCategories] = useState<InvestmentCategoryOption[]>([])
  const [keyInformationCategories, setKeyInformationCategories] = useState<KeyInformationCategoryOption[]>([])
  const [selectedLocale, setSelectedLocale] = useState<Locale>(defaultLocale)
  const [galleryPickerKey, setGalleryPickerKey] = useState(0)
  const [showUnpublishDialog, setShowUnpublishDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showTranslateModal, setShowTranslateModal] = useState(false)
  const [hasGlossary, setHasGlossary] = useState(false)
  const [approving, setApproving] = useState(false)
  const [i18nData, setI18nData] = useState({
    title: '',
    location: '',
    shortDescription: '',
    description: '',
    metaTitle: '',
    metaDescription: '',
  })
  const [competitiveAdvantagesConfig, setCompetitiveAdvantagesConfig] = useState<CompetitiveAdvantagesConfig>({
    title: '',
    rows: [],
  })
  const [howItWorksConfig, setHowItWorksConfig] = useState<HowItWorksConfig>({
    title: '',
    content: '',
    links: [],
  })
  const [keyInformationConfig, setKeyInformationConfig] = useState<KeyInformationConfig>({
    title: '',
    rows: [],
  })
  const [descriptionLinks, setDescriptionLinks] = useState<DescriptionLinkRow[]>([])
  const [faqConfig, setFaqConfig] = useState<ProjectFaqConfig>({
    enableTagRedirect: false,
    tagRedirectLabel: 'Voir toutes les FAQ de ce projet',
    items: [],
  })
  const [faqArticleOptions, setFaqArticleOptions] = useState<ProjectFaqOption[]>([])
  const [selectedFaqArticleId, setSelectedFaqArticleId] = useState('')
  const [lendingProductData, setLendingProductData] = useState<Record<string, any> | null>(null)
  const [lendingLoading, setLendingLoading] = useState(true)
  const [linkingProduct, setLinkingProduct] = useState(false)
  const [transitioningStatus, setTransitioningStatus] = useState(false)
  const [lendingForm, setLendingForm] = useState({
    borrowerId: '',
    asset: 'USDC',
    targetSize: '',
    supplyAprBps: '800',
  })
  const [lendingFormErrors, setLendingFormErrors] = useState<Record<string, string>>({})

  const normalizeExternalUrl = (value: string): string => {
    const raw = value.trim()
    if (!raw) return ''
    if (/^https?:\/\//i.test(raw)) return raw
    return `https://${raw}`
  }

  const deriveLinkLabel = (label: string, url: string): string => {
    const cleanLabel = label.trim()
    if (cleanLabel.length > 0) return cleanLabel
    const normalizedUrl = normalizeExternalUrl(url)
    if (!normalizedUrl) return ''
    try {
      const parsed = new URL(normalizedUrl)
      return parsed.hostname.replace(/^www\./, '')
    } catch {
      return normalizedUrl
    }
  }

  const buildCompetitiveAdvantagesPayload = () => ({
    title: competitiveAdvantagesConfig.title.trim() || null,
    rows: competitiveAdvantagesConfig.rows
      .map((row) => ({
        icon: row.icon.trim(),
        iconBackgroundColor: row.iconBackgroundColor.trim(),
        category: row.category || 'content',
        title: row.title.trim(),
        description: row.description.trim(),
      })),
  })

  const parseCompetitiveAdvantagesFromI18n = (raw: any): CompetitiveAdvantagesConfig => {
    const rows = Array.isArray(raw?.rows)
      ? raw.rows
          .filter((row: any) => row && typeof row === 'object')
          .map((row: any) => {
            const cat = (row.category ?? 'content').toString().trim().toLowerCase()
            const validCat = ['work', 'note', 'success', 'danger'].includes(cat) ? cat : 'content'
            return {
              icon:
                typeof row.icon === 'string' && row.icon.trim().length > 0
                  ? row.icon
                  : 'check_circle_rounded',
              iconBackgroundColor:
                typeof row.iconBackgroundColor === 'string' &&
                row.iconBackgroundColor.trim().length > 0
                  ? row.iconBackgroundColor
                  : '#1E88E5',
              category: validCat as 'content' | 'work' | 'note' | 'success' | 'danger',
              title: typeof row.title === 'string' ? row.title : '',
              description: typeof row.description === 'string' ? row.description : '',
            }
          })
      : []

    return {
      title: typeof raw?.title === 'string' ? raw.title : '',
      rows,
    }
  }

  const buildHowItWorksPayload = () => ({
    title: howItWorksConfig.title.trim() || null,
    content: howItWorksConfig.content.trim() || null,
    links: howItWorksConfig.links
      .map((link) => ({
        label: link.label.trim(),
        url: link.url.trim(),
      }))
      .filter((link) => link.label.length > 0 && link.url.length > 0),
  })

  const parseHowItWorksFromI18n = (raw: any): HowItWorksConfig => {
    const links = Array.isArray(raw?.links)
      ? raw.links
          .filter((link: any) => link && typeof link === 'object')
          .map((link: any) => ({
            label: typeof link.label === 'string' ? link.label : '',
            url: typeof link.url === 'string' ? link.url : '',
          }))
      : []

    return {
      title: typeof raw?.title === 'string' ? raw.title : '',
      content: typeof raw?.content === 'string' ? raw.content : '',
      links,
    }
  }

  const parseDescriptionLinksFromI18n = (raw: any): DescriptionLinkRow[] => {
    if (!Array.isArray(raw)) return []
    return raw
      .filter((link: any) => link && typeof link === 'object')
      .map((link: any) => ({
        url: typeof link.url === 'string' ? link.url : '',
        label: deriveLinkLabel(
          typeof link.label === 'string' ? link.label : '',
          typeof link.url === 'string' ? link.url : ''
        ),
      }))
  }

  const parseFaqFromI18n = (raw: any): ProjectFaqConfig => {
    const items = Array.isArray(raw?.items)
      ? raw.items
          .filter((item: any) => item && typeof item === 'object')
          .map((item: any) => ({
            articleId: typeof item.articleId === 'string' ? item.articleId : '',
            articleSlug: typeof item.articleSlug === 'string' ? item.articleSlug : '',
            collectionSlug: typeof item.collectionSlug === 'string' ? item.collectionSlug : '',
            categorySlug: typeof item.categorySlug === 'string' ? item.categorySlug : '',
            question: typeof item.question === 'string' ? item.question : '',
            standfirst: typeof item.standfirst === 'string' ? item.standfirst : '',
          }))
          .filter((item: ProjectFaqArticleRow) =>
              item.articleId.trim().length > 0 &&
              item.articleSlug.trim().length > 0 &&
              item.collectionSlug.trim().length > 0 &&
              item.categorySlug.trim().length > 0 &&
              item.question.trim().length > 0
          )
      : []

    return {
      enableTagRedirect: raw?.enableTagRedirect === true,
      tagRedirectLabel:
        typeof raw?.tagRedirectLabel === 'string' && raw.tagRedirectLabel.trim().length > 0
          ? raw.tagRedirectLabel
          : 'Voir toutes les FAQ de ce projet',
      items,
    }
  }

  const buildFaqPayload = () => ({
    enableTagRedirect: faqConfig.enableTagRedirect === true,
    tagRedirectLabel: faqConfig.tagRedirectLabel.trim() || null,
    items: faqConfig.items
      .map((item) => ({
        articleId: item.articleId.trim(),
        articleSlug: item.articleSlug.trim(),
        collectionSlug: item.collectionSlug.trim(),
        categorySlug: item.categorySlug.trim(),
        question: item.question.trim(),
        standfirst: item.standfirst.trim() || null,
      }))
      .filter(
        (item) =>
          item.articleId.length > 0 &&
          item.articleSlug.length > 0 &&
          item.collectionSlug.length > 0 &&
          item.categorySlug.length > 0 &&
          item.question.length > 0
      ),
  })

  const buildKeyInformationPayload = () => ({
    title: keyInformationConfig.title.trim() || null,
    rows: keyInformationConfig.rows
      .map((row) => ({
        categoryKey: row.categoryKey.trim(),
        label: row.label.trim(),
        value: row.value.trim(),
        showInfoIcon: row.showInfoIcon === true,
        infoTitle: row.infoTitle.trim() || null,
        infoContent: row.infoContent.trim() || null,
      }))
      .filter((row) => row.categoryKey.length > 0 && row.label.length > 0 && row.value.length > 0),
  })

  const parseKeyInformationFromI18n = (raw: any): KeyInformationConfig => {
    const rows = Array.isArray(raw?.rows)
      ? raw.rows
          .filter((row: any) => row && typeof row === 'object')
          .map((row: any) => ({
            categoryKey: typeof row.categoryKey === 'string' ? row.categoryKey : '',
            label: typeof row.label === 'string' ? row.label : '',
            value: typeof row.value === 'string' ? row.value : '',
            showInfoIcon: row.showInfoIcon === true,
            infoTitle: typeof row.infoTitle === 'string' ? row.infoTitle : '',
            infoContent: typeof row.infoContent === 'string' ? row.infoContent : '',
          }))
      : []

    return {
      title: typeof raw?.title === 'string' ? raw.title : '',
      rows,
    }
  }

  useEffect(() => {
    if (!projectId) return
    fetchProject()
  }, [projectId])

  useEffect(() => {
    fetchInvestmentCategories()
    fetchKeyInformationCategories()
    fetchLendingProductData()
    if (projectId) {
      fetchFaqArticleOptions(projectId, selectedLocale)
    }
  }, [])

  const fetchLendingProductData = async () => {
    if (!projectId) return
    setLendingLoading(true)
    try {
      const res = await fetch(`/api/admin/lending/product-data?project_id=${projectId}`)
      if (res.ok) {
        const json = await res.json()
        if (json.data) {
          setLendingProductData({ [projectId]: json.data })
        } else {
          setLendingProductData(null)
        }
      }
    } catch {
      setLendingProductData(null)
    } finally {
      setLendingLoading(false)
    }
  }

  const fetchInvestmentCategories = async () => {
    try {
      const res = await fetch('/api/admin/investment-categories')
      if (res.ok) {
        const data = await res.json()
        setInvestmentCategories(data.categories ?? [])
      }
    } catch {
      // ignore
    }
  }

  const fetchKeyInformationCategories = async () => {
    try {
      const res = await fetch('/api/admin/key-information-categories')
      if (res.ok) {
        const data = await res.json()
        setKeyInformationCategories(data.categories ?? [])
      }
    } catch {
      // ignore
    }
  }

  const fetchFaqArticleOptions = async (id: string, locale: Locale) => {
    try {
      const res = await fetch(`/api/admin/projects/${id}/faq-options?locale=${locale}&t=${Date.now()}`, {
        cache: 'no-store',
      })
      if (res.ok) {
        const data = await res.json()
        setFaqArticleOptions(Array.isArray(data.options) ? data.options : [])
      } else {
        setFaqArticleOptions([])
      }
    } catch {
      setFaqArticleOptions([])
    }
  }

  const fetchProject = async () => {
    try {
      const response = await fetch(`/api/admin/projects/${projectId}?t=${Date.now()}`, {
        cache: 'no-store',
      })
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        if (response.status === 404) {
          router.push('/admin/projects')
          return
        }
        throw new Error('Failed to fetch project')
      }

      const data = await response.json()
      setProject(data.project)
      
      const i18n = data.project.i18n.find((i: any) => i.locale === selectedLocale)
      if (i18n) {
        setI18nData({
          title: i18n.title || '',
          location: i18n.location || '',
          shortDescription: i18n.shortDescription || '',
          description: i18n.description || '',
          metaTitle: i18n.metaTitle || '',
          metaDescription: i18n.metaDescription || '',
        })
        setCompetitiveAdvantagesConfig(parseCompetitiveAdvantagesFromI18n(i18n.competitiveAdvantages))
        setHowItWorksConfig(parseHowItWorksFromI18n(i18n.howItWorks))
        setKeyInformationConfig(parseKeyInformationFromI18n(i18n.keyInformation))
        setDescriptionLinks(parseDescriptionLinksFromI18n(i18n.descriptionLinks))
        setFaqConfig(parseFaqFromI18n(i18n.faq))
      } else {
        setI18nData({
          title: '',
          location: '',
          shortDescription: '',
          description: '',
          metaTitle: '',
          metaDescription: '',
        })
        setCompetitiveAdvantagesConfig({ title: '', rows: [] })
        setHowItWorksConfig({ title: '', content: '', links: [] })
        setKeyInformationConfig({ title: '', rows: [] })
        setDescriptionLinks([])
        setFaqConfig({
          enableTagRedirect: false,
          tagRedirectLabel: 'Voir toutes les FAQ de ce projet',
          items: [],
        })
      }
    } catch (error) {
      console.error('Error fetching project:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveSettings = async () => {
    if (!project) return

    setSaving(true)
    try {
      const response = await fetch(`/api/admin/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slug: project.slug,
          status: project.status,
          coverMediaId: project.coverMediaId,
          heroMediaId: project.heroMediaId,
          youtubeUrl: project.youtubeUrl,
          investmentCategory: project.investmentCategory,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to update project')
      }

      toastSuccess('Saved')
      await fetchProject()
    } catch (error: any) {
      toastError(error.message || 'An error occurred')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveI18n = async () => {
    if (!project) return

    setSaving(true)
    try {
      // Normalize empty strings to null/undefined before sending
      const payload = {
        locale: selectedLocale,
        title: i18nData.title,
        location: i18nData.location && i18nData.location.trim() !== '' ? i18nData.location.trim() : undefined,
        shortDescription: i18nData.shortDescription && i18nData.shortDescription.trim() !== '' ? i18nData.shortDescription.trim() : undefined,
        description: i18nData.description && i18nData.description.trim() !== '' ? i18nData.description.trim() : undefined,
        metaTitle: i18nData.metaTitle && i18nData.metaTitle.trim() !== '' ? i18nData.metaTitle.trim() : undefined,
        metaDescription: i18nData.metaDescription && i18nData.metaDescription.trim() !== '' ? i18nData.metaDescription.trim() : undefined,
        competitiveAdvantages: buildCompetitiveAdvantagesPayload(),
        howItWorks: buildHowItWorksPayload(),
        keyInformation: buildKeyInformationPayload(),
        faq: buildFaqPayload(),
        descriptionLinks: descriptionLinks
          .map((link) => ({
            url: normalizeExternalUrl(link.url),
            label: deriveLinkLabel(link.label, link.url),
          }))
          .filter((link) => link.url.length > 0),
      }

      const response = await fetch(`/api/admin/projects/${projectId}/i18n`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to update content')
      }

      toastSuccess('Saved')
      await fetchProject()
    } catch (error: any) {
      toastError(error.message || 'An error occurred')
    } finally {
      setSaving(false)
    }
  }

  const handlePublish = async () => {
    if (!project) return

    setSaving(true)
    try {
      const response = await fetch(`/api/admin/projects/${projectId}/publish`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to publish project')
      }

      const data = await response.json()
      if (data.warning) {
        // Show warning but still consider it a success
        toastError(data.warning)
      } else {
        toastSuccess('Published')
      }
      await fetchProject()
    } catch (error: any) {
      toastError(error.message || 'An error occurred')
    } finally {
      setSaving(false)
    }
  }

  const handleUnpublish = async () => {
    if (!project) return

    setSaving(true)
    try {
      const response = await fetch(`/api/admin/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'DRAFT',
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to unpublish project')
      }

      toastSuccess('Set to draft')
      await fetchProject()
      setShowUnpublishDialog(false)
    } catch (error: any) {
      toastError(error.message || 'An error occurred')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!project) return

    setSaving(true)
    try {
      const response = await fetch(`/api/admin/projects/${projectId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete project')
      }

      toastSuccess('Deleted')
      router.push('/admin/projects')
    } catch (error: any) {
      toastError(error.message || 'An error occurred')
      setSaving(false)
    }
  }

  const handleApproveTranslation = async () => {
    if (!project) return
    setApproving(true)
    try {
      const res = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityType: 'PROJECT',
          entityId: project.id,
          locale: selectedLocale,
        }),
      })
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.error || 'Failed to approve translation')
      }
      toastSuccess('Translation approved')
      await fetchProject() // Reload to update status
    } catch (error: any) {
      toastError(error.message || 'Failed to approve translation')
    } finally {
      setApproving(false)
    }
  }

  const handleAddGalleryMedia = async (mediaId: string) => {
    if (!project) return

    try {
      const response = await fetch(`/api/admin/projects/${projectId}/gallery`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mediaId }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to add media')
      }

      setGalleryPickerKey((prev) => prev + 1)
      await fetchProject()
    } catch (error: any) {
      toastError(error.message || 'An error occurred')
    }
  }

  const handleRemoveGalleryMedia = async (projectMediaId: string) => {
    if (!project) return
    if (!confirm('Remove this image from gallery?')) return

    try {
      const response = await fetch(`/api/admin/projects/${projectId}/gallery/${projectMediaId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to remove media')
      }

      await fetchProject()
    } catch (error: any) {
      toastError(error.message || 'An error occurred')
    }
  }

  useEffect(() => {
    // Check if glossary exists
    fetch('/api/admin/settings/translation')
      .then((res) => res.json())
      .then((data) => {
        setHasGlossary(!!data.settings?.translationGlossary)
      })
      .catch(() => setHasGlossary(false))
  }, [])

  useEffect(() => {
    if (!project) return
    
    const i18n = project.i18n.find((i) => i.locale === selectedLocale)
    if (i18n) {
      setI18nData({
        title: i18n.title || '',
        location: i18n.location || '',
        shortDescription: i18n.shortDescription || '',
        description: i18n.description || '',
        metaTitle: i18n.metaTitle || '',
        metaDescription: i18n.metaDescription || '',
      })
      setCompetitiveAdvantagesConfig(parseCompetitiveAdvantagesFromI18n(i18n.competitiveAdvantages))
      setHowItWorksConfig(parseHowItWorksFromI18n(i18n.howItWorks))
      setKeyInformationConfig(parseKeyInformationFromI18n(i18n.keyInformation))
      setDescriptionLinks(parseDescriptionLinksFromI18n(i18n.descriptionLinks))
      setFaqConfig(parseFaqFromI18n(i18n.faq))
    } else {
      setI18nData({
        title: '',
        location: '',
        shortDescription: '',
        description: '',
        metaTitle: '',
        metaDescription: '',
      })
      setCompetitiveAdvantagesConfig({ title: '', rows: [] })
      setHowItWorksConfig({ title: '', content: '', links: [] })
      setKeyInformationConfig({ title: '', rows: [] })
      setDescriptionLinks([])
      setFaqConfig({
        enableTagRedirect: false,
        tagRedirectLabel: 'Voir toutes les FAQ de ce projet',
        items: [],
      })
    }
  }, [selectedLocale, project])

  useEffect(() => {
    if (!projectId) return
    fetchFaqArticleOptions(projectId, selectedLocale)
  }, [projectId, selectedLocale])

  const addCompetitiveAdvantageRow = () => {
    setCompetitiveAdvantagesConfig((prev) => ({
      ...prev,
      rows: [
        ...prev.rows,
        {
          icon: 'check_circle_rounded',
          iconBackgroundColor: '#1E88E5',
          category: 'content',
          title: '',
          description: '',
        },
      ],
    }))
  }

  const updateCompetitiveAdvantageRow = (
    index: number,
    patch: Partial<CompetitiveAdvantageRow>
  ) => {
    setCompetitiveAdvantagesConfig((prev) => ({
      ...prev,
      rows: prev.rows.map((row, i) => (i === index ? { ...row, ...patch } : row)),
    }))
  }

  const removeCompetitiveAdvantageRow = (index: number) => {
    setCompetitiveAdvantagesConfig((prev) => ({
      ...prev,
      rows: prev.rows.filter((_, i) => i !== index),
    }))
  }

  const moveCompetitiveAdvantageRow = (index: number, direction: -1 | 1) => {
    setCompetitiveAdvantagesConfig((prev) => {
      const targetIndex = index + direction
      if (targetIndex < 0 || targetIndex >= prev.rows.length) return prev
      const rows = [...prev.rows]
      const current = rows[index]
      rows[index] = rows[targetIndex]
      rows[targetIndex] = current
      return { ...prev, rows }
    })
  }

  const addHowItWorksLink = () => {
    setHowItWorksConfig((prev) => ({
      ...prev,
      links: [...prev.links, { label: '', url: '' }],
    }))
  }

  const updateHowItWorksLink = (index: number, patch: Partial<HowItWorksLink>) => {
    setHowItWorksConfig((prev) => ({
      ...prev,
      links: prev.links.map((link, i) => (i === index ? { ...link, ...patch } : link)),
    }))
  }

  const removeHowItWorksLink = (index: number) => {
    setHowItWorksConfig((prev) => ({
      ...prev,
      links: prev.links.filter((_, i) => i !== index),
    }))
  }

  const moveHowItWorksLink = (index: number, direction: -1 | 1) => {
    setHowItWorksConfig((prev) => {
      const targetIndex = index + direction
      if (targetIndex < 0 || targetIndex >= prev.links.length) return prev
      const links = [...prev.links]
      const current = links[index]
      links[index] = links[targetIndex]
      links[targetIndex] = current
      return { ...prev, links }
    })
  }

  const addDescriptionLink = () => {
    setDescriptionLinks((prev) => [...prev, { label: '', url: '' }])
  }

  const updateDescriptionLink = (index: number, patch: Partial<DescriptionLinkRow>) => {
    setDescriptionLinks((prev) => prev.map((link, i) => (i === index ? { ...link, ...patch } : link)))
  }

  const removeDescriptionLink = (index: number) => {
    setDescriptionLinks((prev) => prev.filter((_, i) => i !== index))
  }

  const moveDescriptionLink = (index: number, direction: -1 | 1) => {
    setDescriptionLinks((prev) => {
      const targetIndex = index + direction
      if (targetIndex < 0 || targetIndex >= prev.length) return prev
      const links = [...prev]
      const current = links[index]
      links[index] = links[targetIndex]
      links[targetIndex] = current
      return links
    })
  }

  const addFaqArticleRow = () => {
    const option = faqArticleOptions.find((item) => item.articleId === selectedFaqArticleId)
    if (!option) return
    setFaqConfig((prev) => {
      if (prev.items.some((row) => row.articleId === option.articleId)) {
        return prev
      }
      return {
        ...prev,
        items: [...prev.items, option],
      }
    })
    setSelectedFaqArticleId('')
  }

  const removeFaqArticleRow = (index: number) => {
    setFaqConfig((prev) => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index),
    }))
  }

  const moveFaqArticleRow = (index: number, direction: -1 | 1) => {
    setFaqConfig((prev) => {
      const targetIndex = index + direction
      if (targetIndex < 0 || targetIndex >= prev.items.length) return prev
      const items = [...prev.items]
      const current = items[index]
      items[index] = items[targetIndex]
      items[targetIndex] = current
      return { ...prev, items }
    })
  }

  const addKeyInformationRow = () => {
    const firstCategory = keyInformationCategories[0]
    setKeyInformationConfig((prev) => ({
      ...prev,
      rows: [
        ...prev.rows,
        {
          categoryKey: firstCategory?.key ?? '',
          label: firstCategory?.label ?? '',
          value: '',
          showInfoIcon: !!(firstCategory?.infoTitle || firstCategory?.infoContent),
          infoTitle: firstCategory?.infoTitle ?? '',
          infoContent: firstCategory?.infoContent ?? '',
        },
      ],
    }))
  }

  const updateKeyInformationRow = (index: number, patch: Partial<KeyInformationRow>) => {
    setKeyInformationConfig((prev) => ({
      ...prev,
      rows: prev.rows.map((row, i) => (i === index ? { ...row, ...patch } : row)),
    }))
  }

  const updateKeyInformationCategory = (index: number, categoryKey: string) => {
    const category = keyInformationCategories.find((item) => item.key === categoryKey)
    updateKeyInformationRow(index, {
      categoryKey,
      label: category?.label ?? '',
      showInfoIcon: !!(category?.infoTitle || category?.infoContent),
      infoTitle: category?.infoTitle ?? '',
      infoContent: category?.infoContent ?? '',
    })
  }

  const removeKeyInformationRow = (index: number) => {
    setKeyInformationConfig((prev) => ({
      ...prev,
      rows: prev.rows.filter((_, i) => i !== index),
    }))
  }

  const moveKeyInformationRow = (index: number, direction: -1 | 1) => {
    setKeyInformationConfig((prev) => {
      const targetIndex = index + direction
      if (targetIndex < 0 || targetIndex >= prev.rows.length) return prev
      const rows = [...prev.rows]
      const current = rows[index]
      rows[index] = rows[targetIndex]
      rows[targetIndex] = current
      return { ...prev, rows }
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading project...</div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Project not found.</div>
      </div>
    )
  }

  const publicUrl = `/projects/${project.slug}`

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Edit Project</h1>
          <p className="text-sm text-gray-500 mt-1">
            Public URL: <a href={publicUrl} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">{publicUrl}</a>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/admin/projects"
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            ← Back to Projects
          </Link>
          <Button
            onClick={() => setShowDeleteDialog(true)}
            disabled={saving}
            className="bg-red-600 hover:bg-red-700 text-white"
          >
            Delete Project
          </Button>
        </div>
      </div>

      {/* Project Settings Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Project Settings</h2>
            <p className="text-sm text-gray-500 mt-1">Configure basic project information and media</p>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`px-3 py-1 text-sm font-semibold rounded-full ${
                project.status === 'PUBLISHED'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {project.status}
            </span>
            {project.status === 'DRAFT' && (
              <Button 
                onClick={handlePublish} 
                disabled={saving}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                Publish Project
              </Button>
            )}
            {project.status === 'PUBLISHED' && (
              <Button 
                onClick={() => setShowUnpublishDialog(true)} 
                disabled={saving}
                className="bg-orange-600 hover:bg-orange-700 text-white"
              >
                Set to Draft
              </Button>
            )}
          </div>
        </div>

        <div className="space-y-6">
          {/* Slug */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Slug
            </label>
            <input
              type="text"
              value={project.slug}
              onChange={(e) => setProject({ ...project, slug: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          {/* Catégorie d'investissement */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Catégorie d&apos;investissement
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Utilisée pour le filtre par catégorie sur la page Offres (app mobile)
            </p>
            <select
              value={project.investmentCategory ?? ''}
              onChange={(e) =>
                setProject({
                  ...project,
                  investmentCategory: e.target.value || null,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">— Aucune —</option>
              {investmentCategories.map((c) => (
                <option key={c.id} value={c.label}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* Exclusive Lending Offer (Phase 2A.11.5) */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Exclusive Lending Offer</h3>
            <p className="text-xs text-gray-500 mb-4">
              Transform this project into an investable exclusive lending offer.
            </p>
            {blockProjectBasedEo && (
              <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                Création lending depuis ce projet CMS est <strong>désactivée</strong>. Utilisez Vault Builder →
                Packaged Product → moteur lending. Rollback :{' '}
                <code className="rounded bg-amber-100/80 px-1">ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO=true</code>
              </div>
            )}
            {lendingLoading ? (
              <div className="flex items-center gap-2 text-sm text-gray-400 py-4">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                Loading lending data...
              </div>
            ) : (() => {
              const lending = lendingProductData?.[projectId] ?? null
              if (!lending) {
                return (
                  <div className="border border-dashed border-gray-300 rounded-md p-6 bg-gray-50">
                    <p className="text-sm text-gray-600 mb-4">
                      No lending product linked to this project.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Borrower (Customer)</label>
                        <input
                          type="text"
                          value={lendingForm.borrowerId}
                          onChange={(e) => {
                            setLendingForm(f => ({ ...f, borrowerId: e.target.value }))
                            setLendingFormErrors(e2 => ({ ...e2, borrowerId: '' }))
                          }}
                          className={`w-full px-3 py-2 border rounded-md text-sm ${lendingFormErrors.borrowerId ? 'border-red-400 bg-red-50' : 'border-gray-300'}`}
                          placeholder="UUID Customer (person) ou client portfolio"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          ID de la fiche Customer 360 (personne), ou UUID client portefeuille si tu le connais. Le
                          moteur prêt résout vers le client portfolio interne (pe_clients).
                        </p>
                        {lendingFormErrors.borrowerId && <p className="text-xs text-red-500 mt-1">{lendingFormErrors.borrowerId}</p>}
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Asset</label>
                        <select
                          value={lendingForm.asset}
                          onChange={(e) => setLendingForm(f => ({ ...f, asset: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        >
                          <option value="USDC">USDC</option>
                          <option value="USDT">USDT</option>
                          <option value="BTC">BTC</option>
                          <option value="ETH">ETH</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Target Size</label>
                        <input
                          type="number"
                          value={lendingForm.targetSize}
                          onChange={(e) => {
                            setLendingForm(f => ({ ...f, targetSize: e.target.value }))
                            setLendingFormErrors(e2 => ({ ...e2, targetSize: '' }))
                          }}
                          className={`w-full px-3 py-2 border rounded-md text-sm ${lendingFormErrors.targetSize ? 'border-red-400 bg-red-50' : 'border-gray-300'}`}
                          placeholder="2000000"
                          min="1"
                        />
                        {lendingFormErrors.targetSize && <p className="text-xs text-red-500 mt-1">{lendingFormErrors.targetSize}</p>}
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Supply APR (bps)</label>
                        <input
                          type="number"
                          value={lendingForm.supplyAprBps}
                          onChange={(e) => {
                            setLendingForm(f => ({ ...f, supplyAprBps: e.target.value }))
                            setLendingFormErrors(e2 => ({ ...e2, supplyAprBps: '' }))
                          }}
                          className={`w-full px-3 py-2 border rounded-md text-sm ${lendingFormErrors.supplyAprBps ? 'border-red-400 bg-red-50' : 'border-gray-300'}`}
                          min="0"
                        />
                        {lendingFormErrors.supplyAprBps && <p className="text-xs text-red-500 mt-1">{lendingFormErrors.supplyAprBps}</p>}
                      </div>
                    </div>
                    <button
                      onClick={async () => {
                        const errors: Record<string, string> = {}
                        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
                        if (!lendingForm.borrowerId.trim()) {
                          errors.borrowerId = 'UUID emprunteur (Customer) requis'
                        } else if (!uuidRegex.test(lendingForm.borrowerId.trim())) {
                          errors.borrowerId = 'Must be a valid UUID'
                        }
                        if (!lendingForm.targetSize || parseFloat(lendingForm.targetSize) <= 0) {
                          errors.targetSize = 'Target size must be greater than 0'
                        }
                        if (!lendingForm.supplyAprBps || parseFloat(lendingForm.supplyAprBps) <= 0) {
                          errors.supplyAprBps = 'Supply APR must be greater than 0'
                        }
                        if (Object.keys(errors).length > 0) {
                          setLendingFormErrors(errors)
                          return
                        }

                        setLinkingProduct(true)
                        const aprVal = parseFloat(lendingForm.supplyAprBps)
                        const payload = {
                          project_id: projectId,
                          borrower_client_id: lendingForm.borrowerId.trim(),
                          asset: lendingForm.asset,
                          target_size: parseFloat(lendingForm.targetSize),
                          title: i18nData.title || project?.slug || '',
                          supply_apr_bps: aprVal,
                          borrow_apr_bps: aprVal + 200,
                        }
                        console.log('[LendingProduct] Creating with payload:', payload)

                        try {
                          const res = await fetch('/api/admin/lending/create-from-project', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload),
                          })
                          const data = await res.json()
                          console.log('[LendingProduct] Response:', res.status, data)

                          if (!res.ok) {
                            const errorMsg = data.detail || data.error || 'Failed to create lending product'
                            throw new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg))
                          }

                          toastSuccess('Lending product created successfully!')
                          setLendingProductData({
                            [projectId]: {
                              lending_product_id: data.product_id || data.id,
                              apy: data.supply_apr != null ? Number(data.supply_apr) : aprVal / 100,
                              raised: 0,
                              target: parseFloat(lendingForm.targetSize),
                              progress: 0,
                              investorsCount: 0,
                              asset: lendingForm.asset,
                              status: data.status || 'draft',
                              borrower_client_id: data.borrower_client_id || lendingForm.borrowerId.trim(),
                              pool_id: data.pool_id || data.lending_pool_id,
                            },
                          })

                          setTimeout(() => fetchLendingProductData(), 1000)
                        } catch (error: any) {
                          console.error('[LendingProduct] Error:', error)
                          toastError(error.message || 'An error occurred while creating the lending product')
                        } finally {
                          setLinkingProduct(false)
                        }
                      }}
                      disabled={linkingProduct || blockProjectBasedEo}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-md disabled:opacity-50 transition-colors"
                    >
                      {linkingProduct && (
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                      )}
                      {linkingProduct ? 'Creating...' : 'Create Lending Product'}
                    </button>
                  </div>
                )
              }
              return (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                      <p className="text-xs text-blue-600 font-medium">APY</p>
                      <p className="text-lg font-bold text-blue-900">{lending.apy}%</p>
                    </div>
                    <div className="bg-green-50 rounded-lg p-3 border border-green-200">
                      <p className="text-xs text-green-600 font-medium">Progress</p>
                      <p className="text-lg font-bold text-green-900">{(lending.progress ?? 0).toFixed(1)}%</p>
                      <p className="text-xs text-green-600">{(lending.raised ?? 0).toLocaleString()} / {(lending.target ?? 0).toLocaleString()} {lending.asset}</p>
                    </div>
                    <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
                      <p className="text-xs text-purple-600 font-medium">Investors</p>
                      <p className="text-lg font-bold text-purple-900">{lending.investorsCount ?? 0}</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                      <p className="text-xs text-gray-600 font-medium">Status</p>
                      <p className={`text-lg font-bold ${
                        lending.status === 'active' ? 'text-green-700' :
                        lending.status === 'fundraising' ? 'text-blue-700' :
                        lending.status === 'draft' ? 'text-amber-600' :
                        'text-gray-700'
                      }`}>{lending.status}</p>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 space-y-1">
                    <p><span className="font-medium">Product ID:</span> {lending.lending_product_id}</p>
                    <p><span className="font-medium">Pool ID:</span> {lending.pool_id}</p>
                    <p><span className="font-medium">Borrower:</span> {lending.borrower_client_id}</p>
                    <p><span className="font-medium">Asset:</span> {lending.asset}</p>
                  </div>

                  {/* Status transition buttons */}
                  <div className="flex flex-wrap gap-2 pt-2">
                    {lending.status === 'draft' && (
                      <button
                        onClick={async () => {
                          if (!confirm('Ouvrir la levée de fonds pour cette offre ?')) return
                          setTransitioningStatus(true)
                          try {
                            const res = await fetch(`/api/admin/lending/products/${lending.lending_product_id}/transition`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ action: 'open-fundraising' }),
                            })
                            const data = await res.json()
                            if (!res.ok) throw new Error(data.detail || 'Failed')
                            toastSuccess('Status → fundraising')
                            fetchLendingProductData()
                          } catch (err: any) {
                            toastError(err.message || 'Transition failed')
                          } finally {
                            setTransitioningStatus(false)
                          }
                        }}
                        disabled={transitioningStatus}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md disabled:opacity-50 transition-colors"
                      >
                        {transitioningStatus && (
                          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                        )}
                        Open Fundraising
                      </button>
                    )}
                    {(lending.status === 'fundraising' || lending.status === 'funded') && (
                      <button
                        onClick={async () => {
                          if (!confirm('Activer cette offre ? Cela déclenchera l\'emprunt automatique.')) return
                          setTransitioningStatus(true)
                          try {
                            const res = await fetch(`/api/admin/lending/products/${lending.lending_product_id}/transition`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ action: 'activate' }),
                            })
                            const data = await res.json()
                            if (!res.ok) throw new Error(data.detail || 'Failed')
                            toastSuccess('Status → active')
                            fetchLendingProductData()
                          } catch (err: any) {
                            toastError(err.message || 'Transition failed')
                          } finally {
                            setTransitioningStatus(false)
                          }
                        }}
                        disabled={transitioningStatus}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-md disabled:opacity-50 transition-colors"
                      >
                        {transitioningStatus && (
                          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                        )}
                        Activate
                      </button>
                    )}
                    {lending.status === 'active' && (
                      <button
                        onClick={async () => {
                          if (!confirm('Marquer cette offre comme remboursée ?')) return
                          setTransitioningStatus(true)
                          try {
                            const res = await fetch(`/api/admin/lending/products/${lending.lending_product_id}/transition`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ action: 'mark-repaid' }),
                            })
                            const data = await res.json()
                            if (!res.ok) throw new Error(data.detail || 'Failed')
                            toastSuccess('Status → repaid')
                            fetchLendingProductData()
                          } catch (err: any) {
                            toastError(err.message || 'Transition failed')
                          } finally {
                            setTransitioningStatus(false)
                          }
                        }}
                        disabled={transitioningStatus}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium rounded-md disabled:opacity-50 transition-colors"
                      >
                        {transitioningStatus && (
                          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                        )}
                        Mark Repaid
                      </button>
                    )}
                    {lending.status === 'repaid' && (
                      <button
                        onClick={async () => {
                          if (!confirm('Clôturer définitivement cette offre ?')) return
                          setTransitioningStatus(true)
                          try {
                            const res = await fetch(`/api/admin/lending/products/${lending.lending_product_id}/transition`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ action: 'close' }),
                            })
                            const data = await res.json()
                            if (!res.ok) throw new Error(data.detail || 'Failed')
                            toastSuccess('Status → closed')
                            fetchLendingProductData()
                          } catch (err: any) {
                            toastError(err.message || 'Transition failed')
                          } finally {
                            setTransitioningStatus(false)
                          }
                        }}
                        disabled={transitioningStatus}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium rounded-md disabled:opacity-50 transition-colors"
                      >
                        {transitioningStatus && (
                          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                        )}
                        Close
                      </button>
                    )}
                  </div>
                </div>
              )
            })()}
          </div>

          {/* Images Section - Uniform Design */}
          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Images</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Cover Image - Portrait */}
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cover Image (Portrait)
                  </label>
                  <p className="text-xs text-gray-500">
                    For project cards in listings. Recommended: portrait format (2:3 ratio)
                  </p>
                </div>
                <MediaField
                  value={project.coverMediaId || undefined}
                  onChange={(mediaId) => {
                    setProject({ ...project, coverMediaId: mediaId || null })
                  }}
                  label=""
                  allowClear
                  preview
                />
                {project.coverMedia && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-md border border-gray-200">
                    <p className="text-xs text-gray-500 mb-2">Preview:</p>
                    <div className="w-32 h-48 border border-gray-300 rounded overflow-hidden bg-white">
                      <img
                        src={project.coverMedia.url}
                        alt={project.coverMedia.filename}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-2 truncate">{project.coverMedia.filename}</p>
                  </div>
                )}
              </div>

              {/* Hero Image - Panoramic */}
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Hero Image (Panoramic)
                  </label>
                  <p className="text-xs text-gray-500">
                    For project detail page hero section. Recommended: panoramic format (16:9 ratio)
                  </p>
                </div>
                <MediaField
                  value={project.heroMediaId || undefined}
                  onChange={(mediaId) => {
                    setProject({ ...project, heroMediaId: mediaId || null })
                  }}
                  label=""
                  allowClear
                  preview
                />
                {project.heroMedia && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-md border border-gray-200">
                    <p className="text-xs text-gray-500 mb-2">Preview:</p>
                    <div className="w-full h-32 border border-gray-300 rounded overflow-hidden bg-white">
                      <img
                        src={project.heroMedia.url}
                        alt={project.heroMedia.filename}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-2 truncate">{project.heroMedia.filename}</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* YouTube URL */}
          <div className="border-t border-gray-200 pt-6">
            <div className="mb-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                YouTube URL (optional)
              </label>
              <p className="text-xs text-gray-500">
                Add a YouTube video URL to display on the project detail page
              </p>
            </div>
            <input
              type="url"
              value={project.youtubeUrl || ''}
              onChange={(e) => setProject({ ...project, youtubeUrl: e.target.value || null })}
              placeholder="https://www.youtube.com/watch?v=..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 mb-3"
            />
            {project.youtubeUrl && (() => {
              // Extract YouTube video ID from URL
              const getYouTubeVideoId = (url: string): string | null => {
                const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/)
                return match ? match[1] : null
              }
              const videoId = getYouTubeVideoId(project.youtubeUrl)
              return videoId ? (
                <div className="p-3 bg-gray-50 rounded-md border border-gray-200">
                  <p className="text-xs text-gray-500 mb-2">Preview:</p>
                  <div className="aspect-video w-full max-w-2xl border border-gray-300 rounded overflow-hidden bg-black">
                    <iframe
                      src={`https://www.youtube.com/embed/${videoId}`}
                      title="YouTube video preview"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                      className="w-full h-full"
                    />
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-yellow-50 rounded-md border border-yellow-200">
                  <p className="text-xs text-yellow-800">Invalid YouTube URL. Please use format: https://www.youtube.com/watch?v=... or https://youtu.be/...</p>
                </div>
              )
            })()}
          </div>

          {/* Save Settings Button - Very Visible Blue */}
          <div className="border-t border-gray-200 pt-6">
            <button
              onClick={handleSaveSettings}
              disabled={saving}
              className="w-full md:w-auto px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-md shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {saving ? (
                <>
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Saving...
                </>
              ) : (
                'Save Settings'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Localized Content Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Localized Content</h2>
            <p className="text-sm text-gray-500 mt-1">Edit project content for different languages</p>
          </div>
          <div className="flex gap-2 items-center">
            <select
              value={selectedLocale}
              onChange={(e) => setSelectedLocale(e.target.value as Locale)}
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
            >
              {supportedLocales.map((locale) => (
                <option key={locale} value={locale}>
                  {locale.toUpperCase()}
                </option>
              ))}
            </select>
            {project && (() => {
              const currentI18n = project.i18n.find((i) => i.locale === selectedLocale)
              const translationStatus = currentI18n?.translationStatus
              return translationStatus ? (
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
                    {translationStatus === 'ORIGINAL'
                      ? 'ORIGINAL'
                      : translationStatus === 'MACHINE'
                      ? 'MACHINE'
                      : 'APPROVED'}
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
              ) : null
            })()}
            <button
              onClick={() => setShowTranslateModal(true)}
              disabled={saving || !project}
              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50"
            >
              Auto-translate
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Title *
            </label>
            <input
              type="text"
              value={i18nData.title}
              onChange={(e) => setI18nData({ ...i18nData, title: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Location
            </label>
            <p className="text-xs text-gray-500 mb-2">
              Localisation affichée verticalement sur la carte du projet (ex: "BALI", "JAPAN")
            </p>
            <input
              type="text"
              value={i18nData.location}
              onChange={(e) => setI18nData({ ...i18nData, location: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="BALI"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Short Description
            </label>
            <textarea
              value={i18nData.shortDescription}
              onChange={(e) => setI18nData({ ...i18nData, shortDescription: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Brief description for listings..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description (Markdown)
            </label>
            <textarea
              value={i18nData.description}
              onChange={(e) => setI18nData({ ...i18nData, description: e.target.value })}
              rows={10}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm"
              placeholder="Full project description in Markdown..."
            />
          </div>

          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <div className="flex items-center justify-between gap-3 mb-3">
              <div>
                <h4 className="text-sm font-semibold text-gray-800">Description links</h4>
                <p className="text-xs text-gray-500">
                  Ces liens sont affiches dans le module description de l&apos;app Flutter.
                </p>
              </div>
              <button
                type="button"
                onClick={addDescriptionLink}
                className="px-3 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                + Add link
              </button>
            </div>

            {descriptionLinks.length === 0 ? (
              <div className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-md p-3 bg-white">
                Aucun lien pour cette langue.
              </div>
            ) : (
              <div className="space-y-3">
                {descriptionLinks.map((link, index) => (
                  <div key={`description-link-${index}`} className="border border-gray-200 rounded-md p-3 bg-white">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-sm font-medium text-gray-700">Link {index + 1}</p>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => moveDescriptionLink(index, -1)}
                          disabled={index === 0}
                          className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          onClick={() => moveDescriptionLink(index, 1)}
                          disabled={index === descriptionLinks.length - 1}
                          className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          onClick={() => removeDescriptionLink(index)}
                          className="px-2 py-1 text-sm border border-red-300 text-red-700 rounded hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Link label</label>
                        <input
                          type="text"
                          value={link.label}
                          onChange={(e) => updateDescriptionLink(index, { label: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          placeholder="Read terms and conditions"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Hyperlink URL</label>
                        <input
                          type="url"
                          value={link.url}
                          onChange={(e) =>
                            updateDescriptionLink(index, {
                              url: e.target.value,
                              label: deriveLinkLabel(link.label, e.target.value),
                            })
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          placeholder="https://..."
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <div className="flex items-center justify-between gap-3 mb-3">
              <div>
                <h4 className="text-sm font-semibold text-gray-800">FAQ (articles Help liés au projet)</h4>
                <p className="text-xs text-gray-500">
                  Ajoutez des articles taggés sur ce projet. L&apos;ordre ci-dessous définit l&apos;ordre d&apos;apparition.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
              <div className="md:col-span-3">
                <label className="block text-xs font-medium text-gray-600 mb-1">Add a FAQ article</label>
                <select
                  value={selectedFaqArticleId}
                  onChange={(e) => setSelectedFaqArticleId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                >
                  <option value="">— Select tagged article —</option>
                  {faqArticleOptions
                    .filter((option) => !faqConfig.items.some((item) => item.articleId === option.articleId))
                    .map((option) => (
                      <option key={option.articleId} value={option.articleId}>
                        {option.question} ({option.collectionSlug}/{option.categorySlug}/{option.articleSlug})
                      </option>
                    ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={addFaqArticleRow}
                  disabled={!selectedFaqArticleId}
                  className="w-full px-3 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  + Add article
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Activate redirect link to project-tagged FAQ list in Flutter
                </label>
                <select
                  value={faqConfig.enableTagRedirect ? 'yes' : 'no'}
                  onChange={(e) =>
                    setFaqConfig((prev) => ({ ...prev, enableTagRedirect: e.target.value === 'yes' }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                >
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Redirect label (Flutter)</label>
                <input
                  type="text"
                  value={faqConfig.tagRedirectLabel}
                  onChange={(e) =>
                    setFaqConfig((prev) => ({ ...prev, tagRedirectLabel: e.target.value }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  placeholder="Voir toutes les FAQ de ce projet"
                />
              </div>
            </div>

            {faqConfig.items.length === 0 ? (
              <div className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-md p-3 bg-white">
                Aucun article FAQ sélectionné pour ce projet.
              </div>
            ) : (
              <div className="space-y-3">
                {faqConfig.items.map((item, index) => (
                  <div key={`faq-item-${item.articleId}-${index}`} className="border border-gray-200 rounded-md p-3 bg-white">
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <p className="text-sm font-medium text-gray-800">{item.question}</p>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => moveFaqArticleRow(index, -1)}
                          disabled={index === 0}
                          className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          onClick={() => moveFaqArticleRow(index, 1)}
                          disabled={index === faqConfig.items.length - 1}
                          className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          onClick={() => removeFaqArticleRow(index)}
                          className="px-2 py-1 text-sm border border-red-300 text-red-700 rounded hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500">
                      {item.collectionSlug}/{item.categorySlug}/{item.articleSlug}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="border-t border-gray-200 pt-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">SEO Metadata</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Meta Title
                </label>
                <input
                  type="text"
                  value={i18nData.metaTitle}
                  onChange={(e) => setI18nData({ ...i18nData, metaTitle: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Meta Description
                </label>
                <textarea
                  value={i18nData.metaDescription}
                  onChange={(e) => setI18nData({ ...i18nData, metaDescription: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Key Information (localized content) */}
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="text-lg font-medium text-gray-900">Key information</h3>
                <p className="text-xs text-gray-500 mt-1">
                  Localized by language. Choose a category from database, set right-side value, and optional info modal text.
                </p>
              </div>
              <button
                type="button"
                onClick={addKeyInformationRow}
                className="px-3 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                + Add row
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Module title (optional)
              </label>
              <input
                type="text"
                value={keyInformationConfig.title}
                onChange={(e) => setKeyInformationConfig((prev) => ({ ...prev, title: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Informations clés"
              />
            </div>

            {keyInformationConfig.rows.length === 0 ? (
              <div className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-md p-4">
                No rows yet for this locale. Click <strong>Add row</strong> to start.
              </div>
            ) : (
              <div className="space-y-4">
                {keyInformationConfig.rows.map((row, index) => (
                  <div key={`key-information-row-${index}`} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-sm font-semibold text-gray-700">Row {index + 1}</p>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => moveKeyInformationRow(index, -1)}
                          disabled={index === 0}
                          className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          onClick={() => moveKeyInformationRow(index, 1)}
                          disabled={index === keyInformationConfig.rows.length - 1}
                          className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          onClick={() => removeKeyInformationRow(index)}
                          className="px-2 py-1 text-sm border border-red-300 text-red-700 rounded hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Category (left title)</label>
                        <select
                          value={row.categoryKey}
                          onChange={(e) => updateKeyInformationCategory(index, e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        >
                          <option value="">— Select category —</option>
                          {keyInformationCategories.map((category) => (
                            <option key={category.id} value={category.key}>
                              {category.label} ({category.key})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Value (right side)</label>
                        <input
                          type="text"
                          value={row.value}
                          onChange={(e) => updateKeyInformationRow(index, { value: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          placeholder="11M €"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Info modal title (optional)</label>
                        <input
                          type="text"
                          value={row.infoTitle}
                          onChange={(e) => updateKeyInformationRow(index, { infoTitle: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          placeholder="Informations bonus"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Show "i" icon</label>
                        <select
                          value={row.showInfoIcon ? 'yes' : 'no'}
                          onChange={(e) => updateKeyInformationRow(index, { showInfoIcon: e.target.value === 'yes' })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        >
                          <option value="yes">Yes</option>
                          <option value="no">No</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Info modal content (optional)</label>
                      <textarea
                        value={row.infoContent}
                        onChange={(e) => updateKeyInformationRow(index, { infoContent: e.target.value })}
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        placeholder="Info details shown when user taps the i icon."
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* How It Works (localized content) */}
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="text-lg font-medium text-gray-900">How it works</h3>
                <p className="text-xs text-gray-500 mt-1">
                  Localized by language. Configure title, markdown content, and optional web links.
                </p>
              </div>
              <button
                type="button"
                onClick={addHowItWorksLink}
                className="px-3 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                + Add link
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Module title (optional)
              </label>
              <input
                type="text"
                value={howItWorksConfig.title}
                onChange={(e) => setHowItWorksConfig((prev) => ({ ...prev, title: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="How it works"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Content (Markdown)
              </label>
              <textarea
                value={howItWorksConfig.content}
                onChange={(e) => setHowItWorksConfig((prev) => ({ ...prev, content: e.target.value }))}
                rows={8}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm"
                placeholder="Describe how it works..."
              />
            </div>

            {howItWorksConfig.links.length === 0 ? (
              <div className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-md p-4">
                No links for this locale. Click <strong>Add link</strong> to add one.
              </div>
            ) : (
              <div className="space-y-4">
                {howItWorksConfig.links.map((link, index) => (
                  <div key={`howitworks-link-${index}`} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-sm font-semibold text-gray-700">Link {index + 1}</p>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => moveHowItWorksLink(index, -1)}
                          disabled={index === 0}
                          className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          onClick={() => moveHowItWorksLink(index, 1)}
                          disabled={index === howItWorksConfig.links.length - 1}
                          className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          onClick={() => removeHowItWorksLink(index)}
                          className="px-2 py-1 text-sm border border-red-300 text-red-700 rounded hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Link label</label>
                        <input
                          type="text"
                          value={link.label}
                          onChange={(e) => updateHowItWorksLink(index, { label: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          placeholder="Read Terms & Conditions"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Hyperlink URL</label>
                        <input
                          type="url"
                          value={link.url}
                          onChange={(e) => updateHowItWorksLink(index, { url: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          placeholder="https://..."
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Competitive Advantages (localized content) */}
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="text-lg font-medium text-gray-900">Competitive advantages</h3>
                <p className="text-xs text-gray-500 mt-1">
                  Localized by language. Add rows, order them, then save with this locale.
                </p>
              </div>
              <button
                type="button"
                onClick={addCompetitiveAdvantageRow}
                className="px-3 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                + Add row
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Module title (optional)
              </label>
              <input
                type="text"
                value={competitiveAdvantagesConfig.title}
                onChange={(e) =>
                  setCompetitiveAdvantagesConfig((prev) => ({ ...prev, title: e.target.value }))
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Why Dubai? Why now?"
              />
            </div>

            {competitiveAdvantagesConfig.rows.length === 0 ? (
              <div className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-md p-4">
                No rows yet for this locale. Click <strong>Add row</strong> to start.
              </div>
            ) : (
              <div className="space-y-4">
                {competitiveAdvantagesConfig.rows.map((row, index) => (
                  <div key={`competitive-row-${index}`} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-sm font-semibold text-gray-700">Row {index + 1}</p>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => moveCompetitiveAdvantageRow(index, -1)}
                          disabled={index === 0}
                          className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          onClick={() => moveCompetitiveAdvantageRow(index, 1)}
                          disabled={index === competitiveAdvantagesConfig.rows.length - 1}
                          className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          onClick={() => removeCompetitiveAdvantageRow(index)}
                          className="px-2 py-1 text-sm border border-red-300 text-red-700 rounded hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Icon</label>
                        <select
                          value={row.icon}
                          onChange={(e) =>
                            updateCompetitiveAdvantageRow(index, { icon: e.target.value })
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        >
                          {COMPETITIVE_ADVANTAGE_ICON_OPTIONS.map((iconOption) => (
                            <option key={iconOption.value} value={iconOption.value}>
                              {iconOption.label} ({iconOption.value})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Catégorie (couleur de fond)
                        </label>
                        <select
                          value={row.category ?? 'content'}
                          onChange={(e) =>
                            updateCompetitiveAdvantageRow(index, {
                              category: e.target.value as CompetitiveAdvantageRow['category'],
                            })
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        >
                          {COMPETITIVE_ADVANTAGE_CATEGORY_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Icon background color (hex)
                        </label>
                        <input
                          type="text"
                          value={row.iconBackgroundColor}
                          onChange={(e) =>
                            updateCompetitiveAdvantageRow(index, {
                              iconBackgroundColor: e.target.value,
                            })
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          placeholder="#1E88E5"
                        />
                      </div>
                    </div>

                    <div className="mb-3">
                      <label className="block text-xs font-medium text-gray-600 mb-1">Title</label>
                      <input
                        type="text"
                        value={row.title}
                        onChange={(e) =>
                          updateCompetitiveAdvantageRow(index, { title: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        placeholder="Row title"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Description
                      </label>
                      <textarea
                        value={row.description}
                        onChange={(e) =>
                          updateCompetitiveAdvantageRow(index, {
                            description: e.target.value,
                          })
                        }
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        placeholder="Row description"
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            <p className="mt-4 text-xs text-gray-500">
              Options pour la catégorie : content (blanc, comportement actuel) ; work (jaune clair #FEF9C3) ; note (bleu clair #DBEAFE) ; success (vert clair #D1FAE5) ; danger (rouge clair #FEE2E2). Une barre verticale colorée à gauche indique la catégorie pour les lignes non-content.
            </p>
          </div>

          {/* Save Content Button - Very Visible Blue */}
          <div className="border-t border-gray-200 pt-6">
            <button
              onClick={handleSaveI18n}
              disabled={saving}
              className="w-full md:w-auto px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-md shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {saving ? (
                <>
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Saving...
                </>
              ) : (
                'Save Content'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Portfolio Gallery Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Portfolio Gallery</h2>
            <p className="text-sm text-gray-500 mt-1">Manage images for the project portfolio section</p>
          </div>
          <div key={galleryPickerKey}>
            <MediaField
              value={undefined}
              onChange={(mediaId) => {
                if (mediaId) {
                  handleAddGalleryMedia(mediaId)
                }
              }}
              label=""
              allowClear={false}
              preview={false}
            />
          </div>
        </div>

        {project.gallery.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
            <p className="text-gray-500">No images in portfolio yet. Add images to create a portfolio gallery.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {project.gallery.map((item, index) => (
              <div key={item.id} className="flex items-center gap-4 p-4 border border-gray-200 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors">
                <div className="flex-shrink-0">
                  <img
                    src={item.media.url}
                    alt={item.media.filename}
                    className="w-20 h-20 object-cover rounded border border-gray-300"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {item.media.filename}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Position: {index + 1} of {project.gallery.length}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {index > 0 && (
                    <button
                      onClick={async () => {
                        const newOrder = [...project.gallery]
                        const temp = newOrder[index].order
                        newOrder[index].order = newOrder[index - 1].order
                        newOrder[index - 1].order = temp
                        
                        try {
                          const response = await fetch(`/api/admin/projects/${projectId}/gallery/reorder`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              orderedProjectMediaIds: newOrder.map((item) => item.id),
                            }),
                          })
                          if (response.ok) {
                            await fetchProject()
                          }
                        } catch (error: any) {
                          toastError(error.message || 'An error occurred')
                        }
                      }}
                      className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded transition-colors"
                      title="Move up"
                    >
                      ↑
                    </button>
                  )}
                  {index < project.gallery.length - 1 && (
                    <button
                      onClick={async () => {
                        const newOrder = [...project.gallery]
                        const temp = newOrder[index].order
                        newOrder[index].order = newOrder[index + 1].order
                        newOrder[index + 1].order = temp
                        
                        try {
                          const response = await fetch(`/api/admin/projects/${projectId}/gallery/reorder`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              orderedProjectMediaIds: newOrder.map((item) => item.id),
                            }),
                          })
                          if (response.ok) {
                            await fetchProject()
                          }
                        } catch (error: any) {
                          toastError(error.message || 'An error occurred')
                        }
                      }}
                      className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded transition-colors"
                      title="Move down"
                    >
                      ↓
                    </button>
                  )}
                  <button
                    onClick={() => handleRemoveGalleryMedia(item.id)}
                    className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Unpublish Confirmation Dialog */}
      <AlertDialog open={showUnpublishDialog} onOpenChange={setShowUnpublishDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Set Project to Draft</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to set this project back to draft status?
              <br /><br />
              <strong>What will happen:</strong>
              <ul className="list-disc list-inside mt-2 space-y-1 text-sm">
                <li>The project will no longer be visible on the public website</li>
                <li>It will be removed from public project listings</li>
                <li>You can continue editing and republish it later</li>
                <li>All your content and media will be preserved</li>
              </ul>
              <br />
              This action can be reversed by publishing the project again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleUnpublish}
              className="bg-orange-600 hover:bg-orange-700 text-white"
            >
              Set to Draft
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Project</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this project? This action cannot be undone.
              <br /><br />
              <strong>What will happen:</strong>
              <ul className="list-disc list-inside mt-2 space-y-1 text-sm">
                <li>The project will be permanently deleted from the database</li>
                <li>All project content (titles, descriptions, translations) will be lost</li>
                <li>The project will be removed from all public pages and listings</li>
                <li>Media files (images, videos) will NOT be deleted from storage</li>
                <li>This action is irreversible</li>
              </ul>
              <br />
              <strong className="text-red-600">Warning: This action cannot be reversed!</strong>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Delete Project
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Translate Modal */}
      {project && (
        <TranslateModal
          open={showTranslateModal}
          onOpenChange={setShowTranslateModal}
          sourceLocale={selectedLocale}
          hasGlossary={hasGlossary}
          onTranslate={async ({ sourceLocale, targetLocales, mode }) => {
            const response = await fetch('/api/admin/translate/project', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                projectId: project.id,
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
            // Reload project to show new translations
            await fetchProject()
            return data
          }}
        />
      )}
    </div>
  )
}
