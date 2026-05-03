'use client'

import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { defaultLocale as configDefaultLocale, supportedLocales, type Locale } from '@/config/locales'
import { toastError, toastSuccess } from '@/lib/admin/toast'

type SectionTypeMeta = {
  key: string
  label: string
  description?: string
}

export function CreateCommonModuleModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: (id: string) => void
}) {
  const [types, setTypes] = useState<SectionTypeMeta[]>([])
  const [loadingTypes, setLoadingTypes] = useState(false)
  const [label, setLabel] = useState('')
  const [sectionKey, setSectionKey] = useState('')
  const [defaultLocale, setDefaultLocale] = useState<Locale>(configDefaultLocale)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoadingTypes(true)
    fetch('/api/admin/section-types?eligibleCommonModule=1')
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data.types)) {
          setTypes(data.types)
          setSectionKey((prev) =>
            prev && data.types.some((t: SectionTypeMeta) => t.key === prev)
              ? prev
              : (data.types[0]?.key ?? ''),
          )
        }
      })
      .catch(() => toastError('Impossible de charger les types de sections'))
      .finally(() => setLoadingTypes(false))
  }, [open])

  useEffect(() => {
    if (!open) {
      setLabel('')
      setSectionKey('')
      setDefaultLocale(configDefaultLocale)
    }
  }, [open])

  if (!open) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!label.trim() || !sectionKey) {
      toastError('Libellé et type requis')
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch('/api/admin/site-common-modules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: label.trim(),
          sectionKey,
          defaultLocale,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Échec création')
      }
      toastSuccess('Module commun créé')
      onCreated(data.module?.id ?? '')
      onClose()
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div
        className="w-full max-w-lg rounded-xl bg-white shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-common-module-title"
      >
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 id="create-common-module-title" className="text-lg font-semibold text-slate-900">
            Nouveau module commun
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Fermer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4">
          <p className="text-sm text-slate-600">
            Choisissez le type de bloc (même catalogue que les sections de page), puis un nom court pour le retrouver
            dans la structure.
          </p>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Nom affiché</label>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="ex. CTA fin de page"
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Type de section</label>
            <select
              value={sectionKey}
              onChange={(e) => setSectionKey(e.target.value)}
              disabled={loadingTypes || types.length === 0}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              {types.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label} ({t.key})
                </option>
              ))}
            </select>
            {loadingTypes && <p className="mt-1 text-xs text-slate-500">Chargement…</p>}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Langue de référence</label>
            <select
              value={defaultLocale}
              onChange={(e) => setDefaultLocale(e.target.value as Locale)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              {supportedLocales.map((l) => (
                <option key={l} value={l}>
                  {l.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 border-t pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting ? 'Création…' : 'Créer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
