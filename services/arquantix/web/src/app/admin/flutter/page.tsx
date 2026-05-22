'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  LayoutGrid,
  Box,
  Layers,
  FileJson,
  ChevronRight,
  GitBranch,
} from 'lucide-react'

import { DeviceFrame } from '@/components/admin/flutter-preview/DeviceFrame'

interface DsComponent {
  id: string
  slug: string
  name: string
  schemaJson: Record<string, unknown>
  createdAt: string
}

interface DsChapter {
  id: string
  name: string
  slug: string
  order: number
  components: DsComponent[]
}

interface AppTreeNode {
  id: string
  label: string
  kind: 'page' | 'subpage' | 'module'
  to?: string
  children?: AppTreeNode[]
}

const LAYOUTS = [
  { name: 'Dashboard principal', description: 'Navbar top + header (balance, line chart, boutons) + body widgets (My account, Exclusive offers, News à la Une).', doc: 'DashboardScrollTemplate' },
  { name: 'Offers', description: 'Page Offres: widget Saving Vaults (Widget Builder), catégories investissement et liste offres.', doc: 'OffersScreen' },
  { name: 'Compte Euro', description: 'Template dashboard niveau 2: bouton retour en navbar, header balance/actions, modules body pilotés par JSON.', doc: 'EuroAccountTemplate' },
  { name: 'All transactions', description: 'Header avec back + titre centré, onglets mois (filtre), puis liste des transactions du mois sélectionné.', doc: 'AllTransactionsTemplate' },
  { name: 'Transaction details', description: 'Header back + titre centré, identité transaction, actions (status/statement), détails et recap tile.', doc: 'TransactionDetailTemplate' },
  { name: 'Homepage', description: 'Hero, sections, carousels (offres, news).', doc: 'HomeScreen' },
  { name: 'Page projet (offre exclusive)', description: 'Image 60 %, header avec boutons, body avec modules (key data, FAQ, allocation).', doc: 'ExclusiveOfferDetailScreen' },
  { name: 'Page article / blog', description: 'Header, contenu article avec blocs (texte, médias).', doc: 'ArticleDetailScreen' },
]

