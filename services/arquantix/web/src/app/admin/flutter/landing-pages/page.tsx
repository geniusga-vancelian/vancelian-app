'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Plus, Save, Trash2, ArrowUp, ArrowDown, LayoutTemplate } from 'lucide-react'

import { toastError, toastSuccess } from '@/lib/admin/toast'
import { isValidSlug, slugify } from '@/lib/utils/slugify'

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

interface LandingPageRow {
  id: string
  slug: string
  title: string | null
  description: string | null
  urlPath: string
  configSummary: {
    templateKey: string | null
    modulesCount: number
  }
}

interface LandingPageDetails {
  page: {
    id: string
    slug: string
    title: string | null
    description: string | null
    urlPath: string
  }
  config: LandingConfig
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
      introText: 'Répartition du portefeuille',
      size: 'large',
      slices: [
        { label: 'Actions', percentage: 60, colorHex: '#1E88E5' },
        { label: 'Obligations', percentage: 30, colorHex: '#16A34A' },
        { label: 'Liquidités', percentage: 10, colorHex: '#F59E0B' },
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
})

export default function AdminFlutterLandingPagesBuilderPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [pages, setPages] = useState<LandingPageRow[]>([])
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [details, setDetails] = useState<LandingPageDetails | null>(null)
  const [newSlug, setNewSlug] = useState('')
  const [newTitle, setNewTitle] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [createError, setCreateError] = useState<string | null>(null)
  const [moduleTypeToAdd, setModuleTypeToAdd] = useState(MODULE_CATALOG[0].type)

  const selectedModuleLabel = useMemo(
    () => MODULE_CATALOG.find((m) => m.type === moduleTypeToAdd)?.label ?? moduleTypeToAdd,
    [moduleTypeToAdd]
  )
  const normalizedNewSlug = useMemo(() => slugify(newSlug.trim()), [newSlug])

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
        await refreshPages(mounted)
      } catch {
        toastError('Impossible de charger le builder landing pages.')
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [router])

  const refreshPages = async (mounted = true) => {
    const res = await fetch('/api/admin/landing-pages', { credentials: 'include' })
    if (!res.ok) {
      throw new Error('Failed to fetch landing pages')
    }
    const payload = await res.json()
    const rows = (payload.pages ?? []) as LandingPageRow[]
    if (!mounted) return
    setPages(rows)
    const nextSlug = selectedSlug ?? rows[0]?.slug ?? null
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
    const res = await fetch(`/api/admin/landing-pages/${normalizedSlug}`, { credentials: 'include' })
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
    const payload = (await res.json()) as LandingPageDetails
    if (!mounted) return
    setSelectedSlug(normalizedSlug)
    setDetails({
      ...payload,
      config: withConfigDefaults(payload.config),
    })
  }

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
      const res = await fetch('/api/admin/landing-pages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          slug,
          title: newTitle.trim() || undefined,
          description: newDescription.trim() || undefined,
          config: DEFAULT_CONFIG,
        }),
      })
      const payload = await res.json()
      if (!res.ok) {
        const issues = Array.isArray(payload.issues)
          ? payload.issues.map((i: any) => i?.message).filter(Boolean).join(', ')
          : ''
        throw new Error(issues || payload.error || 'Création impossible')
      }
      toastSuccess('Landing page créée.')
      setNewSlug('')
      setNewTitle('')
      setNewDescription('')
      await refreshPages()
      if (payload.page?.slug) {
        await loadDetails(payload.page.slug)
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
    if (!window.confirm(`Supprimer la landing page "${selectedSlug}" ?`)) return
    setDeleting(true)
    try {
      const res = await fetch(`/api/admin/landing-pages/${selectedSlug}`, {
        method: 'DELETE',
        credentials: 'include',
      })
      const payload = await res.json()
      if (!res.ok) {
        throw new Error(payload.error || 'Suppression impossible')
      }
      toastSuccess('Landing page supprimée.')
      setSelectedSlug(null)
      setDetails(null)
      await refreshPages()
    } catch (e: any) {
      toastError(e?.message || 'Suppression impossible')
    } finally {
      setDeleting(false)
    }
  }

  const updateDetails = (updater: (prev: LandingPageDetails) => LandingPageDetails) => {
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
      const parsed = JSON.parse(raw) as Record<string, unknown>
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
      // Keep UX permissive; user can continue typing invalid JSON.
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

  const handleSave = async () => {
    if (!details) return
    setSaving(true)
    try {
      const res = await fetch(`/api/admin/landing-pages/${details.page.slug}`, {
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
      toastSuccess('Landing page enregistrée.')
      await refreshPages()
    } catch (e: any) {
      toastError(e?.message || 'Sauvegarde impossible')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="p-6 text-gray-500">Chargement du builder landing pages…</div>
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Landing Pages Builder</h1>
          <p className="text-gray-600 mt-1">
            Template page, navbar, Title page, modules/composants et contenu dynamique.
          </p>
        </div>
        <Link
          href="/admin/flutter"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Retour à Flutter
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow border border-gray-100 p-4">
        <h2 className="text-lg font-semibold mb-3">Créer une landing page</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
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

      <div className="grid grid-cols-1 xl:grid-cols-[320px_1fr] gap-6">
        <aside className="bg-white rounded-lg shadow border border-gray-100 p-4">
          <h3 className="text-base font-semibold mb-3">Pages créées</h3>
          {pages.length === 0 ? (
            <p className="text-sm text-gray-500">Aucune landing page.</p>
          ) : (
            <ul className="space-y-2">
              {pages.map((row) => {
                const active = row.slug === selectedSlug
                return (
                  <li key={row.id}>
                    <button
                      type="button"
                      onClick={() => loadDetails(row.slug)}
                      className={`w-full text-left rounded-md border px-3 py-2 ${
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
          )}
        </aside>

        <section className="bg-white rounded-lg shadow border border-gray-100 p-5">
          {!details ? (
            <p className="text-gray-500">Sélectionne une page pour l’éditer.</p>
          ) : (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    {details.page.title || details.page.slug}
                  </h2>
                  <p className="text-sm text-gray-500 font-mono">{details.page.urlPath}</p>
                </div>
                <div className="flex items-center gap-2">
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
                    disabled={saving}
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

              <div className="border rounded-lg p-4 space-y-4">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <LayoutTemplate className="w-4 h-4" />
                  Template + Navbar + Title page
                </h3>

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
