'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Globe2, Plus, Save, Trash2, UploadCloud, Wand2 } from 'lucide-react'

import { toastError, toastSuccess } from '@/lib/admin/toast'
import { useAdminEditingLocale } from '@/components/admin/AdminEditingLocaleContext'
import type { Locale } from '@/config/locales'

const ICON_OPTIONS = [
  'home_rounded',
  'trending_up_rounded',
  'currency_bitcoin',
  'radio_rounded',
  'search_rounded',
  'more_horiz_rounded',
] as const

type IconKey = (typeof ICON_OPTIONS)[number]

type TargetKind = 'native_tab' | 'cms_page' | 'external_url'

type TargetState = {
  kind: TargetKind
  /// `value` selon kind : `native_tab` → 'home'/'offers'/etc. ;
  /// `cms_page` → slug ; `external_url` → URL.
  value: string
}

type Item = {
  id: string
  order: number
  enabled: boolean
  label: string
  icon: IconKey | null
  target: TargetState | null
}

type ShellMeta = {
  requestedLocale: string
  defaultLocale: string
  supportedLocales: string[]
  contentLocale: string | null
  isFallback: boolean
  localeCoverage: string[]
  availableIcons: readonly IconKey[]
}

type LandingPageOption = {
  slug: string
  title: string | null
  urlPath: string
  modulesCount: number
  contentLocale: string | null
}

const NATIVE_TAB_VALUES = [
  'home',
  'offers',
  'markets',
  'design_system',
  'search',
  'more',
]

function targetFromApi(raw: unknown): TargetState | null {
  if (!raw || typeof raw !== 'object') return null
  const r = raw as Record<string, unknown>
  const kind = String(r.kind ?? '')
  if (kind === 'native_tab') return { kind, value: String(r.value ?? '') }
  if (kind === 'cms_page') return { kind, value: String(r.slug ?? '') }
  if (kind === 'external_url') return { kind, value: String(r.value ?? '') }
  return null
}

function targetToApi(t: TargetState): Record<string, string> {
  if (t.kind === 'cms_page') return { kind: 'cms_page', slug: t.value }
  return { kind: t.kind, value: t.value }
}