const APP_ARBORESCENCE: AppTreeNode[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    kind: 'page',
    to: '/admin/flutter/layouts/DashboardScrollTemplate',
    children: [
      { id: 'dashboard-navbar', label: 'Navbar (top)', kind: 'subpage' },
      { id: 'dashboard-header', label: 'Header: Balance + Line chart + Buttons', kind: 'subpage' },
      {
        id: 'dashboard-body',
        label: 'Body content',
        kind: 'subpage',
        children: [
          { id: 'dashboard-widget-account', label: 'Widget: My account', kind: 'module' },
          { id: 'dashboard-widget-exclusive', label: 'Widget: Exclusive offers', kind: 'module' },
          { id: 'dashboard-widget-news', label: 'Widget: News à la Une (10 dernières news DB)', kind: 'module' },
          { id: 'dashboard-widget-news-analysis', label: 'Widget: News Analyses (type ANALYSIS)', kind: 'module' },
        ],
      },
    ],
  },
  {
    id: 'offers',
    label: 'Offers',
    kind: 'page',
    to: '/admin/flutter/layouts/OffersScreen',
    children: [
      { id: 'offers-widget-saving-vaults', label: 'Widget: Saving Vaults (Widget Builder slug)', kind: 'module' },
      { id: 'offers-categories', label: 'Module: catégories d’investissement', kind: 'module' },
      { id: 'offers-exclusive', label: 'Module: top exclusive offers', kind: 'module' },
    ],
  },
  {
    id: 'all-transactions',
    label: 'All transactions',
    kind: 'page',
    to: '/admin/flutter/layouts/AllTransactionsTemplate',
    children: [
      { id: 'all-transactions-header', label: 'Header: back + title centered', kind: 'subpage' },
      { id: 'all-transactions-tabs', label: 'Tabs: months (filter)', kind: 'subpage' },
      { id: 'all-transactions-body', label: 'Body: transactions list by selected month', kind: 'subpage' },
    ],
  },
  {
    id: 'euro-account',
    label: 'Compte Euro',
    kind: 'page',
    to: '/admin/flutter/layouts/EuroAccountTemplate',
    children: [
      { id: 'euro-account-navbar', label: 'Navbar: back (gauche) + actions (droite)', kind: 'subpage' },
      { id: 'euro-account-header', label: 'Header: balance + boutons d’action', kind: 'subpage' },
      {
        id: 'euro-account-body',
        label: 'Body modules (ordre DB)',
        kind: 'subpage',
        children: [
          { id: 'euro-account-marketing', label: 'Widget: Marketing cards small carousel', kind: 'module' },
          { id: 'euro-account-transactions', label: 'Module: Transaction latest 10', kind: 'module' },
        ],
      },
    ],
  },
  {
    id: 'transaction-detail',
    label: 'Transaction details',
    kind: 'page',
    to: '/admin/flutter/layouts/TransactionDetailTemplate',
    children: [
      { id: 'transaction-detail-header', label: 'Header: back + centered title', kind: 'subpage' },
      { id: 'transaction-detail-identity', label: 'Identity: avatar + merchant + datetime + category', kind: 'subpage' },
      { id: 'transaction-detail-actions', label: 'Actions: status + statement', kind: 'subpage' },
      { id: 'transaction-detail-details-card', label: 'Details card: key/value rows', kind: 'subpage' },
      { id: 'transaction-detail-recap', label: 'Recap: transaction tile', kind: 'subpage' },
    ],
  },
  {
    id: 'home',
    label: 'Homepage',
    kind: 'page',
    to: '/admin/flutter/layouts/HomeScreen',
    children: [
      { id: 'news-a-la-une', label: 'Module blog_a_la_une', kind: 'module' },
      { id: 'offers-carousel', label: 'Module offres exclusives', kind: 'module' },
    ],
  },
  {
    id: 'projet',
    label: 'Page projet',
    kind: 'page',
    to: '/admin/flutter/layouts/ExclusiveOfferDetailScreen',
    children: [
      {
        id: 'projet-modules',
        label: 'Sous-page: modules projet',
        kind: 'subpage',
        children: [
          { id: 'module-table-info', label: 'Widget: Table information', kind: 'module' },
          { id: 'module-competitive-advantages', label: 'Widget: Competitive advantages', kind: 'module' },
          { id: 'module-steps-date', label: 'Widget: Steps date (project milestones dynamiques)', kind: 'module' },
          { id: 'module-faq', label: 'FAQ', kind: 'module' },
          { id: 'module-allocation', label: 'Portfolio allocation', kind: 'module' },
          { id: 'module-project-news', label: 'Project news (articles liés)', kind: 'module' },
        ],
      },
    ],
  },
  {
    id: 'article',
    label: 'Page article / blog',
    kind: 'page',
    to: '/admin/flutter/layouts/ArticleDetailScreen',
    children: [
      { id: 'article-body', label: 'Sous-page: contenu article', kind: 'subpage' },
      { id: 'article-media', label: 'Bloc media', kind: 'module' },
    ],
  },
]

const getExpandableNodeIds = (nodes: AppTreeNode[]): string[] => {
  const ids: string[] = []
  const walk = (list: AppTreeNode[]) => {
    list.forEach((node) => {
      if (node.children?.length) {
        ids.push(node.id)
        walk(node.children)
      }
    })
  }
  walk(nodes)
  return ids
}

const ROOT_EXPANDED_NODE_IDS = APP_ARBORESCENCE.filter((n) => n.children?.length).map((n) => n.id)
const ALL_EXPANDABLE_NODE_IDS = getExpandableNodeIds(APP_ARBORESCENCE)

