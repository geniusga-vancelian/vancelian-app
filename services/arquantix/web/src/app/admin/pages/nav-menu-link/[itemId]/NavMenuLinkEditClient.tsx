'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { normalizeExternalNavUrl } from '@/lib/admin/validateExternalNavUrl'
import { defaultLocale, supportedLocales, type Locale } from '@/config/locales'
import { ChevronLeft } from 'lucide-react'

const LOCALE_LABELS: Record<Locale, string> = {
  fr: 'Français',
  en: 'English',
  it: 'Italiano',
}

type ItemPayload = {
  editor?: 'nav_action' | 'nav_menu_link'
  id: string
  label: string
  enabled: boolean
  isRoot: boolean
  pageId: string | null
  navigationNodeKind?: 'PAGE' | 'GROUP' | 'EXTERNAL_LINK'
  openInNewTab?: boolean
  externalUrl?: string | null
  page: { id: string; slug: string; title: string | null; urlPath: string } | null
  i18n: Array<{ locale: string; label: string; translationStatus: string }>
}

export function NavMenuLinkEditClient({ itemId: itemIdProp }: { itemId: string }) {
  const router = useRouter()
  const itemId = (itemIdProp ?? '').trim()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [item, setItem] = useState<ItemPayload | null>(null)
  const [labels, setLabels] = useState<Record<Locale, string>>({
    fr: '',
    en: '',
    it: '',
  })
  const [navKind, setNavKind] = useState<'PAGE' | 'GROUP' | 'EXTERNAL_LINK'>('PAGE')
  const [openTab, setOpenTab] = useState(false)
  const [externalUrl, setExternalUrl] = useState('')
  const [externalUrlError, setExternalUrlError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!itemId) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`/api/admin/menus/primary/items/${encodeURIComponent(itemId)}`)
      const data = (await res.json().catch(() => ({}))) as { item?: ItemPayload; error?: string }
      if (!res.ok) {
        throw new Error(data.error || 'Chargement impossible')
      }
      const it = data.item
      if (!it || typeof it.id !== 'string') {
        throw new Error('Réponse serveur invalide')
      }
      if (it.editor === 'nav_action') {
        router.replace(`/admin/pages/nav-action/${encodeURIComponent(itemId)}`)
        return
      }
      setItem(it)
      const i18nRows = Array.isArray(it.i18n) ? it.i18n : []
      const next: Record<Locale, string> = { fr: '', en: '', it: '' }
      for (const loc of supportedLocales) {
        if (loc === defaultLocale) {
          next[loc] = it.label ?? ''
        } else {
          next[loc] = i18nRows.find((r) => r.locale === loc)?.label ?? ''
        }
      }
      setLabels(next)
      setNavKind(it.navigationNodeKind ?? 'PAGE')
      setOpenTab(Boolean(it.openInNewTab))
      setExternalUrl((it.externalUrl ?? '').trim())
      setExternalUrlError(null)
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur')
      setItem(null)
    } finally {
      setLoading(false)
    }
  }, [itemId, router])

  useEffect(() => {
    void load()
  }, [load])

  const handleSave = async () => {
    if (!itemId || !item) return
    const base = labels[defaultLocale]?.trim() ?? ''
    if (!base) {
      toastError(`Libellé ${LOCALE_LABELS[defaultLocale]} requis`)
      return
    }
    setSaving(true)
    setExternalUrlError(null)
    try {
      const resBase = await fetch(`/api/admin/menus/primary/items/${encodeURIComponent(itemId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: base }),
      })
      const d0 = await resBase.json().catch(() => ({}))
      if (!resBase.ok) throw new Error(d0.error || 'Mise à jour impossible')

      for (const loc of supportedLocales) {
        if (loc === defaultLocale) continue
        const lab = (labels[loc] ?? '').trim()
        if (!lab) continue
        const res = await fetch(`/api/admin/menu-items/${encodeURIComponent(itemId)}/i18n`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ locale: loc, label: lab }),
        })
        const d = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(d.error || `Traduction ${loc} impossible`)
      }

      const navBody: Record<string, unknown> = {
        navigationNodeKind: navKind,
      }
      if (navKind === 'EXTERNAL_LINK') {
        const urlCheck = normalizeExternalNavUrl(externalUrl)
        if (!urlCheck.ok) {
          setExternalUrlError(urlCheck.error)
          toastError(urlCheck.error)
          return
        }
        navBody.externalUrl = urlCheck.url
        navBody.openInNewTab = openTab
      } else {
        navBody.openInNewTab = false
      }
      const resNav = await fetch(`/api/admin/menus/primary/items/${encodeURIComponent(itemId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(navBody),
      })
      const dNav = await resNav.json().catch(() => ({}))
      if (!resNav.ok) {
        const msg =
          typeof dNav.error === 'string' ? dNav.error : 'Type de navigation impossible'
        if (navKind === 'EXTERNAL_LINK') {
          setExternalUrlError(msg)
        }
        toastError(msg)
        return
      }
      setExternalUrlError(null)

      toastSuccess('Menu enregistré')
      await load()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  if (!itemId) {
    return (
      <div className="p-6">
        <p className="text-sm text-red-600">Identifiant manquant.</p>
      </div>
    )
  }

  const page = item?.page

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/admin/pages"
          className="inline-flex items-center gap-1 text-sm font-medium text-indigo-700 hover:text-indigo-900"
        >
          <ChevronLeft className="h-4 w-4" />
          Structure du site
        </Link>
      </div>

      <header>
        <h1 className="text-xl font-semibold text-slate-900">Lien du menu (barre de navigation)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Libellés affichés dans le menu pour chaque langue. La cible de la page ne change pas ici.
        </p>
      </header>

      {loading ? (
        <p className="text-sm text-slate-500">Chargement…</p>
      ) : !item ? (
        <p className="text-sm text-red-600">Impossible de charger cette entrée.</p>
      ) : (
        <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="rounded-lg border border-slate-100 bg-slate-50/80 p-4 text-sm">
            <h2 className="mb-2 font-semibold text-slate-800">Page cible</h2>
            {page ? (
              <div className="space-y-1 text-slate-600">
                <p>
                  <span className="text-slate-500">Titre CMS :</span>{' '}
                  {page.title?.trim() || page.slug}
                </p>
                <p className="font-mono text-xs text-slate-500">{page.urlPath || `/${page.slug}`}</p>
                <Link
                  href={`/admin/pages/${encodeURIComponent(page.slug)}?editingLocale=${encodeURIComponent(defaultLocale)}`}
                  className="inline-block pt-2 text-xs font-medium text-indigo-700 hover:text-indigo-900"
                >
                  Ouvrir l’éditeur de page →
                </Link>
              </div>
            ) : (
              <p className="text-amber-800">Page introuvable — vérifiez la configuration du menu.</p>
            )}
          </div>

          {!item.isRoot ? (
            <div className="rounded-lg border border-slate-100 bg-white p-4">
              <h2 className="mb-2 text-sm font-semibold text-slate-800">Type de navigation (niveau 1)</h2>
              <p className="mb-3 text-xs text-slate-600">
                Défaut historique : <strong>Page cliquable</strong>. Un <strong>Groupe</strong> ouvre seulement le
                méga-menu (rubrique non cliquable). Un <strong>Lien externe</strong> utilise l’URL ci-dessous ; une
                page rattachée reste possible pour alimenter le méga-menu.
              </p>
              <label className="mb-3 block text-sm font-medium text-slate-700">
                Comportement
                <select
                  value={navKind}
                  onChange={(e) => {
                    setExternalUrlError(null)
                    setNavKind(e.target.value as 'PAGE' | 'GROUP' | 'EXTERNAL_LINK')
                  }}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm"
                >
                  <option value="PAGE">Page CMS cliquable</option>
                  <option value="GROUP">Groupe (non cliquable, méga-menu si ≥ 2 enfants)</option>
                  <option value="EXTERNAL_LINK">Lien externe</option>
                </select>
              </label>
              {navKind === 'GROUP' ? (
                <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-950">
                  Cette entrée est une rubrique de navigation : pas de lien principal. Les pages enfants (structure
                  CMS) alimentent le méga-menu. Sans contenu publié, l’URL de la page hub reste en 404 — comportement
                  attendu.
                </p>
              ) : null}
              {navKind === 'EXTERNAL_LINK' ? (
                <div className="mt-3 space-y-2">
                  <label className="block text-sm font-medium text-slate-700">
                    URL externe
                    <input
                      type="url"
                      value={externalUrl}
                      onChange={(e) => {
                        setExternalUrl(e.target.value)
                        setExternalUrlError(null)
                      }}
                      placeholder="https://…"
                      aria-invalid={externalUrlError ? true : undefined}
                      className={cn(
                        'mt-1 w-full rounded-lg border px-3 py-2 text-sm shadow-sm',
                        externalUrlError
                          ? 'border-red-500 focus:border-red-500 focus:ring-red-500/30'
                          : 'border-slate-300',
                      )}
                    />
                  </label>
                  {externalUrlError ? (
                    <p className="text-sm text-red-600" role="alert">
                      {externalUrlError}
                    </p>
                  ) : null}
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={openTab}
                      onChange={(e) => setOpenTab(e.target.checked)}
                      className="rounded border-slate-300"
                    />
                    Ouvrir dans un nouvel onglet
                  </label>
                </div>
              ) : null}
            </div>
          ) : null}

          <div>
            <h2 className="mb-3 text-sm font-semibold text-slate-800">Libellés par langue</h2>
            <div className="space-y-3">
              {supportedLocales.map((loc) => (
                <label key={loc} className="block text-sm">
                  <span className="mb-1 block font-medium text-slate-700">
                    {LOCALE_LABELS[loc]}
                    {loc === defaultLocale ? (
                      <span className="ml-1 font-normal text-slate-500">(référence)</span>
                    ) : null}
                  </span>
                  <input
                    type="text"
                    value={labels[loc] ?? ''}
                    onChange={(e) =>
                      setLabels((prev) => ({
                        ...prev,
                        [loc]: e.target.value,
                      }))
                    }
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm"
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4">
            <Button type="button" disabled={saving} onClick={() => void handleSave()}>
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