export default function AdminFlutterShellPage() {
  const router = useRouter()
  const { locale: editingLocale, setLocale, editingLocales } = useAdminEditingLocale()

  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<Item[]>([])
  const [meta, setMeta] = useState<ShellMeta | null>(null)
  const [seeded, setSeeded] = useState<boolean | null>(null)
  const [seeding, setSeeding] = useState(false)
  const [saving, setSaving] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [landingPages, setLandingPages] = useState<LandingPageOption[]>([])
  const [creating, setCreating] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [newLabel, setNewLabel] = useState('')
  const [newIcon, setNewIcon] = useState<IconKey>('home_rounded')
  const [newKind, setNewKind] = useState<TargetKind>('native_tab')
  const [newValue, setNewValue] = useState('home')

  const load = useCallback(async (loc: string) => {
    const res = await fetch(
      `/api/admin/flutter/shell?locale=${encodeURIComponent(loc)}`,
      { credentials: 'include' },
    )
    if (res.status === 404) {
      setSeeded(false)
      setItems([])
      setMeta(null)
      return
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body?.error || `HTTP ${res.status}`)
    }
    const payload = await res.json()
    setSeeded(true)
    setMeta(payload.meta as ShellMeta)
    const parsedItems: Item[] = (payload.items ?? []).map((raw: Record<string, unknown>) => ({
      id: String(raw.id),
      order: Number(raw.order ?? 0),
      enabled: Boolean(raw.enabled ?? true),
      label: String(raw.label ?? ''),
      icon: (raw.icon as IconKey | null) ?? null,
      target: targetFromApi(raw.target),
    }))
    parsedItems.sort((a, b) => a.order - b.order)
    setItems(parsedItems)
  }, [])

  /// Charge la liste des landing pages disponibles (toutes locales). Sert au
  /// dropdown des targets `cms_page` : on ne propose que des slugs réellement
  /// existants en base — évite la dérive (slug typé à la main qui pointe nulle
  /// part) et donne aux admins la couverture i18n de chaque page d'un coup.
  const loadLandingPages = useCallback(async (loc: string) => {
    try {
      const res = await fetch(
        `/api/admin/landing-pages?locale=${encodeURIComponent(loc)}`,
        { credentials: 'include' },
      )
      if (!res.ok) return
      const payload = await res.json()
      const opts: LandingPageOption[] = (payload.pages ?? []).map((p: {
        slug: string
        title: string | null
        urlPath: string
        configSummary?: { modulesCount?: number; contentLocale?: string | null }
      }) => ({
        slug: p.slug,
        title: p.title,
        urlPath: p.urlPath,
        modulesCount: p.configSummary?.modulesCount ?? 0,
        contentLocale: p.configSummary?.contentLocale ?? null,
      }))
      setLandingPages(opts)
    } catch {
      /// non-bloquant : si l'API liste est down, on garde un input texte libre.
    }
  }, [])

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
        await Promise.all([load(editingLocale), loadLandingPages(editingLocale)])
      } catch (e) {
        toastError(e instanceof Error ? e.message : 'Chargement impossible')
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router])

  useEffect(() => {
    if (loading) return
    void Promise.all([load(editingLocale), loadLandingPages(editingLocale)]).catch(
      (e) => toastError(e instanceof Error ? e.message : 'Rechargement impossible'),
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingLocale])

  const handleSeed = async () => {
    setSeeding(true)
    try {
      const res = await fetch('/api/admin/flutter/shell/seed', {
        method: 'POST',
        credentials: 'include',
      })
      const body = await res.json()
      if (!res.ok) throw new Error(body?.error || 'Seed impossible')
      toastSuccess('Shell de l’app initialisé.')
      await load(editingLocale)
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Seed impossible')
    } finally {
      setSeeding(false)
    }
  }

  const updateItem = (id: string, patch: Partial<Item>) => {
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, ...patch } : it)))
  }

  const writeAll = async (scope: 'draft' | 'published') => {
    if (items.length === 0) return
    const url =
      `/api/admin/flutter/shell` +
      `?locale=${encodeURIComponent(editingLocale)}&status=${scope}`
    const res = await fetch(url, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: items.map((it) => ({
          id: it.id,
          label: it.label,
          icon: it.icon ?? undefined,
          target: it.target ? targetToApi(it.target) : undefined,
          enabled: it.enabled,
          order: it.order,
        })),
      }),
    })
    const body = await res.json()
    if (!res.ok) {
      const issues = Array.isArray(body?.issues)
        ? body.issues.map((i: { message?: string }) => i?.message).filter(Boolean).join(', ')
        : ''
      throw new Error(issues || body?.error || `HTTP ${res.status}`)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await writeAll('draft')
      toastSuccess('Brouillon enregistré.')
      await load(editingLocale)
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Sauvegarde impossible')
    } finally {
      setSaving(false)
    }
  }

  const handlePublish = async () => {
    setPublishing(true)
    try {
      await writeAll('published')
      toastSuccess('Tab bar publiée.')
      await load(editingLocale)
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Publication impossible')
    } finally {
      setPublishing(false)
    }
  }

  const handleAddItem = async () => {
    const label = newLabel.trim()
    if (!label) {
      toastError('Le libellé est requis.')
      return
    }
    if (!newValue.trim()) {
      toastError('La valeur cible est requise.')
      return
    }
    setCreating(true)
    try {
      const target =
        newKind === 'cms_page'
          ? { kind: 'cms_page', slug: newValue.trim() }
          : { kind: newKind, value: newValue.trim() }
      const res = await fetch(
        `/api/admin/flutter/shell/items?locale=${encodeURIComponent(editingLocale)}&status=draft`,
        {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ label, icon: newIcon, target }),
        },
      )
      const body = await res.json()
      if (!res.ok) {
        const issues = Array.isArray(body?.issues)
          ? body.issues.map((i: { message?: string }) => i?.message).filter(Boolean).join(', ')
          : ''
        throw new Error(issues || body?.error || `HTTP ${res.status}`)
      }
      toastSuccess('Tab ajouté (brouillon).')
      setNewLabel('')
      setNewKind('native_tab')
      setNewValue('home')
      setNewIcon('home_rounded')
      await load(editingLocale)
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Création impossible')
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteItem = async (id: string, label: string) => {
    if (!window.confirm(`Supprimer définitivement le tab "${label}" ?`)) return
    setDeletingId(id)
    try {
      const res = await fetch(`/api/admin/flutter/shell/items/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        credentials: 'include',
      })
      const body = await res.json()
      if (!res.ok) throw new Error(body?.error || `HTTP ${res.status}`)
      toastSuccess('Tab supprimé.')
      await load(editingLocale)
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Suppression impossible')
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return <div className="p-6 text-gray-500">Chargement…</div>
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">App — Tabs principaux</h1>
          <p className="text-gray-600 mt-1">
            Pilote la tab bar de l’app Flutter (libellés, icônes, cibles natives) en multi-langue.
          </p>
        </div>
        <Link
          href="/admin/flutter"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Retour à Flutter
        </Link>
      </div>

      {seeded === false ? (
        <div className="bg-white rounded-lg shadow border border-gray-100 p-5">
          <h2 className="text-lg font-semibold mb-2">Initialiser le shell</h2>
          <p className="text-sm text-gray-600 mb-3">
            Aucune configuration en base. Lance l’initialisation pour créer le menu&nbsp;
            <code className="font-mono">app_main_tabs</code>, ses items et le contenu CMS associé.
            <br />
            <span className="text-gray-500">
              Idempotent — peut être ré-exécuté à tout moment sans rien casser.
            </span>
          </p>
          <button
            type="button"
            onClick={handleSeed}
            disabled={seeding}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Wand2 className="w-4 h-4" />
            {seeding ? 'Initialisation…' : 'Initialiser le shell'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow border border-gray-100 p-4 flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-gray-200 bg-gray-50 text-gray-700 text-xs">
              <Globe2 className="w-3 h-3" />
              Édition&nbsp;: <code className="font-mono">{editingLocale}</code>
            </span>
            {meta ? (
              <>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-gray-200 bg-gray-50 text-gray-700 text-xs">
                  Défaut&nbsp;: <code className="font-mono">{meta.defaultLocale}</code>
                </span>
                {meta.contentLocale && meta.contentLocale !== editingLocale ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-amber-200 bg-amber-50 text-amber-700 text-xs">
                    Contenu servi en&nbsp;: <code className="font-mono">{meta.contentLocale}</code>
                    {meta.isFallback ? ' (fallback)' : ''}
                  </span>
                ) : null}
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-gray-200 bg-gray-50 text-gray-600 text-xs">
                  Variantes&nbsp;: {meta.localeCoverage.join(', ') || '—'}
                </span>
              </>
            ) : null}
            <div className="ml-auto flex items-center gap-2">
              {editingLocales.length > 1 ? (
                <select
                  value={editingLocale}
                  onChange={(e) => setLocale(e.target.value as Locale)}
                  className="px-3 py-2 border border-gray-200 rounded-md text-sm"
                  aria-label="Langue d'édition"
                >
                  {editingLocales.map((loc) => (
                    <option key={loc} value={loc}>
                      {loc}
                    </option>
                  ))}
                </select>
              ) : null}
              <button
                type="button"
                onClick={handleSeed}
                disabled={seeding}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-gray-200 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                title="Réconcilie les libellés/cibles manquants pour les locales activées (ne touche pas l’existant)."
              >
                <Wand2 className="w-4 h-4" />
                {seeding ? 'Réconciliation…' : 'Réconcilier'}
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || publishing}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Sauvegarde…' : 'Enregistrer brouillon'}
              </button>
              <button
                type="button"
                onClick={handlePublish}
                disabled={saving || publishing}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                <UploadCloud className="w-4 h-4" />
                {publishing ? 'Publication…' : 'Publier'}
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow border border-gray-100 p-4 space-y-3">
            <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Ajouter un tab
            </h2>
            <p className="text-xs text-gray-500">
              Le tab est créé en <strong>brouillon</strong> pour la langue d’édition (libellé identique pour les autres langues, à
              affiner ensuite). Les icônes/cibles ne sont pas localisées.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-2 items-start">
              <input
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                placeholder={`Libellé (${editingLocale})`}
                className="px-3 py-2 border rounded-md md:col-span-1"
              />
              <select
                value={newIcon}
                onChange={(e) => setNewIcon(e.target.value as IconKey)}
                className="px-3 py-2 border rounded-md"
                aria-label="Icône"
              >
                {ICON_OPTIONS.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
              <select
                value={newKind}
                onChange={(e) => {
                  const k = e.target.value as TargetKind
                  setNewKind(k)
                  setNewValue(k === 'native_tab' ? 'home' : '')
                }}
                className="px-3 py-2 border rounded-md"
                aria-label="Type cible"
              >
                <option value="native_tab">native_tab</option>
                <option value="cms_page">cms_page</option>
                <option value="external_url">external_url</option>
              </select>
              {newKind === 'native_tab' ? (
                <select
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  className="px-3 py-2 border rounded-md"
                  aria-label="Valeur cible"
                >
                  {NATIVE_TAB_VALUES.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              ) : newKind === 'cms_page' && landingPages.length > 0 ? (
                <select
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  className="px-3 py-2 border rounded-md"
                  aria-label="Page CMS"
                >
                  <option value="">— page —</option>
                  {landingPages.map((p) => (
                    <option key={p.slug} value={p.slug}>
                      {(p.title || p.slug)} ({p.slug})
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  placeholder={newKind === 'cms_page' ? 'slug-de-page' : 'https://…'}
                  className="px-3 py-2 border rounded-md"
                />
              )}
              <button
                type="button"
                onClick={handleAddItem}
                disabled={creating}
                className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                <Plus className="w-4 h-4" />
                {creating ? 'Ajout…' : 'Ajouter'}
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow border border-gray-100 overflow-hidden">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-3 py-2 w-16">Ordre</th>
                  <th className="px-3 py-2 w-20">Activé</th>
                  <th className="px-3 py-2">Libellé ({editingLocale})</th>
                  <th className="px-3 py-2 w-48">Icône</th>
                  <th className="px-3 py-2 w-44">Type cible</th>
                  <th className="px-3 py-2">Valeur cible</th>
                  <th className="px-3 py-2 w-24"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.id} className="border-t border-gray-100">
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        min={0}
                        value={it.order}
                        onChange={(e) =>
                          updateItem(it.id, { order: Number(e.target.value || 0) })
                        }
                        className="w-16 px-2 py-1 border rounded"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={it.enabled}
                        onChange={(e) => updateItem(it.id, { enabled: e.target.checked })}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        value={it.label}
                        onChange={(e) => updateItem(it.id, { label: e.target.value })}
                        className="w-full px-2 py-1 border rounded"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={it.icon ?? ''}
                        onChange={(e) =>
                          updateItem(it.id, { icon: (e.target.value || null) as IconKey | null })
                        }
                        className="w-full px-2 py-1 border rounded"
                      >
                        <option value="">—</option>
                        {ICON_OPTIONS.map((k) => (
                          <option key={k} value={k}>
                            {k}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={it.target?.kind ?? 'native_tab'}
                        onChange={(e) => {
                          const kind = e.target.value as TargetKind
                          updateItem(it.id, {
                            target: {
                              kind,
                              value: kind === 'native_tab' ? 'home' : '',
                            },
                          })
                        }}
                        className="w-full px-2 py-1 border rounded"
                      >
                        <option value="native_tab">native_tab</option>
                        <option value="cms_page">cms_page</option>
                        <option value="external_url">external_url</option>
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      {it.target?.kind === 'native_tab' ? (
                        <select
                          value={it.target?.value ?? ''}
                          onChange={(e) =>
                            updateItem(it.id, {
                              target: { kind: 'native_tab', value: e.target.value },
                            })
                          }
                          className="w-full px-2 py-1 border rounded"
                        >
                          {NATIVE_TAB_VALUES.map((v) => (
                            <option key={v} value={v}>
                              {v}
                            </option>
                          ))}
                        </select>
                      ) : it.target?.kind === 'cms_page' ? (
                        <div className="flex items-center gap-2">
                          {landingPages.length > 0 ? (
                            <select
                              value={it.target?.value ?? ''}
                              onChange={(e) =>
                                updateItem(it.id, {
                                  target: { kind: 'cms_page', value: e.target.value },
                                })
                              }
                              className="flex-1 px-2 py-1 border rounded"
                            >
                              <option value="">— choisir une page —</option>
                              {landingPages.map((p) => (
                                <option key={p.slug} value={p.slug}>
                                  {(p.title || p.slug)} ({p.slug}) · {p.modulesCount} mod
                                </option>
                              ))}
                            </select>
                          ) : (
                            <input
                              value={it.target?.value ?? ''}
                              onChange={(e) =>
                                updateItem(it.id, {
                                  target: { kind: 'cms_page', value: e.target.value },
                                })
                              }
                              placeholder="slug-de-page"
                              className="flex-1 px-2 py-1 border rounded"
                            />
                          )}
                        </div>
                      ) : (
                        <input
                          value={it.target?.value ?? ''}
                          onChange={(e) =>
                            updateItem(it.id, {
                              target: {
                                kind: it.target?.kind ?? 'native_tab',
                                value: e.target.value,
                              },
                            })
                          }
                          placeholder="https://…"
                          className="w-full px-2 py-1 border rounded"
                        />
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        onClick={() => handleDeleteItem(it.id, it.label || it.id)}
                        disabled={deletingId === it.id}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50"
                        title="Supprimer ce tab (cascade i18n + data CMS)"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        {deletingId === it.id ? '…' : 'Suppr.'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