export default function AdminFlutterPage() {
  const router = useRouter()
  const [chapters, setChapters] = useState<DsChapter[]>([])
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState<string | null>(null)
  const [expandedNodeIds, setExpandedNodeIds] = useState<string[]>(ROOT_EXPANDED_NODE_IDS)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const previewSrc = useMemo(
    () => (selectedNodeId ? `/admin/flutter/preview/${selectedNodeId}` : null),
    [selectedNodeId],
  )

  const toggleNode = (id: string) => {
    setExpandedNodeIds((prev) =>
      prev.includes(id) ? prev.filter((nodeId) => nodeId !== id) : [...prev, id]
    )
  }

  const renderNode = (node: AppTreeNode, depth = 0) => {
    const hasChildren = Boolean(node.children?.length)
    const isExpanded = expandedNodeIds.includes(node.id)
    const isSelected = selectedNodeId === node.id
    const kindLabel =
      node.kind === 'page'
        ? 'Page'
        : node.kind === 'subpage'
          ? 'Sous-page'
          : 'Module'

    return (
      <li key={node.id}>
        <div
          className={`flex items-center justify-between gap-4 py-2 px-3 rounded transition-colors ${
            isSelected
              ? 'bg-indigo-50 border border-indigo-300 ring-1 ring-indigo-200'
              : 'border border-transparent hover:bg-indigo-50/70'
          }`}
          style={{ marginLeft: `${depth * 18}px` }}
        >
          <button
            type="button"
            onClick={() => setSelectedNodeId(node.id)}
            className="min-w-0 flex items-center gap-2 flex-1 text-left cursor-pointer"
            aria-pressed={isSelected}
          >
            {hasChildren ? (
              <span
                role="button"
                tabIndex={0}
                onClick={(e) => {
                  e.stopPropagation()
                  toggleNode(node.id)
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    e.stopPropagation()
                    toggleNode(node.id)
                  }
                }}
                aria-label={isExpanded ? 'Replier la branche' : 'Déplier la branche'}
                className="inline-flex items-center justify-center w-5 h-5 rounded hover:bg-indigo-100 text-gray-500"
              >
                <ChevronRight
                  className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                  aria-hidden
                />
              </span>
            ) : (
              <span className="w-5 h-5" />
            )}
            <span className={`font-medium ${isSelected ? 'text-indigo-900' : 'text-gray-900'}`}>
              {node.label}
            </span>
            <span className="text-xs text-gray-500 ml-2">[{kindLabel}]</span>
          </button>
          {node.to ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                router.push(node.to!)
              }}
              className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800"
            >
              Voir JSON
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : null}
        </div>
        {hasChildren && isExpanded ? (
          <ul className="border-l border-gray-200 ml-2">
            {(node.children ?? []).map((child) => renderNode(child, depth + 1))}
          </ul>
        ) : null}
      </li>
    )
  }

  useEffect(() => {
    setApiError(null)
    fetch('/api/admin/me', { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => {
        if (!data?.user) {
          router.push('/admin/login')
          return undefined
        }
        return fetch('/api/admin/ds-components', { credentials: 'include' })
      })
      .then((res) => {
        if (!res) return undefined
        if (!res.ok) {
          if (res.status === 401) setApiError('Session expirée ou non autorisée. Reconnectez-vous.')
          else setApiError('Impossible de charger les composants.')
          return { chapters: [] }
        }
        return res.json()
      })
      .then((data) => {
        if (data) setChapters(data.chapters ?? [])
      })
      .catch(() => {
        setApiError('Erreur réseau. Vérifiez la console.')
        setChapters([])
      })
      .finally(() => setLoading(false))
  }, [router])

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Flutter</h1>
      <p className="text-gray-600 mb-8">
        Layouts de page, composants Design System et widgets (composants + données dynamiques en base).
      </p>
      <div className="mb-8 flex flex-wrap items-center gap-3">
        <Link
          href="/admin/flutter/landing-pages"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700"
        >
          <LayoutGrid className="w-4 h-4" />
          Builder Landing Pages
        </Link>
        <Link
          href="/admin/flutter/shell"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-indigo-200 text-indigo-700 hover:bg-indigo-50"
        >
          <Layers className="w-4 h-4" />
          App — Tabs principaux
        </Link>
        <Link
          href="/admin/widget-builder"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-indigo-200 text-indigo-700 hover:bg-indigo-50"
        >
          <Layers className="w-4 h-4" />
          Widget Builder
        </Link>
      </div>

      {apiError && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
          {apiError}
        </div>
      )}

      {/* Layouts de page — liste ligne par ligne */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <LayoutGrid className="w-5 h-5 text-indigo-600" />
          Layouts de page
        </h2>
        <p className="text-gray-600 mb-4 text-sm">
          Structures d’écran réutilisables dans l’app Flutter (template, header, body).
        </p>
        <ul className="bg-white rounded-lg shadow border border-gray-100 divide-y divide-gray-100 overflow-hidden">
          {LAYOUTS.map((layout) => (
            <li key={layout.name}>
              <button
                type="button"
                onClick={() => router.push(`/admin/flutter/layouts/${layout.doc}`)}
                className="w-full px-4 py-3 flex items-center justify-between gap-4 text-left hover:bg-indigo-50/70 transition-colors cursor-pointer"
              >
                <div className="min-w-0">
                  <span className="font-medium text-gray-900">{layout.name}</span>
                  <span className="text-gray-500 text-sm ml-2">— {layout.description}</span>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400 shrink-0" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      </section>

      {/* Composants existants (DS) — liste ligne par ligne */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Box className="w-5 h-5 text-indigo-600" />
          Composants existants
        </h2>
        <p className="text-gray-600 mb-4 text-sm">
          Composants Design System enregistrés en base. Chaque composant a un schéma JSON pour l’utiliser dans les pages.
        </p>
        {loading ? (
          <div className="bg-white rounded-lg shadow border border-gray-100 p-6 text-gray-500">Chargement…</div>
        ) : (() => {
          const flat: { comp: DsComponent; chapterName: string }[] = []
          chapters.forEach((ch) => {
            ch.components.forEach((comp) => flat.push({ comp, chapterName: ch.name }))
          })
          if (flat.length === 0) {
            return (
              <div className="bg-white rounded-lg shadow border border-gray-100 p-6 text-gray-500">
                Aucun composant. Exécutez <code className="bg-gray-100 px-1 rounded">npm run db:seed-ds-components</code> (et vérifiez que vous êtes connecté à l’admin).
              </div>
            )
          }
          return (
            <ul className="bg-white rounded-lg shadow border border-gray-100 divide-y divide-gray-100 overflow-hidden">
              {flat.map(({ comp, chapterName }) => (
                <li key={comp.id}>
                  <button
                    type="button"
                    onClick={() => router.push(`/admin/flutter/widgets/${comp.id}`)}
                    className="w-full px-4 py-3 flex items-center justify-between gap-4 text-left hover:bg-indigo-50/70 transition-colors cursor-pointer"
                  >
                    <span className="flex items-center gap-3 min-w-0">
                      <FileJson className="w-4 h-4 text-indigo-600 shrink-0" />
                      <span className="font-medium text-gray-900">{comp.name}</span>
                      <span className="text-gray-500 text-sm">({comp.slug})</span>
                      <span className="text-gray-400">·</span>
                      <span className="text-gray-600 text-sm">{chapterName}</span>
                    </span>
                    <ChevronRight className="w-5 h-5 text-gray-400 shrink-0" aria-hidden />
                  </button>
                </li>
              ))}
            </ul>
          )
        })()}
      </section>

      {/* Widgets — liste ligne par ligne, cliquable vers le détail (modèle JSON) */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-600" />
          Widgets
        </h2>
        <p className="text-gray-600 mb-4 text-sm">
          Liste des widgets (composants en base). Cliquez sur une ligne pour afficher le modèle JSON du module.
        </p>
        {loading ? (
          <div className="bg-white rounded-lg shadow border border-gray-100 p-6 text-gray-500">Chargement…</div>
        ) : (() => {
          const flatWidgets: { component: DsComponent; chapterName: string }[] = []
          chapters.forEach((ch) => {
            ch.components.forEach((comp) => {
              const schemaType = (comp.schemaJson as { type?: string })?.type
              if (schemaType === 'layout') return
              flatWidgets.push({ component: comp, chapterName: ch.name })
            })
          })
          const preferredOrder = ['my_account', 'news_a_la_une', 'news_analysis', 'exclusive_offers', 'marketing_cards']
          flatWidgets.sort((a, b) => {
            const ai = preferredOrder.indexOf(a.component.slug)
            const bi = preferredOrder.indexOf(b.component.slug)
            const aw = ai === -1 ? Number.MAX_SAFE_INTEGER : ai
            const bw = bi === -1 ? Number.MAX_SAFE_INTEGER : bi
            if (aw !== bw) return aw - bw
            return a.component.name.localeCompare(b.component.name)
          })
          if (flatWidgets.length === 0) {
            return (
              <div className="bg-white rounded-lg shadow border border-gray-100 p-6 text-gray-500">
                Aucun widget. Exécutez <code className="bg-gray-100 px-1 rounded">npm run db:seed-ds-components</code> (et vérifiez que vous êtes connecté à l’admin).
              </div>
            )
          }
          return (
            <ul className="bg-white rounded-lg shadow border border-gray-100 divide-y divide-gray-100 overflow-hidden">
              {flatWidgets.map(({ component, chapterName }) => (
                <li
                  key={component.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => router.push(`/admin/flutter/widgets/${component.id}`)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      router.push(`/admin/flutter/widgets/${component.id}`)
                    }
                  }}
                  className="px-4 py-3 flex items-center justify-between gap-4 cursor-pointer hover:bg-indigo-50/70 transition-colors"
                >
                  <span className="font-medium text-gray-900">{component.name}</span>
                  <span className="text-gray-500 text-sm">({component.slug})</span>
                  <span className="text-gray-400">·</span>
                  <span className="text-gray-600 text-sm">{chapterName}</span>
                  <ChevronRight className="w-5 h-5 text-gray-400 shrink-0" aria-hidden />
                </li>
              ))}
            </ul>
          )
        })()}
      </section>

      {/* Arborescence + preview DS Flutter en split */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-indigo-600" />
          Arborescence de l’application
        </h2>
        <p className="text-gray-600 mb-4 text-sm">
          Vue en arbre d’exécution: pages niveau 1, puis sous-pages, puis modules. Cliquez un nœud pour afficher la preview DS Flutter à droite.
        </p>
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_440px] gap-6 items-start">
          <div className="bg-white rounded-lg shadow border border-gray-100 p-4">
            <div className="flex items-center gap-2 mb-3">
              <button
                type="button"
                onClick={() => setExpandedNodeIds(ALL_EXPANDABLE_NODE_IDS)}
                className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-700 hover:bg-gray-50"
              >
                Tout déplier
              </button>
              <button
                type="button"
                onClick={() => setExpandedNodeIds([])}
                className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-700 hover:bg-gray-50"
              >
                Tout replier
              </button>
              {selectedNodeId ? (
                <button
                  type="button"
                  onClick={() => setSelectedNodeId(null)}
                  className="text-xs px-2 py-1 rounded border border-indigo-200 text-indigo-700 hover:bg-indigo-50"
                >
                  Désélectionner
                </button>
              ) : null}
            </div>
            <ul className="space-y-1">
              {APP_ARBORESCENCE.map((node) => renderNode(node))}
            </ul>
          </div>
          <div className="hidden xl:flex justify-center sticky top-6">
            <div>
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2 text-center">
                Preview DS Flutter
              </div>
              <DeviceFrame src={previewSrc} title={selectedNodeId ?? 'Preview'} />
              {selectedNodeId ? (
                <div className="mt-3 text-xs text-gray-600 text-center break-words max-w-[399px]">
                  Node : <code className="bg-gray-100 px-1 py-0.5 rounded">{selectedNodeId}</code>
                </div>
              ) : (
                <div className="mt-3 text-xs text-gray-500 text-center max-w-[399px]">
                  Cliquez sur un nœud à gauche pour le prévisualiser ici.
                </div>
              )}
            </div>
          </div>
        </div>
        {/* En dessous de XL : preview en plein, sous l'arbre */}
        <div className="xl:hidden mt-6 flex justify-center">
          <div>
            <DeviceFrame src={previewSrc} title={selectedNodeId ?? 'Preview'} />
          </div>
        </div>
      </section>

      <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
        <p className="text-sm text-indigo-800">
          Schéma JSON du composant <strong>marketing_cards</strong> et utilisation Flutter : voir{' '}
          <code className="bg-white/80 px-1 rounded">docs/arquantix/DS_COMPONENT_MARKETING_CARDS.md</code>.
        </p>
      </div>
    </div>
  )
}
