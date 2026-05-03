'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { defaultLocale, supportedLocales, type Locale } from '@/config/locales'
import { ChevronLeft, Trash2 } from 'lucide-react'

const LOCALE_LABELS: Record<Locale, string> = {
  fr: 'Français',
  en: 'English',
  it: 'Italiano',
}

function styleFromApi(s: string | null | undefined): 'primary' | 'secondary' {
  const v = (s || '').toLowerCase()
  if (v === 'secondary' || v === 'outline') return 'secondary'
  return 'primary'
}

type ItemPayload = {
  editor?: 'nav_action' | 'nav_menu_link'
  id: string
  label: string
  externalUrl: string | null
  buttonStyle: string | null
  enabled: boolean
  i18n: Array<{ locale: string; label: string; translationStatus: string }>
}

export default function NavActionEditPage() {
  const router = useRouter()
  const params = useParams()
  const rawId = params?.itemId
  const itemId = typeof rawId === 'string' ? rawId : Array.isArray(rawId) ? rawId[0] ?? '' : ''

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [item, setItem] = useState<ItemPayload | null>(null)
  const [externalUrl, setExternalUrl] = useState('')
  const [style, setStyle] = useState<'primary' | 'secondary'>('primary')
  const [labels, setLabels] = useState<Record<Locale, string>>({
    fr: '',
    en: '',
    it: '',
  })
  const [deleteOpen, setDeleteOpen] = useState(false)

  const load = useCallback(async () => {
    if (!itemId) return
    setLoading(true)
    try {
      const res = await fetch(`/api/admin/menus/primary/items/${encodeURIComponent(itemId)}`)
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'Chargement impossible')
      const it = data.item as ItemPayload
      if (it.editor === 'nav_menu_link') {
        router.replace(`/admin/pages/nav-menu-link/${encodeURIComponent(itemId)}`)
        return
      }
      setItem(it)
      setExternalUrl((it.externalUrl ?? '').trim())
      setStyle(styleFromApi(it.buttonStyle))
      const next: Record<Locale, string> = { fr: '', en: '', it: '' }
      for (const loc of supportedLocales) {
        if (loc === defaultLocale) {
          next[loc] = it.label ?? ''
        } else {
          next[loc] = it.i18n.find((r) => r.locale === loc)?.label ?? ''
        }
      }
      setLabels(next)
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
    try {
      const resBase = await fetch(`/api/admin/menus/primary/items/${encodeURIComponent(itemId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: base,
          externalUrl: externalUrl.trim() || null,
          buttonStyle: style,
        }),
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

      toastSuccess('Bouton enregistré')
      await load()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!itemId) return
    const res = await fetch(`/api/admin/menus/primary/items/${encodeURIComponent(itemId)}`, {
      method: 'DELETE',
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      toastError(data.error || 'Suppression impossible')
      return
    }
    toastSuccess('Bouton supprimé')
    router.push('/admin/pages')
  }

  if (!itemId) {
    return (
      <div className="p-6">
        <p className="text-sm text-red-600">Identifiant manquant.</p>
      </div>
    )
  }

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
        <h1 className="text-xl font-semibold text-slate-900">Bouton du menu (zone droite)</h1>
        <p className="mt-1 text-sm text-slate-600">
          Lien partagé entre les langues ; libellés par langue. Type d’affichage primary ou secondary.
        </p>
      </header>

      {loading ? (
        <p className="text-sm text-slate-500">Chargement…</p>
      ) : !item ? (
        <p className="text-sm text-red-600">Impossible de charger ce bouton.</p>
      ) : (
        <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="grid gap-4">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Lien de redirection (URL)</span>
              <input
                type="text"
                value={externalUrl}
                onChange={(e) => setExternalUrl(e.target.value)}
                placeholder="/connexion ou https://…"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Type d’affichage</span>
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value as 'primary' | 'secondary')}
                className="w-full max-w-xs rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm"
              >
                <option value="primary">Primary (plein)</option>
                <option value="secondary">Secondary (contour)</option>
              </select>
            </label>
          </div>

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
            <Button
              type="button"
              variant="outline"
              className="text-red-700"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="mr-1 h-4 w-4" />
              Supprimer
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Supprimer ce bouton ?"
        description="L’entrée sera retirée du menu principal."
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        destructive
        onConfirm={() => void handleDelete()}
      />
    </div>
  )
}
