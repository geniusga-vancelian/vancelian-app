'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Search, Edit, Eye, EyeOff, Plus, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ContentStatus } from '@prisma/client'
import { defaultLocale, supportedLocales, type Locale } from '@/config/locales'
import {
  ARTICLE_TYPES,
  ARTICLE_TYPE_KEYS,
  type ArticleTypeKey,
  normalizeArticleType,
} from '@/lib/admin/articleTypes'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import CreateHelpArticleModal from '@/components/admin/CreateHelpArticleModal'
import { messageFromAdminApiError } from '@/lib/admin/messageFromAdminApiError'

/**
 * Hub `/admin/content` : vue transverse de tous les contenus éditoriaux
 * (NEWS / ANALYSIS / RESEARCH / ACADEMY / USER_BLOG / HELP). Depuis le
 * cut-over admin (Phase 3.3.D), TOUS les contenus sont édités via
 * l'éditeur unifié `/admin/articles/[id]` — l'admin legacy
 * `/admin/help/articles/*` et son API sœur `/api/admin/help/articles/*`
 * ont été supprimés.
 *
 * Filtres : type, statut, locale, recherche par titre/slug.
 *
 * Source unique : `/api/admin/articles` (qui retourne aussi les Article
 * `articleType=HELP` avec leurs `helpCollectionId/helpCategoryId/helpSlug`).
 */

type UnifiedTypeKey = ArticleTypeKey

interface UnifiedRow {
  id: string
  slug: string
  title: string
  status: ContentStatus
  publishedAt: string | null
  updatedAt: string
  authorName: string | null
  typeKey: UnifiedTypeKey
  /** Lien éditeur unifié. */
  editHref: string
  /** Sous-libellé (slug collection / slug catégorie pour Help, vide sinon). */
  hierarchyLabel?: string
}

const UNIFIED_TYPE_LABELS = ARTICLE_TYPES
const UNIFIED_TYPE_KEYS: UnifiedTypeKey[] = [...ARTICLE_TYPE_KEYS]

