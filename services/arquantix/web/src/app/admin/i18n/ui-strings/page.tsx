'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Globe,
  RefreshCw,
  Save,
  Send,
  Search,
  Sparkles,
  AlertCircle,
} from 'lucide-react'

import { useAdminEditingLocale } from '@/components/admin/AdminEditingLocaleContext'

type UiStringRow = {
  id: string
  key: string
  namespace: string
  locale: string
  value: string
  sourceText: string | null
  publishedValue: string | null
  description: string | null
  status: 'DRAFT' | 'PUBLISHED'
  translationStatus: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
  source: string
  updatedAt: string
}

type UiStringsResponse = {
  items: UiStringRow[]
  meta: {
    requestedLocale: string
    defaultLocale: string
    supportedLocales: string[]
    total: number
    limit: number
    offset: number
    availableNamespaces: string[]
    coverage: { locale: string; total: number; translated: number }[]
  }
}

const PAGE_SIZE = 200

/// Composant principal : page admin /admin/i18n/ui-strings.
/// Permet à l'admin de visualiser et d'éditer les overrides CMS de toutes
/// les strings ARB Flutter, par locale, namespace, et statut.
export default function UiStringsPage() {
  const { locale, setLocale, editingLocales } = useAdminEditingLocale()

  const [items, setItems] = useState<UiStringRow[]>([])
  const [meta, setMeta] = useState<UiStringsResponse['meta'] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [namespace, setNamespace] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [importing, setImporting] = useState(false)
  const [flash, setFlash] = useState<string | null>(null)

  /// Debounce simple sur la recherche (300 ms) — évite de spammer l'API.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 300)
    return () => clearTimeout(t)
  }, [search])

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams()
        params.set('locale', locale)
        if (namespace !== 'all') params.set('namespace', namespace)
        if (debouncedSearch.length >= 2) params.set('q', debouncedSearch)
        params.set('limit', String(PAGE_SIZE))
        const res = await fetch(`/api/admin/ui-strings?${params.toString()}`, {
          credentials: 'include',
          signal,
        })
        if (!res.ok) {
          const t = await res.text()
          throw new Error(`HTTP ${res.status}: ${t.slice(0, 200)}`)
        }
        const data = (await res.json()) as UiStringsResponse
        setItems(data.items)
        setMeta(data.meta)
        /// Reset des éditions locales : on repart toujours du DB après refresh.
        setEdits({})
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
        setError((e as Error).message)
      } finally {
        setLoading(false)
      }
    },
    [locale, namespace, debouncedSearch],
  )

  useEffect(() => {
    const ctrl = new AbortController()
    void refresh(ctrl.signal)
    return () => ctrl.abort()
  }, [refresh])

  const dirtyCount = useMemo(() => Object.keys(edits).length, [edits])
  const hasDirty = dirtyCount > 0

  const handleSave = async (publish: boolean) => {
    if (!hasDirty) return
    const setter = publish ? setPublishing : setSaving
    setter(true)
    setError(null)
    try {
      const entries = Object.entries(edits).map(([id, value]) => ({ id, value }))
      const url = `/api/admin/ui-strings?locale=${encodeURIComponent(locale)}${publish ? '&status=published' : ''}`
      const res = await fetch(url, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entries }),
      })
      if (!res.ok) {
        const t = await res.text()
        throw new Error(`HTTP ${res.status}: ${t.slice(0, 200)}`)
      }
      const data = await res.json()
      setFlash(
        publish
          ? `Publié ${data.meta?.publishedCopied ?? entries.length} string(s).`
          : `Brouillon enregistré (${data.meta?.touched ?? entries.length} string(s)).`,
      )
      await refresh()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setter(false)
      setTimeout(() => setFlash(null), 4000)
    }
  }

  const handleImport = async () => {
    setImporting(true)
    setError(null)
    try {
      const res = await fetch('/api/admin/ui-strings/import', {
        method: 'POST',
        credentials: 'include',
      })
      if (!res.ok) {
        const t = await res.text()
        throw new Error(`HTTP ${res.status}: ${t.slice(0, 200)}`)
      }
      const data = await res.json()
      const s = data.stats ?? {}
      setFlash(
        `ARB importé (locales: ${(data.locales ?? []).join(', ')}). +${s.created ?? 0} créées, ${s.updatedFull ?? 0} resync, ${s.updatedMetaOnly ?? 0} méta.`,
      )
      await refresh()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setImporting(false)
      setTimeout(() => setFlash(null), 5000)
    }
  }

  const namespacesList = meta?.availableNamespaces ?? [
    'common',
    'module',
    'screen',
    'error',
    'misc',
  ]

  return (
    <div className="max-w-7xl">
      <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-2">
        <Globe className="w-7 h-7 text-indigo-600" />
        UI strings (mobile)
      </h1>
      <p className="text-gray-600 mb-6 text-sm max-w-3xl">
        Surcharge CMS des strings ARB Flutter (boutons natifs, titres de
        widgets, libellés universels). Source de vérité = fichiers
        <code className="bg-gray-100 px-1 rounded mx-1">app_*.arb</code>
        compilés ; cette table ne stocke que les <em>overrides</em> publiés à
        l’app sans rebuild via
        <code className="bg-gray-100 px-1 rounded mx-1">/api/mobile/flutter/ui-strings</code>.
      </p>

      {/* Barre de filtres */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1 rounded-md border border-gray-200 bg-white px-2 py-1">
          {editingLocales.map((l) => (
            <button
              key={l}
              type="button"
              onClick={() => setLocale(l)}
              className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                l === locale
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-700 hover:bg-indigo-50'
              }`}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>

        <select
          value={namespace}
          onChange={(e) => setNamespace(e.target.value)}
          className="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm"
        >
          <option value="all">Tous namespaces</option>
          {namespacesList.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>

        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Recherche key ou texte (≥ 2 car.)…"
            className="w-full rounded-md border border-gray-200 bg-white pl-8 pr-3 py-1.5 text-sm"
          />
        </div>

        <button
          type="button"
          onClick={() => refresh()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Recharger
        </button>

        <button
          type="button"
          onClick={handleImport}
          disabled={importing}
          className="inline-flex items-center gap-1.5 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-sm text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
          title="Re-importe les ARB côté Flutter (préserve vos overrides)"
        >
          <Sparkles className={`w-4 h-4 ${importing ? 'animate-pulse' : ''}`} />
          Re-importer ARB
        </button>
      </div>

      {/* Indicateur de couverture par locale */}
      {meta?.coverage && meta.coverage.length > 0 ? (
        <div className="mb-4 flex flex-wrap gap-2">
          {meta.coverage.map((c) => {
            const pct = c.total > 0 ? Math.round((c.translated / c.total) * 100) : 0
            return (
              <div
                key={c.locale}
                className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1 text-xs"
              >
                <span className="font-semibold text-gray-700">{c.locale.toUpperCase()}</span>
                <span className="text-gray-500">
                  {c.translated} / {c.total}
                </span>
                <span
                  className={`font-medium ${
                    pct >= 90 ? 'text-emerald-600' : pct >= 50 ? 'text-amber-600' : 'text-rose-600'
                  }`}
                >
                  {pct}%
                </span>
              </div>
            )
          })}
        </div>
      ) : null}

      {flash ? (
        <div className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {flash}
        </div>
      ) : null}
      {error ? (
        <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <pre className="whitespace-pre-wrap font-mono text-xs">{error}</pre>
        </div>
      ) : null}

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-3 py-2 text-left font-semibold text-gray-700 w-[28%]">Key</th>
              <th className="px-3 py-2 text-left font-semibold text-gray-700 w-[24%]">
                Source ({meta?.defaultLocale ?? 'en'})
              </th>
              <th className="px-3 py-2 text-left font-semibold text-gray-700 w-[36%]">
                Override ({locale.toUpperCase()})
              </th>
              <th className="px-3 py-2 text-left font-semibold text-gray-700 w-[12%]">Statut</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-6 text-center text-gray-500">
                  Chargement…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-6 text-center text-gray-500">
                  Aucune string. Essayez « Re-importer ARB ».
                </td>
              </tr>
            ) : (
              items.map((it) => {
                const currentValue = edits[it.id] ?? it.value
                const isDirty = it.id in edits
                const isOverride = currentValue !== (it.sourceText ?? '')
                const isPublishedDifferent =
                  it.publishedValue !== null && it.publishedValue !== currentValue
                return (
                  <tr key={it.id} className={`border-b border-gray-100 ${isDirty ? 'bg-amber-50' : ''}`}>
                    <td className="px-3 py-2 align-top">
                      <div className="font-mono text-xs text-gray-800 break-all">{it.key}</div>
                      <div className="mt-0.5 text-xs text-gray-400">
                        {it.namespace} · {it.translationStatus}
                      </div>
                    </td>
                    <td className="px-3 py-2 align-top text-gray-600">
                      <div className="whitespace-pre-wrap text-xs">{it.sourceText ?? '—'}</div>
                    </td>
                    <td className="px-3 py-2 align-top">
                      <textarea
                        value={currentValue}
                        onChange={(e) => {
                          const v = e.target.value
                          setEdits((prev) => {
                            const next = { ...prev }
                            if (v === it.value) {
                              delete next[it.id]
                            } else {
                              next[it.id] = v
                            }
                            return next
                          })
                        }}
                        rows={Math.min(4, Math.max(1, currentValue.split('\n').length))}
                        className={`w-full rounded border px-2 py-1 text-sm font-mono ${
                          isDirty ? 'border-amber-400 bg-white' : 'border-gray-200 bg-white'
                        }`}
                      />
                    </td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex flex-col gap-1 text-xs">
                        {isOverride ? (
                          <span className="inline-flex items-center gap-1 rounded bg-indigo-100 px-1.5 py-0.5 text-indigo-700 w-fit">
                            override
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded bg-gray-100 px-1.5 py-0.5 text-gray-600 w-fit">
                            = source
                          </span>
                        )}
                        {it.publishedValue !== null ? (
                          <span
                            className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 w-fit ${
                              isPublishedDifferent
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-emerald-100 text-emerald-700'
                            }`}
                            title={`Publié : ${it.publishedValue}`}
                          >
                            {isPublishedDifferent ? 'pub. divergent' : 'publié'}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded bg-gray-100 px-1.5 py-0.5 text-gray-500 w-fit">
                            non publié
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Footer actions sticky */}
      <div className="sticky bottom-0 mt-4 flex items-center justify-between gap-3 rounded-md border border-gray-200 bg-white/95 backdrop-blur px-4 py-3 shadow-sm">
        <div className="text-sm text-gray-600">
          {meta ? (
            <>
              {meta.total} key{meta.total > 1 ? 's' : ''} affichée{meta.total > 1 ? 's' : ''}{' '}
              · locale <strong>{locale.toUpperCase()}</strong>
              {hasDirty ? (
                <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                  {dirtyCount} modif{dirtyCount > 1 ? 's' : ''} non sauvegardée{dirtyCount > 1 ? 's' : ''}
                </span>
              ) : null}
            </>
          ) : (
            '—'
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleSave(false)}
            disabled={!hasDirty || saving || publishing}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <Save className={`w-4 h-4 ${saving ? 'animate-pulse' : ''}`} />
            Enregistrer brouillon
          </button>
          <button
            type="button"
            onClick={() => handleSave(true)}
            disabled={!hasDirty || saving || publishing}
            className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Send className={`w-4 h-4 ${publishing ? 'animate-pulse' : ''}`} />
            Publier (DRAFT + PUBLISHED)
          </button>
        </div>
      </div>
    </div>
  )
}
