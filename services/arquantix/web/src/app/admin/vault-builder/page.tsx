'use client'

import { Suspense, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Plus, Save, Trash2, ArrowUp, ArrowDown, LayoutTemplate, Package, ChevronDown, ChevronRight } from 'lucide-react'

import { buildPackagedPutBodyFromDraft } from '@/lib/admin/packagedProductSchemas'
import { toastError, toastSuccess, toastWarning } from '@/lib/admin/toast'
import { isValidSlug, slugify } from '@/lib/utils/slugify'
import { PackagedEngineLendingSection } from '@/components/admin/PackagedEngineLendingSection'
import {
  buildProductRegistryDraft,
  PackagedProductSettingsPanel,
  type ProductRegistryDraft,
} from '@/components/admin/PackagedProductSettingsPanel'
import { MediaField } from '@/components/admin/MediaField'

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
  packagedProduct?: AdminPackagedProductView | null
}

interface ModuleCatalogItem {
  type: string
  label: string
  defaultContent: Record<string, unknown>
}

const MODULE_CATALOG: ModuleCatalogItem[] = [
  {
    type: 'TitlePage',
    label: 'Title page module',
    defaultContent: {
      title: 'Titre de section',
      subtitle: '',
      promoVideoUrl: '',
      promoVideoUrls: [],
    },
  },
  {
    type: 'SimpleMarkdownContentModule',
    label: 'Contenu simple Markdown + liens',
    defaultContent: {
      moduleTitle: 'À propos',
      markdown:
        'Utilisez ce bloc pour afficher du contenu **Markdown** avec paragraphes, listes et mise en forme.',
      links: [
        { label: 'En savoir plus', url: 'https://arquantix.com' },
      ],
    },
  },
  {
    type: 'CompetitiveAdvantagesModule',
    label: 'Competitive Advantages Module',
    defaultContent: {
      title: 'Pourquoi cette offre ?',
      rows: [
        {
          icon: 'assignment_turned_in_rounded',
          iconBackgroundColor: '#1E88E5',
          category: 'content',
          title: 'Process rigoureux',
          description: 'Une sélection stricte des opportunités avec gouvernance claire.',
        },
        {
          icon: 'insights_rounded',
          iconBackgroundColor: '#16A34A',
          category: 'success',
          title: 'Suivi data',
          description: 'Des indicateurs lisibles pour piloter la performance.',
        },
      ],
    },
  },
  {
    type: 'FaqAccordionModule',
    label: 'FAQ Accordion Module',
    defaultContent: {
      title: 'FAQ',
      footerLinkLabel: 'Voir les FAQ du projet',
      footerCollectionSlug: 'getting-started',
      footerCategorySlug: 'investing-basics',
      footerFilterLabel: '',
      items: [
        { articleSlug: 'what-is-investing' },
      ],
    },
  },
  {
    type: 'ContentBasDePageSansModuleBlanc',
    label: 'content bas de page sans module blanc',
    defaultContent: {
      markdown:
        "En participant à ce programme, vous confirmez avoir lu et accepté nos [conditions générales](https://arquantix.com).",
    },
  },
  {
    type: 'MarktingCardLargePortrait',
    label: 'MarktingCardLargePortrait',
    defaultContent: {
      title: 'Fluidifiez vos processus de travail',
      imageAssetPath: 'assets/marketing_card_large_portrait.png',
      heightSize: 'large',
    },
  },
  {
    type: 'MarketingCardsSmallCarouselModule',
    label: 'Marketing Cards Small Carousel',
    defaultContent: {
      items: [],
    },
  },
  {
    type: 'MarketingCardsSmallSlidingCarrousel_Portrait',
    label: 'Marketing Cards Small Sliding Carrousel (Portrait)',
    defaultContent: {
      title: '',
      carousel: false,
      showBullets: true,
      visibleCardsCount: 1.2,
      cardAspectRatio: '1.2:1',
      items: [
        {
          imageUrl: 'https://picsum.photos/600/800',
          redirectUrl: 'https://arquantix.com',
          title: 'Carte portrait',
          description: '',
        },
      ],
    },
  },
  {
    type: 'MarketingCardsSmallSlidingCarrousel_Paysage',
    label: 'Marketing Cards Small Sliding Carrousel (Paysage)',
    defaultContent: {
      title: '',
      carousel: false,
      showBullets: true,
      items: [
        {
          imageUrl: 'https://picsum.photos/800/600',
          redirectUrl: 'https://arquantix.com',
          title: 'Carte paysage',
          description: '',
        },
      ],
    },
  },
  {
    type: 'TransactionLatest10Module',
    label: 'Transaction Latest 10 Module',
    defaultContent: {
      title: 'Dernières transactions',
      limit: 10,
    },
  },
  {
    type: 'BlogALaUne',
    label: 'Blog A la Une',
    defaultContent: {
      title: 'À la une',
      limit: 3,
    },
  },
  {
    type: 'AllocationModule',
    label: 'Allocation (Donuts)',
    defaultContent: {
      title: 'Allocation',
      introText: 'Votre portefeuille génère des intérêts grâce à une allocation dynamique.',
      size: 'large',
      slices: [
        { label: 'Energy', percentage: 38.2, colorHex: '#374151' },
        { label: 'Real estate', percentage: 28.5, colorHex: '#6B7280' },
        { label: 'Crypto', percentage: 15.0, colorHex: '#9CA3AF' },
        { label: 'Stablecoins', percentage: 10.3, colorHex: '#D1D5DB' },
        { label: 'Equity', percentage: 5.7, colorHex: '#E5E7EB' },
        { label: 'Others', percentage: 2.3, colorHex: '#CBD5E1' },
      ],
    },
  },
  {
    type: 'KeyInformationModule',
    label: 'Key Information',
    defaultContent: {
      title: 'Infos clés',
      rows: [
        { label: 'Montant', value: '10M €', showInfoIcon: false, infoLinkArticle: '' },
        { label: 'Durée', value: '2 ans', showInfoIcon: true, infoLinkArticle: 'article-faq-duree' },
      ],
    },
  },
  {
    type: 'PerformanceChart',
    label: 'Performance Chart (Bundle)',
    defaultContent: {
      title: 'Performance',
    },
  },
  {
    type: 'StepsModule',
    label: 'Étapes / timeline (Steps)',
    defaultContent: {
      title: 'Étapes du projet',
      rightLabel: '',
      subtitle: '',
      items: [
        {
          dayLabel: 'Étape 1',
          date: '1er trimestre 2026',
          title: 'Lancement',
          description: 'Description courte de cette étape.',
          tags: ['Lancement'],
        },
        {
          dayLabel: 'Étape 2',
          date: '2e trimestre 2026',
          title: 'Déploiement',
          description: 'Suite du calendrier.',
          tags: [],
        },
      ],
    },
  },
  {
    type: 'VideoBlockArticleModule',
    label: 'Vidéos (cartes poster + lecture)',
    defaultContent: {
      title: 'Vidéos',
      items: [
        {
          title: 'Titre de la vidéo',
          posterImageUrl: 'https://picsum.photos/800/450',
          videoUrl: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
          date: '7 avril 2026',
        },
      ],
    },
  },
]

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
  const catalogItem = MODULE_CATALOG.find((item) => item.type === 'TitlePage')
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

function AdminVaultBuilderPageInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const slugFromQuery = searchParams?.get('slug') ?? null
  const eoWorkspace = searchParams?.get('eo') === '1'
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
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
  const [moduleTypeToAdd, setModuleTypeToAdd] = useState(MODULE_CATALOG[0].type)
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
  const [productModuleTypeToAdd, setProductModuleTypeToAdd] = useState(MODULE_CATALOG[0].type)

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

  const selectedModuleLabel = useMemo(
    () => MODULE_CATALOG.find((m) => m.type === moduleTypeToAdd)?.label ?? moduleTypeToAdd,
    [moduleTypeToAdd]
  )
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
      await loadDetails(nextSlug, mounted)
    } else {
      setDetails(null)
      setSelectedSlug(null)
    }
  }

  const loadDetails = async (slug: string, mounted = true) => {
    const normalizedSlug = slug?.trim().replace(/\/+$/, '') || ''
    if (!normalizedSlug) return
    const res = await fetch(`/api/admin/vaults/${normalizedSlug}`, { credentials: 'include' })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      const message = body?.error || body?.detail || `Erreur ${res.status}`
      toastError(`Détails de la page : ${message}`)
      if (mounted) {
        setDetails(null)
        setSelectedSlug(null)
      }
      return
    }
    const payload = (await res.json()) as VaultDetails
    if (!mounted) return
    setSelectedSlug(normalizedSlug)
    setDetails({
      ...payload,
      config: withConfigDefaults(payload.config),
    })
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
      await refreshVaults()
      if (payload.vault?.slug) {
        await loadDetails(payload.vault.slug)
      }
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

  const handleAddModule = () => {
    if (!details) return
    const catalogItem = MODULE_CATALOG.find((item) => item.type === moduleTypeToAdd)
    if (!catalogItem) return
    updateDetails((prev) => ({
      ...prev,
      config: {
        ...prev.config,
        modules: [
          ...prev.config.modules,
          {
            id: crypto.randomUUID(),
            type: catalogItem.type,
            enabled: true,
            content: structuredClone(catalogItem.defaultContent),
          },
        ],
      },
    }))
    toastSuccess(`Module "${selectedModuleLabel}" ajouté.`)
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

  const moveModule = (moduleId: string, direction: 'up' | 'down') => {
    if (!details) return
    const modules = [...details.config.modules]
    const index = modules.findIndex((m) => m.id === moduleId)
    if (index < 0) return
    const target = direction === 'up' ? index - 1 : index + 1
    if (target < 0 || target >= modules.length) return
    const tmp = modules[index]
    modules[index] = modules[target]
    modules[target] = tmp
    updateDetails((prev) => ({
      ...prev,
      config: { ...prev.config, modules },
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
    if (!details || !productDraft) return
    setSaving(true)
    try {
      const res = await fetch(`/api/admin/vaults/${details.page.slug}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          title: details.page.title ?? '',
          description: details.page.description ?? '',
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

      let putBody
      try {
        putBody = buildPackagedPutBodyFromDraft(productDraft)
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'Données produit packagé invalides'
        toastError(msg)
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
        toastWarning('Le contenu Vault a été enregistré, mais pas le registre produit.')
        await refreshVaults()
        return
      }

      toastSuccess('Vault et registre produit enregistrés.')
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
      await loadDetails(details.page.slug)
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Mise à jour impossible')
    } finally {
      setPackagedPublishBusy(false)
    }
  }

  const ensureRequiredProductModules = (
    modules: LandingModule[],
    product?: PortfolioProduct,
  ): LandingModule[] => {
    let result = [...modules]
    if (!result.some((m) => m.type === 'TitlePage')) {
      const catalogItem = MODULE_CATALOG.find((item) => item.type === 'TitlePage')!
      result = [
        {
          id: crypto.randomUUID(),
          type: 'TitlePage',
          enabled: true,
          content: structuredClone(catalogItem.defaultContent),
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

  const handleAddProductModule = () => {
    const catalogItem = MODULE_CATALOG.find((item) => item.type === productModuleTypeToAdd)
    if (!catalogItem) return
    setProductModules((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        type: catalogItem.type,
        enabled: true,
        content: structuredClone(catalogItem.defaultContent),
      },
    ])
    toastSuccess(`Module "${MODULE_CATALOG.find((m) => m.type === productModuleTypeToAdd)?.label ?? productModuleTypeToAdd}" ajouté.`)
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

  const moveProductModule = (moduleId: string, direction: 'up' | 'down') => {
    const modules = [...productModules]
    const index = modules.findIndex((m) => m.id === moduleId)
    if (index < 0) return
    const target = direction === 'up' ? index - 1 : index + 1
    if (target < 0 || target >= modules.length) return
    ;[modules[index], modules[target]] = [modules[target], modules[index]]
    setProductModules(modules)
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
            Créer des vaults à la demande via le builder. Template, navbar, modules et contenu dynamique.
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
                Parcours recommandé : <strong>Product Settings</strong> (registre) →{' '}
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

                      <div className="border rounded-lg p-4 space-y-4 bg-white">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <h4 className="font-semibold text-gray-900">Modules / Composants</h4>
                          <div className="flex items-center gap-2">
                            <select
                              value={productModuleTypeToAdd}
                              onChange={(e) => setProductModuleTypeToAdd(e.target.value)}
                              className="px-3 py-2 border rounded-md"
                            >
                              {MODULE_CATALOG.map((item) => (
                                <option key={item.type} value={item.type}>
                                  {item.label}
                                </option>
                              ))}
                            </select>
                            <button
                              type="button"
                              onClick={handleAddProductModule}
                              className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-indigo-200 text-indigo-700 hover:bg-indigo-50"
                            >
                              <Plus className="w-4 h-4" />
                              Ajouter
                            </button>
                          </div>
                        </div>

                        {productModules.length === 0 ? (
                          <p className="text-sm text-gray-500">
                            Aucun module. Ajoute des composants depuis la liste.
                          </p>
                        ) : (
                          <div className="space-y-3">
                            {productModules.map((module, index) => {
                              const isRequired = REQUIRED_PRODUCT_MODULE_TYPES.includes(module.type)
                              return (
                              <div key={module.id} className={`rounded-md border p-3 ${isRequired ? 'border-indigo-300 bg-indigo-50/30' : 'border-gray-200'}`}>
                                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm font-medium text-gray-900">
                                      #{index + 1} · {module.type}
                                    </span>
                                    {isRequired && (
                                      <span className="text-[10px] font-semibold uppercase tracking-wide text-indigo-600 bg-indigo-100 px-1.5 py-0.5 rounded">
                                        requis
                                      </span>
                                    )}
                                    <label className="text-xs inline-flex items-center gap-1">
                                      <input
                                        type="checkbox"
                                        checked={module.enabled}
                                        disabled={isRequired}
                                        onChange={(e) =>
                                          setProductModules((prev) =>
                                            prev.map((m) =>
                                              m.id === module.id
                                                ? { ...m, enabled: e.target.checked }
                                                : m
                                            )
                                          )
                                        }
                                      />
                                      actif
                                    </label>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <button
                                      type="button"
                                      onClick={() => moveProductModule(module.id, 'up')}
                                      className="p-1 rounded border border-gray-200 hover:bg-gray-50"
                                      title="Monter"
                                    >
                                      <ArrowUp className="w-4 h-4" />
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => moveProductModule(module.id, 'down')}
                                      className="p-1 rounded border border-gray-200 hover:bg-gray-50"
                                      title="Descendre"
                                    >
                                      <ArrowDown className="w-4 h-4" />
                                    </button>
                                    {!isRequired && (
                                    <button
                                      type="button"
                                      onClick={() => removeProductModule(module.id)}
                                      className="p-1 rounded border border-red-200 text-red-600 hover:bg-red-50"
                                      title="Supprimer"
                                    >
                                      <Trash2 className="w-4 h-4" />
                                    </button>
                                    )}
                                  </div>
                                </div>
                                <textarea
                                  defaultValue={JSON.stringify(module.content, null, 2)}
                                  onBlur={(e) =>
                                    handleUpdateProductModuleContent(module.id, e.target.value)
                                  }
                                  className="w-full min-h-[120px] p-2 border rounded-md font-mono text-xs"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                  Édite le JSON puis quitte le champ pour appliquer.
                                </p>
                              </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
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
                            onClick={() => loadDetails(row.slug)}
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
            <div className="space-y-6">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-xl font-semibold text-gray-900">
                      {details.page.title || details.page.slug}
                    </h2>
                    {productDraft?.enabled &&
                      details.packagedProduct &&
                      productDraft.productType === 'EXCLUSIVE_OFFER' && (
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            productDraft.commercialStatus === 'PUBLISHED'
                              ? 'bg-green-100 text-green-700'
                              : productDraft.commercialStatus === 'ARCHIVED'
                                ? 'bg-gray-200 text-gray-600'
                                : 'bg-gray-100 text-gray-500'
                          }`}
                        >
                          {productDraft.commercialStatus === 'PUBLISHED'
                            ? 'Publié'
                            : productDraft.commercialStatus === 'ARCHIVED'
                              ? 'Archivé'
                              : 'Brouillon'}
                        </span>
                      )}
                  </div>
                  <p className="text-sm text-gray-500 font-mono">{details.page.urlPath}</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {productDraft?.enabled &&
                    details.packagedProduct &&
                    productDraft.productType === 'EXCLUSIVE_OFFER' && (
                      <button
                        type="button"
                        onClick={handleToggleExclusiveOfferCatalogPublish}
                        disabled={packagedPublishBusy || saving}
                        className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium border ${
                          productDraft.commercialStatus === 'PUBLISHED'
                            ? 'border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100'
                            : 'border-green-300 bg-green-50 text-green-700 hover:bg-green-100'
                        } disabled:opacity-50`}
                      >
                        {packagedPublishBusy
                          ? '…'
                          : productDraft.commercialStatus === 'PUBLISHED'
                            ? 'Dépublier'
                            : productDraft.commercialStatus === 'ARCHIVED'
                              ? 'Republier'
                              : 'Publier'}
                      </button>
                    )}
                  <button
                    type="button"
                    onClick={handleDeletePage}
                    disabled={deleting}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4" />
                    Supprimer
                  </button>
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={saving || packagedPublishBusy}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <Save className="w-4 h-4" />
                    {saving ? 'Sauvegarde…' : 'Enregistrer'}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input
                  value={details.page.title ?? ''}
                  onChange={(e) =>
                    updateDetails((prev) => ({
                      ...prev,
                      page: { ...prev.page, title: e.target.value },
                    }))
                  }
                  placeholder="Titre page (admin)"
                  className="px-3 py-2 border rounded-md"
                />
                <input
                  value={details.page.description ?? ''}
                  onChange={(e) =>
                    updateDetails((prev) => ({
                      ...prev,
                      page: { ...prev.page, description: e.target.value },
                    }))
                  }
                  placeholder="Description page"
                  className="px-3 py-2 border rounded-md"
                />
              </div>

              {productDraft && (
                <PackagedProductSettingsPanel
                  draft={productDraft}
                  onChange={setProductDraft}
                  serverLinked={Boolean(details.packagedProduct)}
                  lendingEngineLinked={Boolean(details.packagedProduct?.lendingEngineLinked)}
                />
              )}

              <PackagedEngineLendingSection
                packagedProductId={details.packagedProduct?.id ?? null}
                productType={
                  productDraft?.productType ?? details.packagedProduct?.productType ?? 'VAULT_SIMPLE'
                }
                hasPackagedRow={Boolean(details.packagedProduct)}
                onRefresh={async () => {
                  if (selectedSlug) await loadDetails(selectedSlug)
                }}
              />

              <div className="border rounded-lg p-4 space-y-4">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <LayoutTemplate className="w-4 h-4" />
                  Template + Navbar + Title page
                </h3>

                <div>
                  <label className="block text-sm font-medium mb-1">Catégorie (Investment Type)</label>
                  <select
                    value={details.config.investmentTypeSlug ?? ''}
                    onChange={(e) =>
                      updateDetails((prev) => ({
                        ...prev,
                        config: {
                          ...prev.config,
                          investmentTypeSlug: e.target.value || undefined,
                        },
                      }))
                    }
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="">— Aucune —</option>
                    {investmentTypes.map((t) => (
                      <option key={t.id} value={t.slug}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Template de page</label>
                  <select
                    value={details.config.templateKey}
                    onChange={(e) =>
                      updateDetails((prev) => ({
                        ...prev,
                        config: { ...prev.config, templateKey: e.target.value as TemplateKey },
                      }))
                    }
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="PageSimpleNavBarTopTitlePageContent">
                      PageSimpleNavBarTopTitlePageContent
                    </option>
                    <option value="ModaleFullHeightPage">ModaleFullHeightPage</option>
                    <option value="DashboardScrollTemplate">DashboardScrollTemplate</option>
                  </select>
                </div>

                <div>
                  <MediaField
                    label="Image média (header)"
                    value={details.config.headerMediaId ?? null}
                    onChange={(mediaId) =>
                      updateDetails((prev) => ({
                        ...prev,
                        config: { ...prev.config, headerMediaId: mediaId ?? undefined },
                      }))
                    }
                  />
                </div>

                {(productDraft?.productType === 'EXCLUSIVE_OFFER' ||
                  details.packagedProduct?.productType === 'EXCLUSIVE_OFFER') && (
                  <div className="rounded-lg border border-violet-200 bg-violet-50/60 p-4 space-y-3">
                    <div>
                      <h4 className="font-semibold text-gray-900">Vidéo promo (optionnel)</h4>
                      <p className="text-xs text-gray-600 mt-1">
                        Comme l&apos;image de header, mais pour une vidéo : si une URL est renseignée, l&apos;app
                        affiche un bouton lecture sur le hero et ouvre la vidéo (navigateur / lecteur). Stockée
                        dans le module <strong>TitlePage</strong> (<code className="text-[11px]">promoVideoUrl</code>
                        ).
                      </p>
                    </div>
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
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-sm font-medium mb-1">Navbar gauche (icône)</label>
                    <select
                      value={details.config.navbar.leftIconType}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            navbar: {
                              ...prev.config.navbar,
                              leftIconType: e.target.value as LeftIconType,
                            },
                          },
                        }))
                      }
                      className="w-full px-3 py-2 border rounded-md"
                    >
                      <option value="none">Aucune</option>
                      <option value="back">Back</option>
                      <option value="close">Close</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Redirect gauche</label>
                    <select
                      value={details.config.navbar.leftRedirectType}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            navbar: {
                              ...prev.config.navbar,
                              leftRedirectType: e.target.value as Exclude<RedirectType, 'none'>,
                            },
                          },
                        }))
                      }
                      className="w-full px-3 py-2 border rounded-md"
                    >
                      <option value="back">back</option>
                      <option value="close">close</option>
                      <option value="internal">internal</option>
                      <option value="external">external</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Target gauche</label>
                    <input
                      value={details.config.navbar.leftTarget ?? ''}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            navbar: {
                              ...prev.config.navbar,
                              leftTarget: e.target.value,
                            },
                          },
                        }))
                      }
                      placeholder="/offers ou https://..."
                      className="w-full px-3 py-2 border rounded-md"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-sm font-medium mb-1">Navbar droite (icône)</label>
                    <select
                      value={details.config.navbar.rightAction.icon}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            navbar: {
                              ...prev.config.navbar,
                              rightAction: {
                                ...prev.config.navbar.rightAction,
                                icon: e.target.value as RightIconType,
                              },
                            },
                          },
                        }))
                      }
                      className="w-full px-3 py-2 border rounded-md"
                    >
                      <option value="none">Aucune</option>
                      <option value="favorite">favorite</option>
                      <option value="share">share</option>
                      <option value="notifications">notifications</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Redirect droite</label>
                    <select
                      value={details.config.navbar.rightAction.redirectType}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            navbar: {
                              ...prev.config.navbar,
                              rightAction: {
                                ...prev.config.navbar.rightAction,
                                redirectType: e.target.value as RedirectType,
                              },
                            },
                          },
                        }))
                      }
                      className="w-full px-3 py-2 border rounded-md"
                    >
                      <option value="none">none</option>
                      <option value="back">back</option>
                      <option value="close">close</option>
                      <option value="internal">internal</option>
                      <option value="external">external</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Target droite</label>
                    <input
                      value={details.config.navbar.rightAction.target ?? ''}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            navbar: {
                              ...prev.config.navbar,
                              rightAction: {
                                ...prev.config.navbar.rightAction,
                                target: e.target.value,
                              },
                            },
                          },
                        }))
                      }
                      placeholder="/profile ou https://..."
                      className="w-full px-3 py-2 border rounded-md"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[160px_1fr] gap-3">
                  <label className="inline-flex items-center gap-2 text-sm font-medium">
                    <input
                      type="checkbox"
                      checked={details.config.pageTitle.enabled}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            pageTitle: {
                              ...prev.config.pageTitle,
                              enabled: e.target.checked,
                            },
                          },
                        }))
                      }
                    />
                    Title page actif
                  </label>
                  <input
                    value={details.config.pageTitle.text}
                    onChange={(e) =>
                      updateDetails((prev) => ({
                        ...prev,
                        config: {
                          ...prev.config,
                          pageTitle: {
                            ...prev.config.pageTitle,
                            text: e.target.value,
                          },
                        },
                      }))
                    }
                    placeholder="Texte Title page"
                    className="px-3 py-2 border rounded-md"
                  />
                </div>

                <div className="border rounded-md p-3 space-y-3">
                  <label className="inline-flex items-center gap-2 text-sm font-medium">
                    <input
                      type="checkbox"
                      checked={details.config.fixedBottomCta.enabled}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            fixedBottomCta: {
                              ...prev.config.fixedBottomCta,
                              enabled: e.target.checked,
                            },
                          },
                        }))
                      }
                    />
                    Bouton fixe bas de page (gradient + blur)
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <input
                      value={details.config.fixedBottomCta.label}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            fixedBottomCta: {
                              ...prev.config.fixedBottomCta,
                              label: e.target.value,
                            },
                          },
                        }))
                      }
                      placeholder="Label bouton CTA"
                      className="px-3 py-2 border rounded-md"
                    />
                    <select
                      value={details.config.fixedBottomCta.redirectType}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            fixedBottomCta: {
                              ...prev.config.fixedBottomCta,
                              redirectType: e.target.value as RedirectType,
                            },
                          },
                        }))
                      }
                      className="px-3 py-2 border rounded-md"
                    >
                      <option value="none">none</option>
                      <option value="back">back</option>
                      <option value="close">close</option>
                      <option value="internal">internal</option>
                      <option value="external">external</option>
                    </select>
                    <input
                      value={details.config.fixedBottomCta.target ?? ''}
                      onChange={(e) =>
                        updateDetails((prev) => ({
                          ...prev,
                          config: {
                            ...prev.config,
                            fixedBottomCta: {
                              ...prev.config.fixedBottomCta,
                              target: e.target.value,
                            },
                          },
                        }))
                      }
                      placeholder="/route ou https://..."
                      className="px-3 py-2 border rounded-md"
                    />
                  </div>
                </div>
              </div>

              <div className="border rounded-lg p-4 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="font-semibold text-gray-900">Modules / Composants</h3>
                  <div className="flex items-center gap-2">
                    <select
                      value={moduleTypeToAdd}
                      onChange={(e) => setModuleTypeToAdd(e.target.value)}
                      className="px-3 py-2 border rounded-md"
                    >
                      {MODULE_CATALOG.map((item) => (
                        <option key={item.type} value={item.type}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={handleAddModule}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-indigo-200 text-indigo-700 hover:bg-indigo-50"
                    >
                      <Plus className="w-4 h-4" />
                      Ajouter
                    </button>
                  </div>
                </div>

                {details.config.modules.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    Aucun module sélectionné. Ajoute des composants depuis la liste.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {details.config.modules.map((module, index) => (
                      <div key={module.id} className="rounded-md border border-gray-200 p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900">
                              #{index + 1} · {module.type}
                            </span>
                            <label className="text-xs inline-flex items-center gap-1">
                              <input
                                type="checkbox"
                                checked={module.enabled}
                                onChange={(e) =>
                                  updateDetails((prev) => ({
                                    ...prev,
                                    config: {
                                      ...prev.config,
                                      modules: prev.config.modules.map((m) =>
                                        m.id === module.id ? { ...m, enabled: e.target.checked } : m
                                      ),
                                    },
                                  }))
                                }
                              />
                              actif
                            </label>
                          </div>
                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              onClick={() => moveModule(module.id, 'up')}
                              className="p-1 rounded border border-gray-200 hover:bg-gray-50"
                              title="Monter"
                            >
                              <ArrowUp className="w-4 h-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => moveModule(module.id, 'down')}
                              className="p-1 rounded border border-gray-200 hover:bg-gray-50"
                              title="Descendre"
                            >
                              <ArrowDown className="w-4 h-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => removeModule(module.id)}
                              className="p-1 rounded border border-red-200 text-red-600 hover:bg-red-50"
                              title="Supprimer"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                        <textarea
                          defaultValue={JSON.stringify(module.content, null, 2)}
                          onBlur={(e) => handleUpdateModuleContent(module.id, e.target.value)}
                          className="w-full min-h-[160px] p-2 border rounded-md font-mono text-xs"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Édite le JSON puis quitte le champ pour appliquer.
                        </p>
                        {module.type === 'CompetitiveAdvantagesModule' && (
                          <p className="text-xs text-gray-500 mt-2">
                            Options pour la catégorie (par row) : content (blanc, comportement actuel) ; work (jaune clair #FEF9C3) ; note (bleu clair #DBEAFE) ; success (vert clair #D1FAE5) ; danger (rouge clair #FEE2E2).
                          </p>
                        )}
                        {(module.type === 'MarketingCardsSmallSlidingCarrousel_Portrait' ||
                          module.type === 'MarketingCardsSmallSlidingCarrousel_Paysage') && (
                          <p className="text-xs text-gray-500 mt-2">
                            Options de taille des cartes : `visibleCardsCount` (ex: 1, 1.2, 1.5, 1.8; virgule acceptee) et `cardAspectRatio` au format largeur:hauteur (ex: 1:1, 1:4, 3:4, 1:1.4).
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
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
