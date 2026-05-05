'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ChevronLeft, Trash2 } from 'lucide-react'
import { defaultLocale as configDefaultLocale, supportedLocales, type Locale } from '@/config/locales'
import { SectionEditor } from '@/components/admin/SectionEditor'
import { LocaleCompletenessStrip } from '@/components/admin/LocaleCompletenessStrip'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { computeCommonModuleLocalesCompleteness } from '@/lib/admin/commonModuleLocaleCompleteness'
import type { CommonModuleEntryStored } from '@/lib/cms/commonModulesStorage'
import { normalizeCommonModuleEntry } from '@/lib/cms/commonModulesStorage'
import {
  deepMerge,
  deepMergeThree,
  pickTranslatableFromData,
  stripTranslatableFromData,
} from '@/lib/cms/commonModuleDesignSplit'
import { getSectionType } from '@/lib/sections/library'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const LOCALE_LABEL: Record<Locale, string> = {
  fr: 'Français',
  en: 'English',
  it: 'Italiano',
}

function deepClone<T>(x: T): T {
  return structuredClone(x)
}

export function SiteCommonModuleEditor({ moduleId }: { moduleId: string }) {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [moduleMeta, setModuleMeta] = useState<CommonModuleEntryStored | null>(null)
  const [sectionTypeLabel, setSectionTypeLabel] = useState('')
  const [label, setLabel] = useState('')
  const [defaultLocale, setDefaultLocale] = useState<Locale>(configDefaultLocale)
  const [activeLocale, setActiveLocale] = useState<Locale>(configDefaultLocale)
  /** Médias, couleurs, options d’affichage — partagés. */
  const [design, setDesign] = useState<Record<string, unknown>>({})
  /** Textes / liens traduisibles par langue. */
  const [localesMap, setLocalesMap] = useState<Record<Locale, Record<string, unknown>>>({
    fr: {},
    en: {},
    it: {},
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/admin/site-common-modules/${moduleId}`)
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'Chargement impossible')
      const raw = json.module as CommonModuleEntryStored
      const m = normalizeCommonModuleEntry(raw)
      setModuleMeta(m)
      setLabel(m.label)
      setDefaultLocale(m.defaultLocale)
      setSectionTypeLabel(json.sectionType?.label ?? m.sectionKey)
      setDesign(deepClone((m.design ?? {}) as Record<string, unknown>))
      setLocalesMap({
        fr: deepClone((m.locales.fr ?? {}) as Record<string, unknown>),
        en: deepClone((m.locales.en ?? {}) as Record<string, unknown>),
        it: deepClone((m.locales.it ?? {}) as Record<string, unknown>),
      })
      setActiveLocale(m.defaultLocale ?? configDefaultLocale)
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Erreur')
      router.push('/admin/pages')
    } finally {
      setLoading(false)
    }
  }, [moduleId, router])

  useEffect(() => {
    void load()
  }, [load])

  const sectionKey = moduleMeta?.sectionKey ?? ''

  const baseDefaults = useMemo((): Record<string, unknown> => {
    const t = getSectionType(sectionKey)
    return ((t?.defaultData ?? {}) as Record<string, unknown>) ?? {}
  }, [sectionKey])

  /** Formulaire « Apparence » : défauts sans champs traduits + design stocké. */
  const designDataForEditor = useMemo(() => {
    if (!sectionKey) return {}
    const stripped = stripTranslatableFromData(baseDefaults, sectionKey)
    return deepMerge(stripped, design)
  }, [baseDefaults, design, sectionKey])

  /** Formulaire « Textes » : défauts + design partagé + texte de la langue active. */
  const textMergedForEditor = useMemo(
    () => deepMergeThree(baseDefaults, design, localesMap[activeLocale] ?? {}),
    [baseDefaults, design, localesMap, activeLocale],
  )

  const handleLocaleChange = (next: Locale) => {
    if (next === activeLocale) return
    setActiveLocale(next)
  }

  const handleDesignChange = (d: Record<string, unknown>) => {
    if (!sectionKey) return
    setDesign(stripTranslatableFromData(d, sectionKey))
  }

  const handleTextChange = (d: Record<string, unknown>) => {
    if (!sectionKey) return
    setLocalesMap((prev) => ({
      ...prev,
      [activeLocale]: pickTranslatableFromData(d, sectionKey),
    }))
  }

  const syntheticModuleForCompleteness = useMemo((): CommonModuleEntryStored | null => {
    if (!moduleMeta) return null
    return normalizeCommonModuleEntry({
      ...moduleMeta,
      design,
      locales: {
        fr: localesMap.fr ?? {},
        en: localesMap.en ?? {},
        it: localesMap.it ?? {},
      },
    })
  }, [moduleMeta, design, localesMap])

  const completeness = syntheticModuleForCompleteness
    ? computeCommonModuleLocalesCompleteness(syntheticModuleForCompleteness)
    : null

  const handleSaveTexts = async () => {
    if (!moduleMeta || !sectionKey) return
    setSaving(true)
    try {
      const block = deepMergeThree(baseDefaults, design, localesMap[activeLocale] ?? {})
      const res = await fetch(`/api/admin/site-common-modules/${moduleId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'locale',
          locale: activeLocale,
          defaultLocale,
          block,
        }),
      })
      const json = await res.json()
      if (!res.ok) {
        throw new Error(json.error || 'Enregistrement impossible')
      }
      toastSuccess('Textes enregistrés')
      await load()
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveDesign = async () => {
    if (!moduleMeta || !sectionKey) return
    setSaving(true)
    try {
      const res = await fetch(`/api/admin/site-common-modules/${moduleId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'design',
          designBlock: designDataForEditor,
        }),
      })
      const json = await res.json()
      if (!res.ok) {
        throw new Error(json.error || 'Enregistrement impossible')
      }
      toastSuccess('Apparence enregistrée')
      await load()
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteModule = async () => {
    if (!moduleMeta) return
    if (
      !confirm(
        `Supprimer le module « ${moduleMeta.label} » ? Les pages qui pointent vers lui n’afficheront plus ce bloc (référence orpheline).`,
      )
    ) {
      return
    }
    setDeleting(true)
    try {
      const res = await fetch(`/api/admin/site-common-modules/${moduleId}`, { method: 'DELETE' })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(typeof json.error === 'string' ? json.error : 'Suppression impossible')
      }
      toastSuccess('Module supprimé')
      router.push('/admin/pages')
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Suppression impossible')
    } finally {
      setDeleting(false)
    }
  }

  const handleSaveMeta = async () => {
    const t = label.trim()
    if (!t || !moduleMeta) return
    setSaving(true)
    try {
      const res = await fetch(`/api/admin/site-common-modules/${moduleId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: t, defaultLocale }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'Erreur')
      toastSuccess('Métadonnées mises à jour')
      await load()
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  if (loading || !moduleMeta) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="py-12 text-center text-gray-500">Chargement…</div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/admin/pages"
          className="inline-flex items-center gap-1 text-sm font-medium text-indigo-700 hover:text-indigo-900"
        >
          <ChevronLeft className="h-4 w-4" />
          Structure du site
        </Link>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Module commun : {moduleMeta.label}</h1>
            <p className="mt-1 text-sm text-slate-600">
              Type <span className="font-mono text-xs">{moduleMeta.sectionKey}</span>
              {sectionTypeLabel ? ` — ${sectionTypeLabel}` : ''}. L’<strong>apparence</strong> (fonds, médias) est
              commune ; les <strong>textes</strong> dépendent de l’onglet de langue.
            </p>
          </div>
          {completeness && (
            <div className="flex flex-col gap-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Complétude</span>
              <LocaleCompletenessStrip levels={completeness} variant="inline" />
            </div>
          )}
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Nom dans la structure</label>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Langue de secours</label>
            <select
              value={defaultLocale}
              onChange={(e) => setDefaultLocale(e.target.value as Locale)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              {supportedLocales.map((l) => (
                <option key={l} value={l}>
                  {LOCALE_LABEL[l]}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-3">
          <Button type="button" variant="outline" size="sm" onClick={() => void handleSaveMeta()} disabled={saving}>
            Mettre à jour nom / langue de secours
          </Button>
        </div>
      </div>

      <div className="rounded-xl border border-amber-100 bg-amber-50/50 p-6 shadow-sm">
        <h2 className="mb-1 text-lg font-semibold text-slate-900">Apparence &amp; mise en page</h2>
        <p className="mb-4 text-sm text-slate-600">
          Image de fond, couleurs, opacités, options d’affichage des boutons : valable pour <strong>toutes</strong> les
          langues.
        </p>
        <SectionEditor
          sectionKey={moduleMeta.sectionKey}
          data={designDataForEditor}
          onChange={handleDesignChange}
          commonModuleSplit="design"
        />
        <div className="mt-4">
          <Button type="button" onClick={() => void handleSaveDesign()} disabled={saving}>
            {saving ? 'Enregistrement…' : 'Enregistrer l’apparence'}
          </Button>
        </div>
      </div>

      <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-900">Langue des textes</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {supportedLocales.map((loc) => (
            <button
              key={loc}
              type="button"
              onClick={() => handleLocaleChange(loc)}
              className={cn(
                'rounded-lg border px-3 py-1.5 text-sm font-medium',
                loc === activeLocale
                  ? 'border-indigo-600 bg-white text-indigo-900'
                  : 'border-slate-200 bg-white/70 text-slate-700 hover:border-slate-300',
              )}
            >
              {LOCALE_LABEL[loc]}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-1 text-lg font-semibold text-slate-900">Textes &amp; liens ({LOCALE_LABEL[activeLocale]})</h2>
        <p className="mb-4 text-sm text-slate-600">
          Titres, descriptions, libellés de boutons et URL cibles pour cette langue uniquement.
        </p>
        <SectionEditor
          sectionKey={moduleMeta.sectionKey}
          data={textMergedForEditor}
          onChange={(d) => handleTextChange(d as Record<string, unknown>)}
          commonModuleSplit="locale"
        />
        <details className="mt-6">
          <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-900">JSON brut (fusion aperçu)</summary>
          <textarea
            value={JSON.stringify(textMergedForEditor, null, 2)}
            readOnly
            className="mt-2 h-40 w-full rounded-md border border-gray-300 bg-slate-50 p-3 font-mono text-xs"
          />
        </details>
        <div className="mt-6">
          <Button type="button" onClick={() => void handleSaveTexts()} disabled={saving}>
            {saving ? 'Enregistrement…' : `Enregistrer les textes (${LOCALE_LABEL[activeLocale]})`}
          </Button>
        </div>
      </div>

      <div className="rounded-xl border border-red-200 bg-red-50/40 p-6 shadow-sm">
        <h2 className="mb-1 text-lg font-semibold text-red-950">Zone sensible</h2>
        <p className="mb-4 text-sm text-red-900/90">
          Supprimer définitivement ce module commun. Les références « module commun » sur les pages resteront mais le
          bloc ne s’affichera plus tant que la référence n’est pas retirée ou remplacée.
        </p>
        <Button
          type="button"
          variant="outline"
          className="border-red-300 text-red-800 hover:bg-red-100"
          onClick={() => void handleDeleteModule()}
          disabled={saving || deleting}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          {deleting ? 'Suppression…' : 'Supprimer ce module'}
        </Button>
      </div>
    </div>
  )
}
