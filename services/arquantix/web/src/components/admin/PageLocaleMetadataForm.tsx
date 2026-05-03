'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { defaultLocale, type Locale } from '@/config/locales'

export type PageLocaleMetadataInitial = {
  title: string
  description: string
  navMegaCategory: string
  navMegaDescription: string
}

type Props = {
  slug: string
  locale: Locale
  initial: PageLocaleMetadataInitial
  onSaved: () => void | Promise<void>
}

export function PageLocaleMetadataForm({ slug, locale, initial, onSaved }: Props) {
  const [title, setTitle] = useState(initial.title)
  const [description, setDescription] = useState(initial.description)
  const [navMegaCategory, setNavMegaCategory] = useState(initial.navMegaCategory)
  const [navMegaDescription, setNavMegaDescription] = useState(initial.navMegaDescription)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setTitle(initial.title)
    setDescription(initial.description)
    setNavMegaCategory(initial.navMegaCategory)
    setNavMegaDescription(initial.navMegaDescription)
  }, [
    initial.title,
    initial.description,
    initial.navMegaCategory,
    initial.navMegaDescription,
    locale,
    slug,
  ])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await fetch(
        `/api/admin/pages/${encodeURIComponent(slug)}/locale-metadata`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            locale,
            title: title.trim() || null,
            description: description.trim() || null,
            navMegaCategory: navMegaCategory.trim() || null,
            navMegaDescription: navMegaDescription.trim() || null,
          }),
        },
      )
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(typeof data.error === 'string' ? data.error : 'Enregistrement impossible')
      }
      toastSuccess('Métadonnées enregistrées')
      await onSaved()
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-3xl space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div>
        <h2 className="text-sm font-semibold text-slate-900">Métadonnées de la page</h2>
        <p className="mt-0.5 text-xs text-slate-600">
          Titre et description SEO pour <strong>{locale.toUpperCase()}</strong>
          {locale === defaultLocale ? (
            <> — aussi synchronisés sur les champs principaux de la page.</>
          ) : null}
          . L’icône méga-menu (média) est réglée dans le bloc « Page — hors traduction » au-dessus.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-1">
        <label className="block text-xs font-medium text-slate-700">
          Titre
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            maxLength={500}
            autoComplete="off"
          />
        </label>
        <label className="block text-xs font-medium text-slate-700">
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            maxLength={2000}
          />
        </label>
      </div>

      <div className="border-t border-slate-100 pt-4">
        <p className="text-[11px] font-medium text-slate-800">Méga-menu (page enfant d’un item)</p>
        <p className="mt-0.5 text-[10px] text-slate-500">
          Libellé de colonne et sous-titre optionnels pour l’affichage dans le méga-menu.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="block text-xs font-medium text-slate-700 sm:col-span-2">
            Libellé colonne (catégorie méga-menu)
            <input
              type="text"
              value={navMegaCategory}
              onChange={(e) => setNavMegaCategory(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              maxLength={120}
              autoComplete="off"
            />
          </label>
          <label className="block text-xs font-medium text-slate-700 sm:col-span-2">
            Sous-titre méga-menu
            <input
              type="text"
              value={navMegaDescription}
              onChange={(e) => setNavMegaDescription(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              maxLength={500}
              autoComplete="off"
            />
          </label>
        </div>
      </div>

      <div className="flex justify-end border-t border-slate-100 pt-3">
        <Button type="submit" disabled={saving}>
          {saving ? 'Enregistrement…' : 'Enregistrer les métadonnées'}
        </Button>
      </div>
    </form>
  )
}