export default function AdminContentHubPage() {
  const router = useRouter()

  const [rows, setRows] = useState<UnifiedRow[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<ContentStatus | 'ALL'>('ALL')
  const [localeFilter, setLocaleFilter] = useState<Locale>(defaultLocale)
  const [typeFilter, setTypeFilter] = useState<UnifiedTypeKey | 'ALL'>('ALL')
  const [helpCreateOpen, setHelpCreateOpen] = useState(false)
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

  const fetchAll = async () => {
    setLoading(true)
    try {
      const data = await fetchArticles()
      setRows(data.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)))
    } catch (e: any) {
      console.error(e)
      toastError('Erreur de chargement du hub contenus')
    } finally {
      setLoading(false)
    }
  }

  const fetchArticles = async (): Promise<UnifiedRow[]> => {
    const params = new URLSearchParams()
    if (searchQuery) params.set('search', searchQuery)
    if (statusFilter !== 'ALL') params.set('status', statusFilter)
    if (typeFilter !== 'ALL') params.set('articleType', typeFilter)
    params.set('locale', localeFilter)

    const res = await fetch(`/api/admin/articles?${params.toString()}`)
    if (!res.ok) {
      if (res.status === 401) router.push('/admin/login')
      throw new Error('Failed to fetch articles')
    }
    const data = await res.json()
    return (data.articles ?? []).map((a: any): UnifiedRow => {
      const tk = normalizeArticleType(a?.articleType) as UnifiedTypeKey
      // Pour HELP, on récupère la hiérarchie via les helpCollection/category
      // *slugs* attendus côté UI ; en pratique l'API ne retourne aujourd'hui
      // que les *ids*, donc on affiche les ids tronqués (utile pour l'admin
      // tant que l'on n'a pas étendu l'API à inclure les slugs).
      const hierarchyLabel =
        tk === 'HELP' && a?.helpCollectionId && a?.helpSlug
          ? `${a.helpCollectionId.slice(0, 6)}… / ${a.helpSlug}`
          : tk === 'ACADEMY' && a?.academyCollectionId && a?.academySlug
            ? `${a.academyCollectionId.slice(0, 6)}… / ${a.academySlug}`
            : undefined
      return {
        id: a.id,
        slug: a.helpSlug ?? a.slug,
        title: a.title ?? a.slug,
        status: a.status,
        publishedAt: a.publishedAt ?? null,
        updatedAt: a.updatedAt ?? a.createdAt ?? '',
        authorName: a.authorName ?? null,
        typeKey: tk,
        editHref: `/admin/articles/${encodeURIComponent(a.id)}`,
        hierarchyLabel,
      }
    })
  }

  const handleCreateArticle = async (articleType: UnifiedTypeKey) => {
    if (articleType === 'HELP') {
      setHelpCreateOpen(true)
      return
    }
    try {
      const descriptor = ARTICLE_TYPES[articleType]
      const slug = `${descriptor.slugPrefix}-${Date.now()}`
      const res = await fetch('/api/admin/articles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, authorName: 'Author', articleType }),
      })
      if (!res.ok) {
        const error = await res.json().catch(() => ({}))
        throw new Error(messageFromAdminApiError(error, 'Failed to create article'))
      }
      const data = await res.json()
      toastSuccess('Article créé')
      router.push(`/admin/articles/${encodeURIComponent(data.article.id)}`)
    } catch (e: any) {
      toastError(e?.message || 'Failed to create article')
    }
  }

  useEffect(() => {
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery, statusFilter, localeFilter, typeFilter])

  const stats = useMemo(() => {
    const byType = new Map<UnifiedTypeKey, number>()
    for (const r of rows) byType.set(r.typeKey, (byType.get(r.typeKey) ?? 0) + 1)
    return byType
  }, [rows])

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Content Hub</h1>
          <p className="text-sm text-gray-500">
            Vue transverse — articles (blog/news/analyses/research/academy/social) + Help. Liens
            directs vers les éditeurs spécialisés.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative" ref={createMenuRef}>
            <Button
              type="button"
              onClick={() => setCreateMenuOpen((o) => !o)}
              aria-haspopup="menu"
              aria-expanded={createMenuOpen}
            >
              <Plus className="w-4 h-4 mr-2" />
              Nouveau
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
                      <span className="text-xs text-gray-500 leading-tight">
                        {descriptor.description}
                      </span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
          <Link
            href="/admin/help/collections"
            className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            title="Gérer les collections / catégories Help"
          >
            Help (Collections)
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Rechercher (titre, slug)…"
              className="pl-9 pr-3 py-2 w-full border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as UnifiedTypeKey | 'ALL')}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            <option value="ALL">Tous les types</option>
            {UNIFIED_TYPE_KEYS.map((key) => (
              <option key={key} value={key}>
                {UNIFIED_TYPE_LABELS[key].label}
              </option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as ContentStatus | 'ALL')}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            <option value="ALL">Tous les statuts</option>
            <option value="DRAFT">Brouillons</option>
            <option value="PUBLISHED">Publiés</option>
          </select>
          <select
            value={localeFilter}
            onChange={(e) => setLocaleFilter(e.target.value as Locale)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            {supportedLocales.map((loc) => (
              <option key={loc} value={loc}>
                {loc.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-gray-600">
          <span className="rounded-full bg-gray-100 px-2 py-0.5 font-medium">
            Total : {rows.length}
          </span>
          {UNIFIED_TYPE_KEYS.map((k) => {
            const c = stats.get(k) ?? 0
            if (c === 0) return null
            return (
              <span
                key={k}
                className={`rounded-full px-2 py-0.5 font-medium ${UNIFIED_TYPE_LABELS[k].badgeClassName}`}
              >
                {UNIFIED_TYPE_LABELS[k].label} : {c}
              </span>
            )
          })}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
            <tr>
              <th className="px-4 py-2 text-left">Type</th>
              <th className="px-4 py-2 text-left">Titre / Slug</th>
              <th className="px-4 py-2 text-left">Hiérarchie / Auteur</th>
              <th className="px-4 py-2 text-left">Statut</th>
              <th className="px-4 py-2 text-left">Mis à jour</th>
              <th className="px-4 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  Chargement…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  Aucun contenu pour ces filtres.
                </td>
              </tr>
            ) : (
              rows.map((r) => {
                const meta = UNIFIED_TYPE_LABELS[r.typeKey]
                return (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${meta.badgeClassName}`}>
                        {meta.label}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="font-medium text-gray-900">{r.title}</div>
                      <div className="text-xs text-gray-500 font-mono">{r.slug}</div>
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-600">
                      {r.hierarchyLabel ? <div>{r.hierarchyLabel}</div> : null}
                      {r.authorName ? <div>{r.authorName}</div> : null}
                    </td>
                    <td className="px-4 py-2">
                      {r.status === 'PUBLISHED' ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold text-green-800">
                          <Eye className="h-3 w-3" /> Publié
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-gray-200 px-2 py-0.5 text-[10px] font-semibold text-gray-700">
                          <EyeOff className="h-3 w-3" /> Brouillon
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500">
                      {r.updatedAt ? new Date(r.updatedAt).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Link
                        href={r.editHref}
                        className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
                      >
                        <Edit className="h-3.5 w-3.5" />
                        Éditer
                      </Link>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-3 text-[11px] text-gray-400">
        Astuce : la création passe par le bouton « Nouveau » ci-dessus (HELP ouvre une
        modale dédiée avec collection / catégorie / slug). L'édition de tous les contenus
        — y compris HELP — se fait via l'éditeur unifié{' '}
        <code className="rounded bg-gray-100 px-1">/admin/articles/[id]</code>.
      </div>

      <CreateHelpArticleModal
        open={helpCreateOpen}
        onClose={() => {
          setHelpCreateOpen(false)
          fetchAll()
        }}
      />
    </div>
  )
}
