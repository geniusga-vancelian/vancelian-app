'use client'

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  Plus,
  Save,
  Trash2,
  ArrowUp,
  ArrowDown,
  Package,
  ChevronDown,
  ChevronRight,
  UploadCloud,
  Landmark,
  Video,
} from 'lucide-react'

import { buildPackagedPutBodyFromDraft } from '@/lib/admin/packagedProductSchemas'
import type { LocaleCompletenessLevel } from '@/lib/admin/pageLocaleCompleteness'
import { AdminEditingLocaleBar } from '@/components/admin/AdminEditingLocaleBar'
import { useAdminEditingLocale } from '@/components/admin/AdminEditingLocaleContext'
import { defaultLocale, isValidLocale, type Locale } from '@/config/locales'
import { type VaultLocaleLayerInfo } from '@/lib/admin/vaultLocaleSectionStatus'
import { toastError, toastSuccess, toastWarning } from '@/lib/admin/toast'
import { isValidSlug, slugify } from '@/lib/utils/slugify'
import { PackagedEngineLendingSection } from '@/components/admin/PackagedEngineLendingSection'
import {
  buildProductRegistryDraft,
  PackagedProductSettingsPanel,
  type ProductRegistryDraft,
} from '@/components/admin/PackagedProductSettingsPanel'
import { MediaField } from '@/components/admin/MediaField'
import { VaultDocumentsListModuleEditor } from '@/components/admin/VaultDocumentsListModuleEditor'
import { VaultLocalisationModuleEditor } from '@/components/admin/VaultLocalisationModuleEditor'
import { VaultVirtualVisualizationModuleEditor } from '@/components/admin/VaultVirtualVisualizationModuleEditor'
import { VaultMediaCarouselModuleEditor } from '@/components/admin/VaultMediaCarouselModuleEditor'
import { VaultVideoBlockArticleModuleEditor } from '@/components/admin/VaultVideoBlockArticleModuleEditor'
import { PagePreviewPanel } from '@/components/admin/PagePreviewPanel'
import { AddVaultModuleModal } from '@/components/admin/AddVaultModuleModal'
import { VaultModulesSection } from '@/components/admin/VaultModulesSection'
import {
  getVaultModuleDefaultContent,
  getVaultModuleDefinition,
  getVaultModuleLabel,
} from '@/lib/admin/vaultModuleCatalog'
import { CollapsibleAdminSection } from '@/components/admin/CollapsibleAdminSection'
import { VAULT_BUILDER_IFRAME_PREVIEW_QUERY } from '@/lib/cms/vaultBuilderPreviewConstants'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

/**
 * Attempt to fix JSON strings that contain raw newlines inside quoted values.
 * Replaces literal newlines within "..." sequences with \\n so JSON.parse succeeds.
 */
function sanitizeJsonNewlines(raw: string): string {
  return raw.replace(/"(?:[^"\\]|\\.)*"/g, (match) =>
    match.replace(/\n/g, '\\n').replace(/\r/g, '\\r').replace(/\t/g, '\\t'),
  )
}

type TemplateKey =
  | 'PageSimpleNavBarTopTitlePageContent'
  | 'ModaleFullHeightPage'
  | 'DashboardScrollTemplate'

type RedirectType = 'none' | 'back' | 'close' | 'internal' | 'external'
type LeftIconType = 'none' | 'back' | 'close'
type RightIconType = 'none' | 'favorite' | 'share' | 'notifications'

interface LandingModule {
  id: string
  type: string
  enabled: boolean
  content: Record<string, unknown>
}

interface LandingConfig {
  templateKey: TemplateKey
  investmentTypeSlug?: string
  sortOrder?: number
  headerMediaId?: string | null
  navbar: {
    leftIconType: LeftIconType
    leftRedirectType: Exclude<RedirectType, 'none'>
    leftTarget?: string
    rightAction: {
      icon: RightIconType
      redirectType: RedirectType
      target?: string
    }
  }
  pageTitle: {
    enabled: boolean
    text: string
  }
  fixedBottomCta: {
    enabled: boolean
    label: string
    redirectType: RedirectType
    target?: string
  }
  modules: LandingModule[]
}

interface InvestmentType {
  id: string
  slug: string
  label: string
}

interface VaultRow {
  id: string
  slug: string
  title: string | null
  description: string | null
  urlPath: string
  investmentTypeSlug: string | null
  sortOrder: number
  configSummary: {
    templateKey: string | null
    modulesCount: number
  }
}

interface PortfolioProduct {
  id: string
  product_code: string
  name: string
  description?: string | null
  product_type: string
  allocations: Array<{ asset_symbol: string; target_weight: string }>
  available_rebalance_frequencies: string[]
  /** Présent quand la liste vient du Bundle Engine admin — visibilité catalogue public. */
  is_public?: boolean
}

interface AdminPackagedProductView {
  id: string
  slug: string
  pageId: string
  productType: string
  commercialStatus: string
  visibility: string
  featuredRank: number | null
  categorySlug: string | null
  tags: string[]
  engineType: string | null
  engineReferenceId: string | null
  lendingEngineLinked: boolean
  updatedAt: string
  publishedAt: string | null
}

interface VaultDetails {
  page: {
    id: string
    slug: string
    title: string | null
    description: string | null
    urlPath: string
  }
  config: LandingConfig
  /** Snapshot publié pour la langue éditée (lecture / comparaison). */
  publishedConfig?: LandingConfig | null
  packagedProduct?: AdminPackagedProductView | null
  editingLocale?: Locale
  localeCompleteness?: Record<Locale, LocaleCompletenessLevel>
  /** Brouillon / publié par langue (section vault). */
  localeVaultLayers?: Record<Locale, VaultLocaleLayerInfo>
}

const DEFAULT_CONFIG: LandingConfig = {
  templateKey: 'PageSimpleNavBarTopTitlePageContent',
  navbar: {
    leftIconType: 'back',
    leftRedirectType: 'back',
    leftTarget: '',
    rightAction: {
      icon: 'favorite',
      redirectType: 'none',
      target: '',
    },
  },
  pageTitle: {
    enabled: true,
    text: 'Titre de page',
  },
  fixedBottomCta: {
    enabled: false,
    label: 'Parrainer une entreprise',
    redirectType: 'none',
    target: '',
  },
  modules: [],
  investmentTypeSlug: undefined,
  sortOrder: 999,
  headerMediaId: undefined,
}

const withConfigDefaults = (config: Partial<LandingConfig> | null | undefined): LandingConfig => ({
  ...DEFAULT_CONFIG,
  ...(config ?? {}),
  navbar: {
    ...DEFAULT_CONFIG.navbar,
    ...(config?.navbar ?? {}),
    rightAction: {
      ...DEFAULT_CONFIG.navbar.rightAction,
      ...(config?.navbar?.rightAction ?? {}),
    },
  },
  pageTitle: {
    ...DEFAULT_CONFIG.pageTitle,
    ...(config?.pageTitle ?? {}),
  },
  fixedBottomCta: {
    ...DEFAULT_CONFIG.fixedBottomCta,
    ...(config?.fixedBottomCta ?? {}),
  },
  modules: Array.isArray(config?.modules) ? (config.modules as LandingModule[]) : [],
  headerMediaId: config?.headerMediaId ?? undefined,
  investmentTypeSlug: config?.investmentTypeSlug ?? undefined,
  sortOrder: config?.sortOrder ?? 999,
})

/** Contenu TitlePage — champs promo lus par l’app (promoVideoUrl / promoVideoUrls). */
type TitlePageJson = Record<string, unknown>

function readPromoVideoFromVaultModules(modules: LandingModule[]): { url: string; mediaId: string | null } {
  const m = modules.find((x) => x.type === 'TitlePage')
  if (!m) return { url: '', mediaId: null }
  const c = (m.content ?? {}) as TitlePageJson
  const multi = c.promoVideoUrls
  let url = ''
  if (Array.isArray(multi) && multi.length > 0) {
    const first = String(multi[0] ?? '').trim()
    if (first) url = first
  }
  if (!url) url = String(c.promoVideoUrl ?? '').trim()
  const mid = c.promoVideoMediaId
  const mediaId = typeof mid === 'string' && mid.length > 0 ? mid : null
  return { url, mediaId }
}

/** Met à jour (ou crée) le module TitlePage avec l’URL vidéo promo — utilisé par l’app mobile (bouton lecture). */
function upsertTitlePagePromoVideo(
  modules: LandingModule[],
  patch: { url: string; mediaId: string | null },
): LandingModule[] {
  const catalogItem = getVaultModuleDefinition('TitlePage')
  if (!catalogItem) return modules
  const baseDefault = structuredClone(catalogItem.defaultContent) as TitlePageJson

  const idx = modules.findIndex((x) => x.type === 'TitlePage')
  const apply = (content: TitlePageJson) => {
    const u = patch.url.trim()
    if (u) {
      content.promoVideoUrl = u
      delete content.promoVideoUrls
      if (patch.mediaId) content.promoVideoMediaId = patch.mediaId
      else delete content.promoVideoMediaId
    } else {
      delete content.promoVideoUrl
      delete content.promoVideoUrls
      delete content.promoVideoMediaId
    }
  }

  if (idx < 0) {
    const content = { ...baseDefault }
    apply(content)
    return [{ id: crypto.randomUUID(), type: 'TitlePage', enabled: true, content }, ...modules]
  }

  return modules.map((mod, i) => {
    if (i !== idx) return mod
    const content = { ...((mod.content ?? {}) as TitlePageJson) }
    apply(content)
    return { ...mod, content }
  })
}

const PRODUCT_REGISTRY_VISIBILITY_SUMMARY: Record<string, string> = {
  PUBLIC: 'Public',
  PRIVATE: 'Privé',
  HIDDEN: 'Masqué',
}

function AdminVaultBuilderPageInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const slugFromQuery = searchParams?.get('slug') ?? null
  const eoWorkspace = searchParams?.get('eo') === '1'
  const { locale: editingLocale, setLocale: setEditingLocale } = useAdminEditingLocale()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [publishVaultBusy, setPublishVaultBusy] = useState(false)
  const [packagedPublishBusy, setPackagedPublishBusy] = useState(false)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [vaults, setVaults] = useState<VaultRow[]>([])
  const [investmentTypes, setInvestmentTypes] = useState<InvestmentType[]>([])
  const [newInvestmentTypeSlug, setNewInvestmentTypeSlug] = useState<string>('')
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [reordering, setReordering] = useState<string | null>(null)
  const [details, setDetails] = useState<VaultDetails | null>(null)
  const [productDraft, setProductDraft] = useState<ProductRegistryDraft | null>(null)
  const [newSlug, setNewSlug] = useState('')
  const [newTitle, setNewTitle] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [createError, setCreateError] = useState<string | null>(null)
  const [portfolioProducts, setPortfolioProducts] = useState<PortfolioProduct[]>([])
  const [portfolioProductsExpanded, setPortfolioProductsExpanded] = useState(true)
  const [selectedProductCode, setSelectedProductCode] = useState<string | null>(null)
  const [productHeaderMediaId, setProductHeaderMediaId] = useState<string | null>(null)
  const [productDetailMediaId, setProductDetailMediaId] = useState<string | null>(null)
  const [productModules, setProductModules] = useState<LandingModule[]>([])
  const [productConfigSaving, setProductConfigSaving] = useState(false)
  const [productSortOrder, setProductSortOrder] = useState<number>(999)
  const [productSortOrders, setProductSortOrders] = useState<Record<string, number>>({})
  const [productIsPublished, setProductIsPublished] = useState(false)
  const [productPublishStates, setProductPublishStates] = useState<Record<string, boolean>>({})
  const [vaultAddModuleOpen, setVaultAddModuleOpen] = useState(false)
  const [productAddModuleOpen, setProductAddModuleOpen] = useState(false)
  const [previewLocale, setPreviewLocale] = useState<Locale>(defaultLocale)
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'mobile'>('desktop')
  const [vaultPreviewReloadEpoch, setVaultPreviewReloadEpoch] = useState(0)

  // ── Create Bundle state ──
  const [showCreateBundle, setShowCreateBundle] = useState(false)
  const [creatingBundle, setCreatingBundle] = useState(false)
  const [bundleName, setBundleName] = useState('')
  const [bundleCode, setBundleCode] = useState('')
  const [bundleDescription, setBundleDescription] = useState('')
  const [bundleRisk, setBundleRisk] = useState<'low' | 'moderate' | 'high' | 'very_high'>('high')
  const [availableInstruments, setAvailableInstruments] = useState<
    Array<{ id: string; code: string; name: string; asset_symbol?: string }>
  >([])
  const [bundleAllocations, setBundleAllocations] = useState<
    Array<{ instrumentId: string; instrumentCode: string; assetSymbol: string; weight: number }>
  >([])
  const [loadingInstruments, setLoadingInstruments] = useState(false)

  const normalizedNewSlug = useMemo(() => slugify(newSlug.trim()), [newSlug])

  const vaultsByCategoryEntries = useMemo(() => {
    const groups = new Map<string, VaultRow[]>()
    const sorted = [...vaults].sort((a, b) => {
      if (a.sortOrder !== b.sortOrder) return a.sortOrder - b.sortOrder
      return (a.slug ?? '').localeCompare(b.slug ?? '')
    })
    for (const v of sorted) {
      const key = v.investmentTypeSlug ?? '__none__'
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key)!.push(v)
    }
    const orderedKeys: string[] = []
    for (const t of investmentTypes) {
      if (groups.has(t.slug)) orderedKeys.push(t.slug)
    }
    if (groups.has('__none__')) orderedKeys.push('__none__')
    return orderedKeys.map((key) => [key, groups.get(key) ?? []] as [string, VaultRow[]])
  }, [vaults, investmentTypes])

  const categoryLabels = useMemo(() => {
    const map = new Map<string, string>()
    map.set('__none__', 'Sans catégorie')
    for (const t of investmentTypes) {
      map.set(t.slug, t.label)
    }
    return map
  }, [investmentTypes])

  useEffect(() => {
    const q = searchParams?.get('editingLocale')
    if (q && isValidLocale(q)) setEditingLocale(q)
  }, [searchParams, setEditingLocale])

  useEffect(() => {
    setPreviewLocale(editingLocale)
  }, [editingLocale])

  const fetchVaultPayload = useCallback(
    async (
      slug: string,
      localeOverride?: Locale,
    ): Promise<{ ok: true; data: VaultDetails } | { ok: false }> => {
      const normalizedSlug = slug?.trim().replace(/\/+$/, '') || ''
      if (!normalizedSlug) return { ok: false }
      const loc = localeOverride ?? editingLocale
      const res = await fetch(
        `/api/admin/vaults/${encodeURIComponent(normalizedSlug)}?locale=${loc}`,
        { credentials: 'include' },
      )
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        const message = body?.error || body?.detail || `Erreur ${res.status}`
        toastError(`Détails de la page : ${message}`)
        return { ok: false }
      }
      const data = (await res.json()) as VaultDetails
      return { ok: true, data }
    },
    [editingLocale],
  )

  const reloadVaultDetails = useCallback(
    async (slug: string, localeOverride?: Locale) => {
      const result = await fetchVaultPayload(slug, localeOverride)
      if (!result.ok) return
      setDetails({
        ...result.data,
        config: withConfigDefaults(result.data.config),
        publishedConfig:
          result.data.publishedConfig != null
            ? withConfigDefaults(result.data.publishedConfig)
            : null,
      })
    },
    [fetchVaultPayload],
  )

  useEffect(() => {
    if (!selectedSlug) {
      setDetails(null)
      return
    }
    let cancelled = false
    ;(async () => {
      const result = await fetchVaultPayload(selectedSlug)
      if (cancelled) return
      if (!result.ok) {
        setDetails(null)
        setSelectedSlug(null)
        return
      }
      setDetails({
        ...result.data,
        config: withConfigDefaults(result.data.config),
        publishedConfig:
          result.data.publishedConfig != null
            ? withConfigDefaults(result.data.publishedConfig)
            : null,
      })
    })()
    return () => {
      cancelled = true
    }
  }, [selectedSlug, editingLocale, fetchVaultPayload])

  useEffect(() => {
    if (!selectedSlug) return
    const params = new URLSearchParams()
    params.set('slug', selectedSlug)
    params.set('editingLocale', editingLocale)
    if (eoWorkspace) params.set('eo', '1')
    router.replace(`/admin/vault-builder?${params.toString()}`, { scroll: false })
  }, [selectedSlug, editingLocale, eoWorkspace, router])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const auth = await fetch('/api/admin/me', { credentials: 'include' })
        const authJson = await auth.json()
        if (!authJson?.user) {
          router.push('/admin/login')
          return
        }
        // Ne pas utiliser Promise.all : si refreshVaults() échoue, les produits portfolio
        // ne se chargeaient jamais (liste bundles vide alors que l’API produits est OK).
        const settled = await Promise.allSettled([
          refreshVaults(mounted, slugFromQuery),
          fetch('/api/admin/investment-types', { credentials: 'include' }),
          fetch('/api/admin/portfolio-engine/products', { credentials: 'include' }),
        ])

        const typesRes = settled[1].status === 'fulfilled' ? settled[1].value : null
        const productsRes = settled[2].status === 'fulfilled' ? settled[2].value : null

        if (settled[0].status === 'rejected') {
          console.warn('[vault-builder] refreshVaults failed', settled[0].reason)
        }

        if (typesRes?.ok && mounted) {
          const typesData = await typesRes.json()
          setInvestmentTypes(typesData.investmentTypes ?? [])
        }
        if (productsRes?.ok && mounted) {
          const productsData = await productsRes.json()
          const items = Array.isArray(productsData.items) ? productsData.items : []
          if (process.env.NODE_ENV === 'development') {
            const raw = productsData as Record<string, unknown>
            console.debug('[vault-builder] /api/admin/portfolio-engine/products', {
              httpStatus: productsRes.status,
              totalField: raw.total,
              topLevelKeys: Object.keys(raw),
              itemsIsArray: Array.isArray(productsData.items),
              itemCount: items.length,
              productCodes: items.map((p: PortfolioProduct) => p.product_code),
              cryptoBundlesInUi: items.filter((p: PortfolioProduct) => p.product_type === 'crypto_bundle')
                .length,
            })
          }
          setPortfolioProducts(items)
          loadAllSortOrders(items)
        } else if (productsRes && !productsRes.ok && mounted) {
          const errBody = await productsRes.json().catch(() => ({}))
          const msg =
            typeof errBody.error === 'string'
              ? errBody.error
              : `Erreur ${productsRes.status} lors du chargement des produits portfolio.`
          toastError(msg)
        } else if (!productsRes && mounted) {
          toastError('Impossible de contacter le serveur pour les produits portfolio.')
        }
      } catch {
        toastError('Impossible de charger le Vault Builder.')
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [router, slugFromQuery])

  const refreshVaults = async (mounted = true, preferredSlug?: string | null) => {
    const res = await fetch('/api/admin/vaults', { credentials: 'include' })
    if (!res.ok) {
      throw new Error('Failed to fetch vaults')
    }
    const payload = await res.json()
    const rows = (payload.vaults ?? []) as VaultRow[]
    if (!mounted) return
    setVaults(rows)
    const nextSlug =
      preferredSlug && rows.some((r) => r.slug === preferredSlug)
        ? preferredSlug
        : selectedSlug && rows.some((r) => r.slug === selectedSlug)
          ? selectedSlug
          : rows[0]?.slug ?? null
    if (nextSlug) {
      if (mounted) setSelectedSlug(nextSlug)
    } else {
      if (mounted) {
        setDetails(null)
        setSelectedSlug(null)
      }
    }
  }

  const packagedSyncKey = details?.packagedProduct
    ? `${details.packagedProduct.id}:${details.packagedProduct.updatedAt}`
    : 'none'

  useEffect(() => {
    if (!details) {
      setProductDraft(null)
      return
    }
    setProductDraft(
      buildProductRegistryDraft(details.page, details.packagedProduct ?? null)
    )
  }, [details?.page.id, packagedSyncKey])

  const handleCreatePage = async () => {
    const slug = normalizedNewSlug
    if (!slug) {
      setCreateError('Le slug est requis.')
      toastError('Le slug est requis.')
      return
    }
    if (!isValidSlug(slug)) {
      setCreateError('Slug invalide. Utilise seulement lettres minuscules, chiffres et tirets.')
      toastError('Slug invalide.')
      return
    }
    setCreateError(null)
    setCreating(true)
    try {
      const res = await fetch('/api/admin/vaults', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          slug,
          title: newTitle.trim() || undefined,
          description: newDescription.trim() || undefined,
          investmentTypeSlug: newInvestmentTypeSlug || undefined,
          config: {
            ...DEFAULT_CONFIG,
            investmentTypeSlug: newInvestmentTypeSlug || undefined,
            sortOrder: 0,
          },
        }),
      })
      const payload = await res.json()
      if (!res.ok) {
        const issues = Array.isArray(payload.issues)
          ? payload.issues.map((i: any) => i?.message).filter(Boolean).join(', ')
          : ''
        throw new Error(issues || payload.error || 'Création impossible')
      }
      toastSuccess('Vault créé.')
      setNewSlug('')
      setNewTitle('')
      setNewDescription('')
      setNewInvestmentTypeSlug('')
      await refreshVaults(true, payload.vault?.slug ?? null)
    } catch (e: any) {
      setCreateError(e?.message || 'Création impossible')
      toastError(e?.message || 'Création impossible')
    } finally {
      setCreating(false)
    }
  }

  const handleDeletePage = async () => {
    if (!selectedSlug) return
    if (!window.confirm(`Supprimer le vault "${selectedSlug}" ?`)) return
    setDeleting(true)
    try {
      const res = await fetch(`/api/admin/vaults/${selectedSlug}`, {
        method: 'DELETE',
        credentials: 'include',
      })
      const payload = await res.json()
      if (!res.ok) {
        throw new Error(payload.error || 'Suppression impossible')
      }
      toastSuccess('Vault supprimé.')
      setSelectedSlug(null)
      setDetails(null)
      await refreshVaults()
    } catch (e: any) {
      toastError(e?.message || 'Suppression impossible')
    } finally {
      setDeleting(false)
    }
  }

  const updateDetails = (updater: (prev: VaultDetails) => VaultDetails) => {
    setDetails((prev) => (prev ? updater(prev) : prev))
  }

  const addVaultModuleOfType = (type: string) => {
    if (!details) return
    if (!getVaultModuleDefinition(type)) {
      toastError(`Type de module inconnu : ${type}`)
      return
    }
    const content = getVaultModuleDefaultContent(type)
    updateDetails((prev) => ({
      ...prev,
      config: {
        ...prev.config,
        modules: [
          ...prev.config.modules,
          {
            id: crypto.randomUUID(),
            type,
            enabled: true,
            content,
          },
        ],
      },
    }))
    toastSuccess(`Module « ${getVaultModuleLabel(type)} » ajouté.`)
  }

  const reorderDetailModulesByIds = (orderedIds: string[]) => {
    if (!details) return
    updateDetails((prev) => {
      if (!prev) return prev
      const map = new Map(prev.config.modules.map((m) => [m.id, m]))
      const next = orderedIds.map((id) => map.get(id)).filter(Boolean) as LandingModule[]
      return { ...prev, config: { ...prev.config, modules: next } }
    })
  }

  const handleUpdateModuleContent = (moduleId: string, raw: string) => {
    if (!details) return
    try {
      const parsed = JSON.parse(sanitizeJsonNewlines(raw)) as Record<string, unknown>
      updateDetails((prev) => ({
        ...prev,
        config: {
          ...prev.config,
          modules: prev.config.modules.map((m) =>
            m.id === moduleId ? { ...m, content: parsed } : m
          ),
        },
      }))
    } catch {
      toastError('JSON invalide — vérifiez la syntaxe (guillemets, virgules, accolades).')
    }
  }

  const handlePatchModuleContentObject = (moduleId: string, patch: Record<string, unknown>) => {
    if (!details) return
    updateDetails((prev) => ({
      ...prev,
      config: {
        ...prev.config,
        modules: prev.config.modules.map((m) =>
          m.id === moduleId ? { ...m, content: { ...m.content, ...patch } } : m
        ),
      },
    }))
  }

  const removeModule = (moduleId: string) => {
    if (!details) return
    updateDetails((prev) => ({
      ...prev,
      config: {
        ...prev.config,
        modules: prev.config.modules.filter((m) => m.id !== moduleId),
      },
    }))
  }

  const handleReorder = async (slug: string, direction: 'up' | 'down') => {
    setReordering(slug)
    try {
      const res = await fetch('/api/admin/vault-reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ slug, direction }),
      })
      const payload = await res.json()
      if (!res.ok) {
        const msg = payload.detail ? `${payload.error}: ${payload.detail}` : payload.error
        throw new Error(msg || 'Réordonnancement impossible')
      }
      toastSuccess('Ordre mis à jour.')
      await refreshVaults()
    } catch (e: any) {
      toastError(e?.message || 'Réordonnancement impossible')
    } finally {
      setReordering(null)
    }
  }

  const handleSave = async () => {
    if (!details) return
    setSaving(true)
    try {
      const res = await fetch(`/api/admin/vaults/${details.page.slug}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          locale: editingLocale,
          title: details.page.title ?? '',
          description: '',
          config: details.config,
        }),
      })
      const payload = await res.json()
      if (!res.ok) {
        const issues = Array.isArray(payload.issues)
          ? payload.issues.map((i: any) => i?.message).filter(Boolean).join(', ')
          : ''
        throw new Error(issues || payload.error || 'Sauvegarde impossible')
      }

      setVaultPreviewReloadEpoch((n) => n + 1)
      updateDetails((prev) => ({
        ...prev,
        page: { ...prev.page, description: '' },
      }))

      if (!productDraft) {
        toastSuccess('Brouillon vault enregistré.')
        await refreshVaults()
        return
      }

      let putBody
      try {
        putBody = buildPackagedPutBodyFromDraft(productDraft)
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'Données produit packagé invalides'
        toastError(msg)
        toastWarning('Brouillon vault enregistré, mais pas le registre produit packagé.')
        await refreshVaults()
        return
      }

      const ppRes = await fetch(`/api/admin/packaged-products/by-page/${details.page.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(putBody),
      })
      const ppPayload = await ppRes.json().catch(() => ({}))
      if (!ppRes.ok) {
        const errMsg =
          typeof ppPayload?.error === 'string'
            ? ppPayload.error
            : `Erreur produit packagé (${ppRes.status})`
        toastError(errMsg)
        toastWarning('Brouillon vault enregistré, mais pas le registre produit packagé.')
        await refreshVaults()
        return
      }

      toastSuccess('Brouillon vault et registre produit enregistrés.')
      await refreshVaults()
    } catch (e: any) {
      toastError(e?.message || 'Sauvegarde impossible')
    } finally {
      setSaving(false)
    }
  }

  /** Publier / Dépublier le registre (EO) — même logique que les bundles Portfolio Engine. */
  const handleToggleExclusiveOfferCatalogPublish = async () => {
    if (!details || !productDraft || !details.packagedProduct || !productDraft.enabled) return
    if (productDraft.productType !== 'EXCLUSIVE_OFFER') return

    const cs = productDraft.commercialStatus
    const nextStatus = cs === 'PUBLISHED' ? 'DRAFT' : 'PUBLISHED'

    let putBody
    try {
      putBody = buildPackagedPutBodyFromDraft({
        ...productDraft,
        commercialStatus: nextStatus,
      })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Données produit packagé invalides'
      toastError(msg)
      return
    }

    setPackagedPublishBusy(true)
    try {
      const ppRes = await fetch(`/api/admin/packaged-products/by-page/${details.page.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(putBody),
      })
      const ppPayload = await ppRes.json().catch(() => ({}))
      if (!ppRes.ok) {
        const errMsg =
          typeof ppPayload?.error === 'string'
            ? ppPayload.error
            : `Erreur registre (${ppRes.status})`
        toastError(errMsg)
        return
      }
      setProductDraft((prev) => (prev ? { ...prev, commercialStatus: nextStatus } : prev))
      toastSuccess(
        nextStatus === 'PUBLISHED'
          ? 'Offre exclusive publiée (catalogue / app mobile).'
          : 'Offre repassée en brouillon.',
      )
      await reloadVaultDetails(details.page.slug)
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Mise à jour impossible')
    } finally {
      setPackagedPublishBusy(false)
    }
  }

  const activeVaultLayer = useMemo(
    () => details?.localeVaultLayers?.[editingLocale],
    [details?.localeVaultLayers, editingLocale],
  )

  const canPublishVaultLocale = useMemo(() => {
    if (!activeVaultLayer) return false
    return (
      activeVaultLayer.kind === 'draft_only' || activeVaultLayer.kind === 'draft_and_published'
    )
  }, [activeVaultLayer])

  const vaultLendingSectionSummary = useMemo(() => {
    if (!details?.packagedProduct) return 'aucun produit packagé'
    return details.packagedProduct.lendingEngineLinked ? 'moteur associé' : 'moteur non associé'
  }, [details?.packagedProduct])

  const promoVideoSectionSummary = useMemo(() => {
    if (!details) return ''
    const { url, mediaId } = readPromoVideoFromVaultModules(details.config.modules)
    const u = url.trim()
    if (u) return u
    if (mediaId) return 'Vidéo (médiathèque)'
    return 'Aucune'
  }, [details])

  const productRegistrySectionSummary = useMemo(() => {
    if (!productDraft) return ''
    if (!productDraft.enabled) return 'Registre désactivé'
    const vis = PRODUCT_REGISTRY_VISIBILITY_SUMMARY[productDraft.visibility] ?? productDraft.visibility
    const rawTags = productDraft.tagsText
      .split(/[,\n\r]+/)
      .map((s) => s.trim())
      .filter(Boolean)
    const tagsHint =
      rawTags.length === 0
        ? 'sans tags'
        : rawTags.length <= 2
          ? rawTags.join(', ')
          : `${rawTags.slice(0, 2).join(', ')} +${rawTags.length - 2}`
    return `${productDraft.slug} · ${vis} · ${tagsHint}`
  }, [productDraft])

  const handlePublishVaultLocale = async () => {
    if (!details?.page.slug) return
    if (!canPublishVaultLocale) {
      toastWarning('Enregistrez d’abord un brouillon pour cette langue.')
      return
    }
    if (
      !window.confirm(
        `Publier le contenu vault (modules) pour ${editingLocale.toUpperCase()} ?\n\n` +
          'Le brouillon actuel remplacera la version publiée pour cette langue uniquement. ' +
          'Les autres langues ne sont pas modifiées.\n\n' +
          'Rappel : le nom d’offre (admin) est enregistré à chaque « Enregistrer (brouillon) » ; seul le corps du vault (modules) suit ce bouton « Publier ».',
      )
    ) {
      return
    }
    setPublishVaultBusy(true)
    try {
      const res = await fetch(
        `/api/admin/vaults/${encodeURIComponent(details.page.slug)}/publish-locale`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ locale: editingLocale }),
        },
      )
      const payload = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(
          typeof payload.error === 'string' ? payload.error : 'Publication impossible',
        )
      }
      toastSuccess(
        `Langue ${editingLocale.toUpperCase()} : version publiée du vault (modules) mise à jour.`,
      )
      setVaultPreviewReloadEpoch((n) => n + 1)
      await reloadVaultDetails(details.page.slug)
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Publication impossible')
    } finally {
      setPublishVaultBusy(false)
    }
  }

  const ensureRequiredProductModules = (
    modules: LandingModule[],
    product?: PortfolioProduct,
  ): LandingModule[] => {
    let result = [...modules]
    if (!result.some((m) => m.type === 'TitlePage')) {
      const titleDef = getVaultModuleDefinition('TitlePage')
      if (!titleDef) return result
      result = [
        {
          id: crypto.randomUUID(),
          type: 'TitlePage',
          enabled: true,
          content: structuredClone(titleDef.defaultContent),
        },
        ...result,
      ]
    }
    if (!result.some((m) => m.type === 'AllocationModule')) {
      const allocs = product?.allocations ?? []
      const slices = allocs.map((a, i) => {
        const greys = ['#374151', '#6B7280', '#9CA3AF', '#D1D5DB', '#E5E7EB', '#CBD5E1']
        const weight = typeof a.target_weight === 'number' ? a.target_weight : parseFloat(a.target_weight) || 0
        return {
          label: a.asset_symbol,
          percentage: Math.round(weight * 10000) / 100,
          colorHex: greys[i % greys.length],
        }
      })
      result.push({
        id: crypto.randomUUID(),
        type: 'AllocationModule',
        enabled: true,
        content: {
          title: 'Allocation',
          introText: '',
          size: 'large',
          slices,
        },
      })
    }
    if (!result.some((m) => m.type === 'PerformanceChart')) {
      result.push({
        id: crypto.randomUUID(),
        type: 'PerformanceChart',
        enabled: true,
        content: {
          title: 'Performance',
        },
      })
    }
    return result
  }

  // ── Create Bundle helpers ──

  const openCreateBundle = async () => {
    setShowCreateBundle(true)
    setBundleName('')
    setBundleCode('')
    setBundleDescription('')
    setBundleRisk('high')
    setBundleAllocations([])
    setLoadingInstruments(true)
    try {
      const res = await fetch('/api/admin/portfolio-engine/instruments', {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        const items = (data.data ?? data.items ?? []) as Array<{
          id: string
          code: string
          name: string
          asset?: { symbol?: string }
        }>
        setAvailableInstruments(
          items.map((i) => ({
            id: i.id,
            code: i.code,
            name: i.name,
            asset_symbol: i.asset?.symbol ?? i.code.replace('-SPOT', ''),
          })),
        )
      }
    } catch {
      toastError('Impossible de charger les instruments.')
    } finally {
      setLoadingInstruments(false)
    }
  }

  const addBundleAllocation = () => {
    const used = new Set(bundleAllocations.map((a) => a.instrumentId))
    const nextInstrument = availableInstruments.find((i) => !used.has(i.id))
    if (!nextInstrument) return
    setBundleAllocations((prev) => [
      ...prev,
      {
        instrumentId: nextInstrument.id,
        instrumentCode: nextInstrument.code,
        assetSymbol: nextInstrument.asset_symbol ?? nextInstrument.code,
        weight: 0,
      },
    ])
  }

  const removeBundleAllocation = (index: number) => {
    setBundleAllocations((prev) => prev.filter((_, i) => i !== index))
  }

  const updateBundleAllocation = (
    index: number,
    field: 'instrumentId' | 'weight',
    value: string | number,
  ) => {
    setBundleAllocations((prev) =>
      prev.map((a, i) => {
        if (i !== index) return a
        if (field === 'instrumentId') {
          const inst = availableInstruments.find((ins) => ins.id === value)
          return {
            ...a,
            instrumentId: value as string,
            instrumentCode: inst?.code ?? a.instrumentCode,
            assetSymbol: inst?.asset_symbol ?? inst?.code ?? a.assetSymbol,
          }
        }
        return { ...a, weight: value as number }
      }),
    )
  }

  const bundleTotalWeight = useMemo(
    () => bundleAllocations.reduce((s, a) => s + a.weight, 0),
    [bundleAllocations],
  )

  const handleCreateBundle = async () => {
    if (!bundleName.trim()) {
      toastError('Le nom du bundle est requis.')
      return
    }
    const code = bundleCode.trim() || bundleName.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '_')
    if (bundleAllocations.length === 0) {
      toastError('Ajoutez au moins une allocation.')
      return
    }
    if (Math.abs(bundleTotalWeight - 100) > 0.5) {
      toastError(`Les poids doivent totaliser 100% (actuellement ${bundleTotalWeight.toFixed(1)}%).`)
      return
    }

    setCreatingBundle(true)
    try {
      const res = await fetch('/api/admin/portfolio-engine/bundles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          name: bundleName.trim(),
          productCode: code,
          description: bundleDescription.trim(),
          riskLabel: bundleRisk,
          allocations: bundleAllocations.map((a) => ({
            instrumentId: a.instrumentId,
            instrumentCode: a.instrumentCode,
            assetSymbol: a.assetSymbol,
            targetWeight: a.weight / 100,
          })),
          availableRebalanceFrequencies: ['weekly', 'monthly', 'quarterly'],
        }),
      })

      if (!res.ok) {
        const payload = (await res.json().catch(() => ({}))) as {
          error?: string
          detail?: unknown
          issues?: unknown
        }
        const fromApi =
          typeof payload.error === 'string' && payload.error.trim().length > 0
            ? payload.error.trim()
            : null
        const fromDetail =
          typeof payload.detail === 'string'
            ? payload.detail
            : Array.isArray(payload.detail)
              ? payload.detail
                  .map((d: { msg?: string; loc?: unknown[] }) =>
                    d && typeof d === 'object' && 'msg' in d ? String(d.msg) : JSON.stringify(d),
                  )
                  .filter(Boolean)
                  .join(' · ')
              : ''
        let message = fromApi || fromDetail || 'Création impossible'
        if (/already exists/i.test(message)) {
          message =
            'Ce code produit est déjà utilisé. Choisissez un autre code (ex. TOP_5_V2) ou supprimez le bundle existant.'
        }
        throw new Error(message)
      }

      const result = await res.json().catch(() => ({}))
      if (result.warning) {
        toastWarning('Bundle créé avec succès, mais la configuration UI (modules) n\'a pas pu être sauvegardée. Vous pouvez la configurer manuellement.')
      }
      toastSuccess(`Bundle "${bundleName}" créé avec succès !`)
      setShowCreateBundle(false)

      // Refresh product list
      const productsRes = await fetch('/api/admin/portfolio-engine/products', {
        credentials: 'include',
      }).catch(() => null)
      if (productsRes?.ok) {
        const data = await productsRes.json()
        setPortfolioProducts(data.items ?? [])
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      toastError(msg)
    } finally {
      setCreatingBundle(false)
    }
  }

  const loadAllSortOrders = async (products: PortfolioProduct[]) => {
    const orders: Record<string, number> = {}
    const pubStates: Record<string, boolean> = {}
    await Promise.all(
      products.map(async (p) => {
        const enginePublic = typeof p.is_public === 'boolean' ? p.is_public : undefined
        try {
          const res = await fetch(
            `/api/admin/portfolio-engine/products/${encodeURIComponent(p.product_code)}/config`,
            { credentials: 'include' }
          )
          if (res.ok) {
            const data = await res.json()
            orders[p.product_code] = typeof data.sortOrder === 'number' ? data.sortOrder : 999
            // Liste admin bundles expose `is_public` (FastAPI) ; Prisma peut encore être absent / défaut false.
            pubStates[p.product_code] =
              typeof enginePublic === 'boolean' ? enginePublic : data.isPublished === true
          } else {
            orders[p.product_code] = 999
            pubStates[p.product_code] = enginePublic ?? false
          }
        } catch {
          orders[p.product_code] = 999
          pubStates[p.product_code] = enginePublic ?? false
        }
      })
    )
    setProductSortOrders(orders)
    setProductPublishStates(pubStates)
  }

  const sortedPortfolioProducts = useMemo(() => {
    return [...portfolioProducts].sort((a, b) => {
      const sa = productSortOrders[a.product_code] ?? 999
      const sb = productSortOrders[b.product_code] ?? 999
      if (sa !== sb) return sa - sb
      return a.name.localeCompare(b.name)
    })
  }, [portfolioProducts, productSortOrders])

  const handleReorderProduct = async (productCode: string, direction: 'up' | 'down') => {
    const sameType = sortedPortfolioProducts.filter((p) => p.product_type === portfolioProducts.find((pp) => pp.product_code === productCode)?.product_type)
    const idx = sameType.findIndex((p) => p.product_code === productCode)
    if (idx < 0) return
    const targetIdx = direction === 'up' ? idx - 1 : idx + 1
    if (targetIdx < 0 || targetIdx >= sameType.length) return

    const reordered = [...sameType]
    ;[reordered[idx], reordered[targetIdx]] = [reordered[targetIdx], reordered[idx]]

    const newOrders = { ...productSortOrders }
    for (let i = 0; i < reordered.length; i++) {
      newOrders[reordered[i].product_code] = i
    }
    setProductSortOrders(newOrders)
    if (selectedProductCode === productCode) {
      setProductSortOrder(newOrders[productCode])
    }

    await Promise.all(
      reordered.map(async (p, i) => {
        try {
          const res = await fetch(
            `/api/admin/portfolio-engine/products/${encodeURIComponent(p.product_code)}/config`,
            { credentials: 'include' }
          )
          const data = res.ok ? await res.json() : {}
          await fetch(
            `/api/admin/portfolio-engine/products/${encodeURIComponent(p.product_code)}/config`,
            {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({
                headerMediaId: data.headerMediaId ?? null,
                modules: Array.isArray(data.modules) ? data.modules : [],
                sortOrder: i,
              }),
            }
          )
        } catch { /* best-effort */ }
      })
    )
    toastSuccess('Ordre mis à jour.')
  }

  const loadProductConfig = async (productCode: string) => {
    const product = portfolioProducts.find((p) => p.product_code === productCode)
    try {
      const res = await fetch(
        `/api/admin/portfolio-engine/products/${encodeURIComponent(productCode)}/config`,
        { credentials: 'include' }
      )
      const data = await res.json()
      if (res.ok) {
        setProductHeaderMediaId(data.headerMediaId ?? null)
        setProductDetailMediaId(data.detailMediaId ?? null)
        const raw = Array.isArray(data.modules) ? data.modules : []
        setProductModules(ensureRequiredProductModules(raw, product))
        setProductSortOrder(typeof data.sortOrder === 'number' ? data.sortOrder : 999)
        setProductIsPublished(data.isPublished === true)
      } else {
        setProductHeaderMediaId(null)
        setProductDetailMediaId(null)
        setProductModules(ensureRequiredProductModules([], product))
        setProductSortOrder(999)
        setProductIsPublished(false)
      }
    } catch {
      setProductHeaderMediaId(null)
      setProductDetailMediaId(null)
      setProductModules(ensureRequiredProductModules([], product))
      setProductSortOrder(999)
      setProductIsPublished(false)
    }
  }

  const handleSelectProduct = (productCode: string) => {
    setSelectedProductCode(productCode)
    loadProductConfig(productCode)
  }

  const handleSaveProductConfig = async () => {
    if (!selectedProductCode) return
    setProductConfigSaving(true)
    try {
      const res = await fetch(
        `/api/admin/portfolio-engine/products/${encodeURIComponent(selectedProductCode)}/config`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ headerMediaId: productHeaderMediaId, detailMediaId: productDetailMediaId, modules: productModules, sortOrder: productSortOrder, isPublished: productIsPublished }),
        }
      )
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}))
        if (res.status === 401) {
          toastError('Session expirée. Reconnectez-vous.')
          router.push('/admin/login')
          return
        }
        throw new Error(payload.detail || payload.error || 'Sauvegarde impossible')
      }
      toastSuccess('Configuration produit enregistrée.')
    } catch (e: any) {
      toastError(e?.message || 'Sauvegarde impossible')
    } finally {
      setProductConfigSaving(false)
    }
  }

  const handleTogglePublish = async (productCode: string, currentlyPublished: boolean) => {
    const product = portfolioProducts.find((p) => p.product_code === productCode)
    if (!product) return
    const newState = !currentlyPublished
    try {
      const res = await fetch(
        `/api/admin/portfolio-engine/bundles/${encodeURIComponent(product.id)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ is_public: newState }),
        }
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.error || data.detail || 'Échec de la mise à jour')
      }
      setProductPublishStates((prev) => ({ ...prev, [productCode]: newState }))
      if (selectedProductCode === productCode) setProductIsPublished(newState)
      if (data.warning) {
        toastWarning(data.warning)
      } else {
        toastSuccess(newState ? 'Bundle publié.' : 'Bundle dépublié.')
      }
    } catch (e: any) {
      toastError(e?.message || 'Impossible de modifier la publication.')
    }
  }

  const handleDeleteBundle = async (product: PortfolioProduct) => {
    const confirmed = window.confirm(
      `Supprimer définitivement le bundle "${product.name}" (${product.product_code}) ?\n\nCette action est irréversible et supprimera toutes les données associées.`
    )
    if (!confirmed) return
    try {
      const res = await fetch(
        `/api/admin/portfolio-engine/bundles/${encodeURIComponent(product.id)}`,
        {
          method: 'DELETE',
          credentials: 'include',
        }
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.error || data.detail || 'Suppression impossible')
      }
      toastSuccess(`Bundle "${product.name}" supprimé.`)
      setPortfolioProducts((prev) => prev.filter((p) => p.id !== product.id))
      if (selectedProductCode === product.product_code) {
        setSelectedProductCode(null)
        setProductModules([])
        setProductHeaderMediaId(null)
      }
    } catch (e: any) {
      toastError(e?.message || 'Suppression impossible')
    }
  }

  const addProductModuleOfType = (type: string) => {
    if (!getVaultModuleDefinition(type)) {
      toastError(`Type de module inconnu : ${type}`)
      return
    }
    const content = getVaultModuleDefaultContent(type)
    setProductModules((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        type,
        enabled: true,
        content,
      },
    ])
    toastSuccess(`Module « ${getVaultModuleLabel(type)} » ajouté.`)
  }

  const reorderProductModulesByIds = (orderedIds: string[]) => {
    const map = new Map(productModules.map((m) => [m.id, m]))
    setProductModules(orderedIds.map((id) => map.get(id)).filter(Boolean) as LandingModule[])
  }

  const handleUpdateProductModuleContent = (moduleId: string, raw: string) => {
    try {
      const parsed = JSON.parse(sanitizeJsonNewlines(raw)) as Record<string, unknown>
      setProductModules((prev) =>
        prev.map((m) => (m.id === moduleId ? { ...m, content: parsed } : m))
      )
    } catch {
      toastError('JSON invalide — vérifiez la syntaxe (guillemets, virgules, accolades).')
    }
  }

  const handlePatchProductModuleContent = (moduleId: string, patch: Record<string, unknown>) => {
    setProductModules((prev) =>
      prev.map((m) =>
        m.id === moduleId ? { ...m, content: { ...m.content, ...patch } } : m
      ),
    )
  }

  const REQUIRED_PRODUCT_MODULE_TYPES = ['TitlePage', 'AllocationModule', 'PerformanceChart']

  const removeProductModule = (moduleId: string) => {
    const target = productModules.find((m) => m.id === moduleId)
    if (target && REQUIRED_PRODUCT_MODULE_TYPES.includes(target.type)) {
      toastError(`Le module ${target.type} est obligatoire et ne peut pas être supprimé.`)
      return
    }
    setProductModules((prev) => prev.filter((m) => m.id !== moduleId))
  }

  if (loading) {
    return <div className="p-6 text-gray-500">Chargement du Vault Builder…</div>
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="min-w-0 flex-1">
          <h1 className="text-3xl font-bold text-gray-900">
            {eoWorkspace ? 'Exclusive Offer — Vault Builder' : 'Vault Builder'}
          </h1>
          <p className="text-gray-600 mt-1">
            Créer des vaults à la demande via le builder : identité, médias, registre catalogue, modules et contenu dynamique.
          </p>
          <div className="mt-2 flex flex-wrap gap-3 text-sm">
            <Link
              href="/admin/vault-builder/exclusive-offers"
              className="text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Exclusive Offers (workspace)
            </Link>
            <span className="text-gray-300">|</span>
            <Link href="/admin" className="text-gray-600 hover:text-gray-900">
              ← Dashboard
            </Link>
          </div>
          {eoWorkspace && (
            <div className="mt-4 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-950">
              <p className="font-semibold">Édition Exclusive Offer</p>
              <p className="mt-1 text-indigo-900/90">
                Parcours recommandé : <strong>informations générales</strong> (identité, médias, registre) →{' '}
                <strong>Moteur lending</strong> → contenu (modules ci-dessous).{' '}
                <Link
                  className="underline font-medium whitespace-nowrap"
                  href="/admin/vault-builder/exclusive-offers"
                >
                  Liste des Exclusive Offers
                </Link>
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow border border-gray-100 p-4">
        <h2 className="text-lg font-semibold mb-3">Créer un vault</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <input
            value={newSlug}
            onChange={(e) => {
              setNewSlug(e.target.value)
              if (createError) setCreateError(null)
            }}
            onBlur={() => {
              if (newSlug.trim().length > 0) {
                setNewSlug(normalizedNewSlug)
              }
            }}
            placeholder="slug (ex: offre-printemps)"
            className="px-3 py-2 border rounded-md"
          />
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Titre"
            className="px-3 py-2 border rounded-md"
          />
          <input
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            placeholder="Description"
            className="px-3 py-2 border rounded-md"
          />
          <select
            value={newInvestmentTypeSlug}
            onChange={(e) => setNewInvestmentTypeSlug(e.target.value)}
            className="px-3 py-2 border rounded-md"
          >
            <option value="">— Catégorie —</option>
            {investmentTypes.map((t) => (
              <option key={t.id} value={t.slug}>
                {t.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleCreatePage}
            disabled={creating}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            {creating ? 'Création…' : 'Créer'}
          </button>
        </div>
        <div className="mt-2 text-xs">
          <span className="text-gray-500">
            Slug normalisé: <code className="font-mono">{normalizedNewSlug || '—'}</code>
          </span>
          {createError ? <p className="text-red-600 mt-1">{createError}</p> : null}
        </div>
      </div>

      {/* ════════════════════ Create Bundle Modal ════════════════════ */}
      {showCreateBundle && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-gray-900">Créer un Crypto Bundle</h3>
                <button
                  type="button"
                  onClick={() => setShowCreateBundle(false)}
                  className="text-gray-400 hover:text-gray-600 text-xl leading-none"
                >
                  ×
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nom du bundle *</label>
                  <input
                    value={bundleName}
                    onChange={(e) => {
                      setBundleName(e.target.value)
                      if (!bundleCode || bundleCode === bundleName.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '_')) {
                        setBundleCode(e.target.value.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '_'))
                      }
                    }}
                    placeholder="ex. Crypto Bundle Top 5"
                    className="w-full px-3 py-2 border rounded-md text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Code produit *</label>
                  <input
                    value={bundleCode}
                    onChange={(e) => setBundleCode(e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, ''))}
                    placeholder="ex. CRYPTO_BUNDLE_TOP5"
                    className="w-full px-3 py-2 border rounded-md text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={bundleDescription}
                    onChange={(e) => setBundleDescription(e.target.value)}
                    rows={2}
                    placeholder="Description courte du bundle…"
                    className="w-full px-3 py-2 border rounded-md text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Niveau de risque</label>
                  <select
                    value={bundleRisk}
                    onChange={(e) => setBundleRisk(e.target.value as typeof bundleRisk)}
                    className="w-full px-3 py-2 border rounded-md text-sm"
                  >
                    <option value="low">Low</option>
                    <option value="moderate">Moderate</option>
                    <option value="high">High</option>
                    <option value="very_high">Very High</option>
                  </select>
                </div>
              </div>

              {/* ── Allocations ── */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">
                    Allocations *{' '}
                    <span className={`font-mono text-xs ${Math.abs(bundleTotalWeight - 100) <= 2 ? 'text-green-600' : 'text-red-500'}`}>
                      ({bundleTotalWeight.toFixed(1)}%)
                    </span>
                  </label>
                  <button
                    type="button"
                    onClick={addBundleAllocation}
                    disabled={loadingInstruments || bundleAllocations.length >= availableInstruments.length}
                    className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border border-indigo-200 text-indigo-700 hover:bg-indigo-50 disabled:opacity-40"
                  >
                    <Plus className="w-3 h-3" /> Ajouter
                  </button>
                </div>
                {loadingInstruments ? (
                  <p className="text-sm text-gray-400 animate-pulse">Chargement des instruments…</p>
                ) : bundleAllocations.length === 0 ? (
                  <p className="text-xs text-gray-400">Aucune allocation. Cliquez sur Ajouter.</p>
                ) : (
                  <div className="space-y-2">
                    {bundleAllocations.map((alloc, idx) => {
                      const usedByOthers = new Set(
                        bundleAllocations.filter((_, i) => i !== idx).map((a) => a.instrumentId),
                      )
                      return (
                      <div key={idx} className="flex items-center gap-2">
                        <select
                          value={alloc.instrumentId}
                          onChange={(e) => updateBundleAllocation(idx, 'instrumentId', e.target.value)}
                          className="flex-1 px-2 py-1.5 border rounded text-sm"
                        >
                          {availableInstruments
                            .filter((inst) => inst.id === alloc.instrumentId || !usedByOthers.has(inst.id))
                            .map((inst) => (
                            <option key={inst.id} value={inst.id}>
                              {inst.asset_symbol ?? inst.code} — {inst.name}
                            </option>
                          ))}
                        </select>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            min={0}
                            max={100}
                            step={1}
                            value={alloc.weight}
                            onChange={(e) =>
                              updateBundleAllocation(idx, 'weight', parseFloat(e.target.value) || 0)
                            }
                            className="w-20 px-2 py-1.5 border rounded text-sm text-right font-mono"
                          />
                          <span className="text-xs text-gray-500">%</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeBundleAllocation(idx)}
                          className="p-1 rounded border border-red-200 text-red-500 hover:bg-red-50"
                          title="Supprimer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Required modules info */}
              <div className="bg-indigo-50 rounded-md p-3 text-xs text-indigo-700 space-y-1">
                <p className="font-semibold">Modules requis créés automatiquement :</p>
                <ul className="list-disc list-inside space-y-0.5">
                  <li>TitlePage — titre éditable dans le builder</li>
                  <li>PerformanceChart — historique pondéré du bundle</li>
                  <li>AllocationModule — donut des allocations</li>
                </ul>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setShowCreateBundle(false)}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  Annuler
                </button>
                <button
                  type="button"
                  onClick={handleCreateBundle}
                  disabled={creatingBundle}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                >
                  <Plus className="w-4 h-4" />
                  {creatingBundle ? 'Création en cours…' : 'Créer le Bundle'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow border border-gray-100 p-4">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => setPortfolioProductsExpanded((e) => !e)}
            className="flex items-center gap-2 text-left"
          >
            {portfolioProductsExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
            <Package className="w-4 h-4 text-indigo-600" />
            <h2 className="text-lg font-semibold text-gray-900">Produits Portfolio Engine</h2>
            <span className="text-sm text-gray-500">
              ({portfolioProducts.length} produit{portfolioProducts.length !== 1 ? 's' : ''})
            </span>
          </button>
          <button
            type="button"
            onClick={openCreateBundle}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-indigo-600 text-white text-sm hover:bg-indigo-700"
          >
            <Plus className="w-4 h-4" />
            Create Bundle
          </button>
        </div>
        {portfolioProductsExpanded && (
          <div className="mt-4">
            {portfolioProducts.length === 0 ? (
              <p className="text-sm text-gray-500">
                Aucun produit actif. Utilisez le bouton &quot;Create Bundle&quot; pour créer votre premier bundle.
              </p>
            ) : (
              <div className="grid grid-cols-1 xl:grid-cols-[280px_1fr] gap-6">
                <aside className="space-y-4">
                  {sortedPortfolioProducts.filter((p) => p.product_type === 'crypto_bundle').length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                        Crypto Bundles
                      </div>
                      <ul className="space-y-2">
                        {sortedPortfolioProducts
                          .filter((p) => p.product_type === 'crypto_bundle')
                          .map((p, idx, arr) => {
                            const active = selectedProductCode === p.product_code
                            return (
                              <li key={p.id} className="flex items-center gap-1">
                                <div className="flex flex-col gap-0.5 shrink-0">
                                  <button
                                    type="button"
                                    onClick={() => handleReorderProduct(p.product_code, 'up')}
                                    disabled={idx === 0}
                                    className="p-1 rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                                    title="Monter"
                                  >
                                    <ArrowUp className="w-3 h-3" />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleReorderProduct(p.product_code, 'down')}
                                    disabled={idx === arr.length - 1}
                                    className="p-1 rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                                    title="Descendre"
                                  >
                                    <ArrowDown className="w-3 h-3" />
                                  </button>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => handleSelectProduct(p.product_code)}
                                  className={`flex-1 text-left rounded-md border px-3 py-2.5 ${
                                    active
                                      ? 'border-indigo-500 bg-indigo-50'
                                      : 'border-gray-200 hover:bg-gray-50'
                                  }`}
                                >
                                  <div className="flex items-center gap-2">
                                    <div className="font-medium text-gray-900">{p.name}</div>
                                    <span className="text-[10px] font-mono text-gray-400">#{(productSortOrders[p.product_code] ?? 999)}</span>
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                                      productPublishStates[p.product_code]
                                        ? 'bg-green-100 text-green-700'
                                        : 'bg-gray-100 text-gray-500'
                                    }`}>
                                      {productPublishStates[p.product_code] ? 'Publié' : 'Brouillon'}
                                    </span>
                                  </div>
                                  <div className="text-xs text-gray-500 font-mono mt-0.5">
                                    {p.product_code}
                                  </div>
                                  {p.allocations?.length > 0 && (
                                    <div className="text-sm text-gray-600 mt-2">
                                      {p.allocations
                                        .map(
                                          (a) =>
                                            `${a.asset_symbol} ${(parseFloat(a.target_weight) * 100).toFixed(0)}%`
                                        )
                                        .join(' / ')}
                                    </div>
                                  )}
                                </button>
                              </li>
                            )
                          })}
                      </ul>
                    </div>
                  )}
                  {sortedPortfolioProducts.filter((p) => p.product_type !== 'crypto_bundle').length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                        Autres produits
                      </div>
                      <ul className="space-y-2">
                        {sortedPortfolioProducts
                          .filter((p) => p.product_type !== 'crypto_bundle')
                          .map((p, idx, arr) => {
                            const active = selectedProductCode === p.product_code
                            return (
                              <li key={p.id} className="flex items-center gap-1">
                                <div className="flex flex-col gap-0.5 shrink-0">
                                  <button
                                    type="button"
                                    onClick={() => handleReorderProduct(p.product_code, 'up')}
                                    disabled={idx === 0}
                                    className="p-1 rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                                    title="Monter"
                                  >
                                    <ArrowUp className="w-3 h-3" />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleReorderProduct(p.product_code, 'down')}
                                    disabled={idx === arr.length - 1}
                                    className="p-1 rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                                    title="Descendre"
                                  >
                                    <ArrowDown className="w-3 h-3" />
                                  </button>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => handleSelectProduct(p.product_code)}
                                  className={`flex-1 text-left rounded-md border px-3 py-2.5 ${
                                    active
                                      ? 'border-indigo-500 bg-indigo-50'
                                      : 'border-gray-200 hover:bg-gray-50'
                                  }`}
                                >
                                  <div className="font-medium text-gray-900">{p.name}</div>
                                  <div className="text-xs text-gray-500 font-mono mt-0.5">
                                    {p.product_code} · {p.product_type}
                                  </div>
                                </button>
                              </li>
                            )
                          })}
                      </ul>
                    </div>
                  )}
                </aside>

                <section className="bg-gray-50/50 rounded-lg border border-gray-200 p-5">
                  {!selectedProductCode ? (
                    <p className="text-gray-500">
                      Sélectionne un produit à gauche pour éditer ses modules.
                    </p>
                  ) : (
                    <div className="space-y-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="text-lg font-semibold text-gray-900">
                              {portfolioProducts.find((p) => p.product_code === selectedProductCode)
                                ?.name ?? selectedProductCode}
                            </h3>
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                              productIsPublished
                                ? 'bg-green-100 text-green-700'
                                : 'bg-gray-100 text-gray-500'
                            }`}>
                              {productIsPublished ? 'Publié' : 'Brouillon'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-500 font-mono">{selectedProductCode}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleTogglePublish(selectedProductCode, productIsPublished)}
                            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium border ${
                              productIsPublished
                                ? 'border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100'
                                : 'border-green-300 bg-green-50 text-green-700 hover:bg-green-100'
                            }`}
                          >
                            {productIsPublished ? 'Dépublier' : 'Publier'}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const product = portfolioProducts.find((p) => p.product_code === selectedProductCode)
                              if (product) handleDeleteBundle(product)
                            }}
                            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium border border-red-300 bg-red-50 text-red-700 hover:bg-red-100"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Supprimer
                          </button>
                          <button
                            type="button"
                            onClick={handleSaveProductConfig}
                            disabled={productConfigSaving}
                            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                          >
                            <Save className="w-4 h-4" />
                            {productConfigSaving ? 'Sauvegarde…' : 'Enregistrer'}
                          </button>
                        </div>
                      </div>

                      <div className="border rounded-lg p-4 space-y-2 bg-white">
                        <h4 className="font-semibold text-gray-900">Media Header (Card)</h4>
                        <p className="text-xs text-gray-500">
                          Image d&apos;arrière-plan affichée sur la card du produit dans le widget Crypto Bundles.
                        </p>
                        <MediaField
                          label="Image header (card)"
                          value={productHeaderMediaId}
                          onChange={(mediaId) => setProductHeaderMediaId(mediaId ?? null)}
                        />
                      </div>

                      <div className="border rounded-lg p-4 space-y-2 bg-white">
                        <h4 className="font-semibold text-gray-900">Media Detail (Page)</h4>
                        <p className="text-xs text-gray-500">
                          Image d&apos;arrière-plan affichée en hero sur la page détail du produit.
                        </p>
                        <MediaField
                          label="Image detail (page background)"
                          value={productDetailMediaId}
                          onChange={(mediaId) => setProductDetailMediaId(mediaId ?? null)}
                        />
                      </div>

                      <VaultModulesSection
                        title="Modules du produit (bundle)"
                        modules={productModules}
                        entityId={`portfolio-product-${selectedProductCode ?? 'none'}`}
                        saving={productConfigSaving}
                        onClickAddModule={() => setProductAddModuleOpen(true)}
                        onReorderModules={reorderProductModulesByIds}
                        onDeleteModule={removeProductModule}
                        onToggleEnabled={(moduleId, enabled) =>
                          setProductModules((prev) =>
                            prev.map((m) => (m.id === moduleId ? { ...m, enabled } : m))
                          )
                        }
                        isModuleLocked={(m) => REQUIRED_PRODUCT_MODULE_TYPES.includes(m.type)}
                        renderModuleEditor={(module) => (
                          <>
                            {module.type === 'MediaImageCarouselModule' ? (
                              <VaultMediaCarouselModuleEditor
                                content={module.content}
                                onPatch={(patch) =>
                                  handlePatchProductModuleContent(module.id, patch)
                                }
                              />
                            ) : module.type === 'DocumentsListModule' ? (
                              <VaultDocumentsListModuleEditor
                                content={module.content}
                                onPatch={(patch) =>
                                  handlePatchProductModuleContent(module.id, patch)
                                }
                              />
                            ) : module.type === 'VideoBlockArticleModule' ? (
                              <VaultVideoBlockArticleModuleEditor
                                content={module.content}
                                onPatch={(patch) =>
                                  handlePatchProductModuleContent(module.id, patch)
                                }
                              />
                            ) : module.type === 'LocalisationModule' ? (
                              <VaultLocalisationModuleEditor
                                content={module.content}
                                onPatch={(patch) =>
                                  handlePatchProductModuleContent(module.id, patch)
                                }
                              />
                            ) : module.type === 'VirtualVisualizationModule' ? (
                              <VaultVirtualVisualizationModuleEditor
                                content={module.content}
                                onPatch={(patch) =>
                                  handlePatchProductModuleContent(module.id, patch)
                                }
                              />
                            ) : (
                              <>
                                <textarea
                                  key={module.id}
                                  defaultValue={JSON.stringify(module.content, null, 2)}
                                  onBlur={(e) =>
                                    handleUpdateProductModuleContent(module.id, e.target.value)
                                  }
                                  className="w-full min-h-[120px] p-2 border rounded-md font-mono text-xs"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                  Édite le JSON puis quitte le champ pour appliquer.
                                </p>
                              </>
                            )}
                          </>
                        )}
                      />
                    </div>
                  )}
                </section>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[320px_1fr] gap-6">
        <aside className="bg-white rounded-lg shadow border border-gray-100 p-4">
          <h3 className="text-base font-semibold mb-3">Vaults par catégorie</h3>
          {vaults.length === 0 ? (
            <p className="text-sm text-gray-500">Aucun vault.</p>
          ) : (
            <div className="space-y-4">
              {vaultsByCategoryEntries.map(([categoryKey, categoryVaults]) => (
                <div key={categoryKey}>
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    {categoryLabels.get(categoryKey) ?? categoryKey}
                  </div>
                  <ul className="space-y-2">
                    {categoryVaults.map((row, idx) => {
                      const active = row.slug === selectedSlug
                      const canMoveUp = idx > 0
                      const canMoveDown = idx < categoryVaults.length - 1
                      const isReordering = reordering === row.slug
                      return (
                        <li key={row.id} className="flex items-center gap-1">
                          <div className="flex flex-col gap-0.5 shrink-0">
                            <button
                              type="button"
                              onClick={() => canMoveUp && handleReorder(row.slug, 'up')}
                              disabled={!canMoveUp || isReordering}
                              className="p-1 rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                              title="Monter"
                            >
                              <ArrowUp className="w-3 h-3" />
                            </button>
                            <button
                              type="button"
                              onClick={() => canMoveDown && handleReorder(row.slug, 'down')}
                              disabled={!canMoveDown || isReordering}
                              className="p-1 rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                              title="Descendre"
                            >
                              <ArrowDown className="w-3 h-3" />
                            </button>
                          </div>
                          <button
                            type="button"
                            onClick={() => setSelectedSlug(row.slug)}
                            className={`flex-1 text-left rounded-md border px-3 py-2 ${
                              active ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:bg-gray-50'
                            }`}
                          >
                            <div className="font-medium text-gray-900">{row.title || row.slug}</div>
                            <div className="text-xs text-gray-500 font-mono">{row.urlPath}</div>
                            <div className="text-xs text-gray-500 mt-1">
                              Template: {row.configSummary.templateKey || '—'} · Modules:{' '}
                              {row.configSummary.modulesCount}
                            </div>
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </aside>

        <section className="bg-white rounded-lg shadow border border-gray-100 p-5">
          {!details ? (
            <p className="text-gray-500">Sélectionne un vault pour l'éditer.</p>
          ) : (
            <div className="lg:grid lg:grid-cols-2 lg:items-start lg:gap-6 lg:divide-x lg:divide-slate-200">
              <div className="space-y-6 lg:min-w-0 lg:pr-6">
              <AdminEditingLocaleBar contextLabel="Vault" />

              <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={saving || packagedPublishBusy || publishVaultBusy}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <Save className="w-4 h-4 shrink-0" />
                    {saving ? 'Enregistrement…' : 'Enregistrer (brouillon)'}
                  </button>
                  <button
                    type="button"
                    onClick={handlePublishVaultLocale}
                    disabled={
                      publishVaultBusy ||
                      saving ||
                      packagedPublishBusy ||
                      !canPublishVaultLocale
                    }
                    title={
                      !canPublishVaultLocale
                        ? 'Enregistrez un brouillon vault pour cette langue avant de publier.'
                        : 'Copie le brouillon vers PUBLISHED pour cette langue uniquement.'
                    }
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-emerald-300 bg-emerald-50 text-emerald-900 text-sm font-medium hover:bg-emerald-100 disabled:opacity-50"
                  >
                    <UploadCloud className="w-4 h-4 shrink-0" />
                    {publishVaultBusy ? 'Publication…' : 'Publier'}
                  </button>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <button
                        type="button"
                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-gray-200 bg-white text-sm font-medium text-gray-800 hover:bg-gray-50"
                      >
                        Plus d&apos;actions
                        <ChevronDown className="w-4 h-4 shrink-0 text-gray-500" />
                      </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                      {productDraft?.enabled &&
                        details.packagedProduct &&
                        productDraft.productType === 'EXCLUSIVE_OFFER' && (
                          <DropdownMenuItem
                            disabled={
                              packagedPublishBusy || saving || publishVaultBusy
                            }
                            onSelect={(e) => {
                              e.preventDefault()
                              void handleToggleExclusiveOfferCatalogPublish()
                            }}
                          >
                            {packagedPublishBusy
                              ? '…'
                              : productDraft.commercialStatus === 'PUBLISHED'
                                ? 'Dépublier (catalogue offre)'
                                : productDraft.commercialStatus === 'ARCHIVED'
                                  ? 'Republier (catalogue offre)'
                                  : 'Publier dans le catalogue'}
                          </DropdownMenuItem>
                        )}
                      <DropdownMenuItem
                        variant="destructive"
                        disabled={deleting || publishVaultBusy}
                        onSelect={(e) => {
                          e.preventDefault()
                          void handleDeletePage()
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                        Supprimer le vault
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_minmax(11rem,19rem)] gap-4 md:gap-6 md:items-start">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <input
                        type="text"
                        value={details.page.title ?? ''}
                        onChange={(e) =>
                          updateDetails((prev) => ({
                            ...prev,
                            page: { ...prev.page, title: e.target.value },
                          }))
                        }
                        placeholder={details.page.slug}
                        aria-label={"Nom de l'offre"}
                        className="min-w-0 w-full border-0 border-b border-transparent bg-transparent px-0 py-0.5 text-xl font-semibold text-gray-900 placeholder:text-gray-400 transition-colors hover:border-gray-200 focus:border-indigo-500 focus:outline-none focus:ring-0"
                      />
                    </div>
                    <p className="text-sm text-gray-500 font-mono truncate" title={details.page.urlPath}>
                      {details.page.urlPath}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Slug page{' '}
                      <span className="font-mono text-gray-700">{details.page.slug}</span>
                    </p>
                  </div>

                  <div className="min-w-0 w-full md:justify-self-end md:border-l md:border-gray-100 md:pl-6">
                    <MediaField
                      compact
                      label="Image de couverture (header)"
                      value={details.config.headerMediaId ?? null}
                      onChange={(mediaId) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: { ...prev.config, headerMediaId: mediaId ?? undefined },
                        }))
                      }
                    />
                  </div>
                </div>

                <div className="space-y-4 pt-4 mt-4 border-t border-gray-100">
                  <CollapsibleAdminSection
                    title="Vidéo promo (optionnel)"
                    summary={promoVideoSectionSummary}
                    icon={<Video className="h-3.5 w-3.5" />}
                    defaultOpen={false}
                    className="border-violet-200 bg-violet-50/50"
                    bodyClassName="space-y-3 border-violet-100 bg-violet-50/60 p-4"
                  >
                    <p className="text-xs text-gray-600">
                      Si une URL ou un média est renseigné, l&apos;app peut afficher un bouton lecture sur le
                      hero. Stocké dans le module <strong>TitlePage</strong> (
                      <code className="text-[11px]">promoVideoUrl</code>
                      ).
                    </p>
                    <div>
                      <label className="block text-sm font-medium mb-1">URL de la vidéo (HTTPS)</label>
                      <input
                        type="url"
                        className="w-full px-3 py-2 border rounded-md text-sm font-mono"
                        placeholder="https://cdn…/video.mp4 ou lien Vimeo / YouTube…"
                        value={readPromoVideoFromVaultModules(details.config.modules).url}
                        onChange={(e) =>
                          updateDetails((prev) => ({
                            ...prev,
                            config: {
                              ...prev.config,
                              modules: upsertTitlePagePromoVideo(prev.config.modules, {
                                url: e.target.value,
                                mediaId: null,
                              }),
                            },
                          }))
                        }
                      />
                    </div>
                    <MediaField
                      label="Ou choisir une vidéo dans la médiathèque"
                      value={readPromoVideoFromVaultModules(details.config.modules).mediaId}
                      onChange={(mediaId) => {
                        if (!mediaId) {
                          updateDetails((prev) => ({
                            ...prev,
                            config: {
                              ...prev.config,
                              modules: upsertTitlePagePromoVideo(prev.config.modules, {
                                url: '',
                                mediaId: null,
                              }),
                            },
                          }))
                          return
                        }
                        void (async () => {
                          try {
                            const res = await fetch('/api/admin/media', { credentials: 'include' })
                            if (!res.ok) return
                            const data = (await res.json()) as { media?: Array<{ id: string; url: string }> }
                            const media = data.media?.find((m) => m.id === mediaId)
                            const url = typeof media?.url === 'string' ? media.url.trim() : ''
                            if (!url) return
                            updateDetails((prev) => ({
                              ...prev,
                              config: {
                                ...prev.config,
                                modules: upsertTitlePagePromoVideo(prev.config.modules, {
                                  url,
                                  mediaId,
                                }),
                              },
                            }))
                          } catch {
                            /* ignore */
                          }
                        })()
                      }}
                    />
                  </CollapsibleAdminSection>
                </div>

                {productDraft && (
                  <CollapsibleAdminSection
                    title="Product (tags, visibilité)"
                    summary={productRegistrySectionSummary}
                    icon={<Package className="h-3.5 w-3.5" />}
                    defaultOpen={false}
                  >
                    <PackagedProductSettingsPanel
                      draft={productDraft}
                      onChange={setProductDraft}
                      serverLinked={Boolean(details.packagedProduct)}
                      lendingEngineLinked={Boolean(details.packagedProduct?.lendingEngineLinked)}
                      embedded
                      suppressEmbeddedTitle
                      exclusiveOfferRegistryLocks={
                        details.packagedProduct?.productType === 'EXCLUSIVE_OFFER'
                      }
                    />
                  </CollapsibleAdminSection>
                )}
              </div>

              <CollapsibleAdminSection
                title="Moteur lending & pool"
                summary={vaultLendingSectionSummary}
                icon={<Landmark className="h-3.5 w-3.5" />}
                defaultOpen={false}
              >
              <PackagedEngineLendingSection
                packagedProductId={details.packagedProduct?.id ?? null}
                productType={
                  productDraft?.productType ?? details.packagedProduct?.productType ?? 'VAULT_SIMPLE'
                }
                hasPackagedRow={Boolean(details.packagedProduct)}
                onRefresh={async () => {
                  if (selectedSlug) await reloadVaultDetails(selectedSlug)
                }}
              />
              </CollapsibleAdminSection>

              <VaultModulesSection
                title="Modules du vault"
                modules={details.config.modules}
                entityId={details.page.id}
                saving={saving}
                onClickAddModule={() => setVaultAddModuleOpen(true)}
                onReorderModules={reorderDetailModulesByIds}
                onDeleteModule={removeModule}
                onToggleEnabled={(moduleId, enabled) =>
                  updateDetails((prev) => ({
                    ...prev,
                    config: {
                      ...prev.config,
                      modules: prev.config.modules.map((m) =>
                        m.id === moduleId ? { ...m, enabled } : m
                      ),
                    },
                  }))
                }
                renderModuleEditor={(module) => (
                  <>
                    {module.type === 'MediaImageCarouselModule' ? (
                      <VaultMediaCarouselModuleEditor
                        content={module.content}
                        onPatch={(patch) => handlePatchModuleContentObject(module.id, patch)}
                      />
                    ) : module.type === 'DocumentsListModule' ? (
                      <VaultDocumentsListModuleEditor
                        content={module.content}
                        onPatch={(patch) => handlePatchModuleContentObject(module.id, patch)}
                      />
                    ) : module.type === 'VideoBlockArticleModule' ? (
                      <VaultVideoBlockArticleModuleEditor
                        content={module.content}
                        onPatch={(patch) => handlePatchModuleContentObject(module.id, patch)}
                      />
                    ) : module.type === 'LocalisationModule' ? (
                      <VaultLocalisationModuleEditor
                        content={module.content}
                        onPatch={(patch) => handlePatchModuleContentObject(module.id, patch)}
                      />
                    ) : module.type === 'VirtualVisualizationModule' ? (
                      <VaultVirtualVisualizationModuleEditor
                        content={module.content}
                        onPatch={(patch) => handlePatchModuleContentObject(module.id, patch)}
                      />
                    ) : (
                      <>
                        <textarea
                          key={module.id}
                          defaultValue={JSON.stringify(module.content, null, 2)}
                          onBlur={(e) => handleUpdateModuleContent(module.id, e.target.value)}
                          className="w-full min-h-[160px] p-2 border rounded-md font-mono text-xs"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Édite le JSON puis quitte le champ pour appliquer.
                        </p>
                        {module.type === 'CompetitiveAdvantagesModule' && (
                          <p className="text-xs text-gray-500 mt-2">
                            Options pour la catégorie (par row) : content (blanc, comportement actuel) ; work
                            (jaune clair #FEF9C3) ; note (bleu clair #DBEAFE) ; success (vert clair #D1FAE5) ;
                            danger (rouge clair #FEE2E2).
                          </p>
                        )}
                        {(module.type === 'MarketingCardsSmallSlidingCarrousel_Portrait' ||
                          module.type === 'MarketingCardsSmallSlidingCarrousel_Paysage') && (
                          <p className="text-xs text-gray-500 mt-2">
                            Options de taille des cartes : `visibleCardsCount` (ex: 1, 1.2, 1.5, 1.8; virgule
                            acceptee) et `cardAspectRatio` au format largeur:hauteur (ex: 1:1, 1:4, 3:4, 1:1.4).
                          </p>
                        )}
                      </>
                    )}
                  </>
                )}
              />

              </div>

              <div className="hidden min-h-0 min-w-0 flex-col lg:sticky lg:top-2 lg:flex lg:h-[calc(100dvh-5rem)] lg:max-h-[calc(100dvh-5rem)] lg:pl-6">
                <PagePreviewPanel
                  title={`${details.page.title || details.page.slug} (${previewLocale.toUpperCase()})`}
                  previewUrl={`/${previewLocale}/projects/${encodeURIComponent(details.page.slug)}?${VAULT_BUILDER_IFRAME_PREVIEW_QUERY}=1`}
                  dismissible={false}
                  toolbar={{
                    locale: previewLocale,
                    onLocaleChange: setPreviewLocale,
                    device: previewDevice,
                    onDeviceChange: setPreviewDevice,
                  }}
                  reloadEpoch={vaultPreviewReloadEpoch}
                  className="min-h-0 flex-1"
                />
              </div>
            </div>
          )}
        </section>
      </div>
      {vaultAddModuleOpen && details ? (
        <AddVaultModuleModal
          headerTitle={`Ajouter un module — ${details.page.slug}`}
          publicPreviewHref={`/${editingLocale}/projects/${encodeURIComponent(details.page.slug)}?${VAULT_BUILDER_IFRAME_PREVIEW_QUERY}=1`}
          onClose={() => setVaultAddModuleOpen(false)}
          onValidate={async (sel) => {
            addVaultModuleOfType(sel.type)
            setVaultAddModuleOpen(false)
          }}
        />
      ) : null}
      {productAddModuleOpen ? (
        <AddVaultModuleModal
          headerTitle={
            selectedProductCode
              ? `Ajouter un module — produit ${selectedProductCode}`
              : 'Ajouter un module — produit'
          }
          headerSubtitle="Les modules sont enregistrés avec la configuration bundle (Enregistrer)."
          publicPreviewHref={null}
          onClose={() => setProductAddModuleOpen(false)}
          onValidate={async (sel) => {
            addProductModuleOfType(sel.type)
            setProductAddModuleOpen(false)
          }}
        />
      ) : null}
    </div>
  )
}

export default function AdminVaultBuilderPage() {
  return (
    <Suspense fallback={<div className="p-6 text-gray-500">Chargement du Vault Builder…</div>}>
      <AdminVaultBuilderPageInner />
    </Suspense>
  )
}
