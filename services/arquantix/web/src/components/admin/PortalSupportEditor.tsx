'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LocaleCompletenessStrip } from '@/components/admin/LocaleCompletenessStrip'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { computePortalSupportLocalesCompleteness } from '@/lib/admin/portalSupportLocaleCompleteness'
import { getDefaultPortalSupportContent } from '@/lib/cms/portal-support'
import type { PortalSupportLocaleBlock } from '@/lib/cms/portalSupportSchema'
import { supportedLocales, type Locale } from '@/config/locales'
import { cn } from '@/lib/utils'

const LOCALE_LABEL: Record<Locale, string> = {
  fr: 'Français',
  en: 'English',
  it: 'Italiano',
}

export type PortalSupportFormState = {
  title: string
  description: string
  ctaLabel: string
  ctaHref: string
  secondaryLinkLabel: string
  secondaryLinkHref: string
}

function initialPortalSupportForm(): PortalSupportFormState {
  const d = getDefaultPortalSupportContent()
  return {
    title: d.title ?? '',
    description: d.description ?? '',
    ctaLabel: d.ctaLabel ?? '',
    ctaHref: d.ctaHref ?? '',
    secondaryLinkLabel: d.secondaryLinkLabel ?? '',
    secondaryLinkHref: d.secondaryLinkHref ?? '',
  }
}

function blockToForm(block: PortalSupportLocaleBlock): PortalSupportFormState {
  const base = initialPortalSupportForm()
  return {
    title: block.title ?? base.title,
    description: block.description ?? base.description,
    ctaLabel: block.ctaLabel ?? base.ctaLabel,
    ctaHref: block.ctaHref ?? base.ctaHref,
    secondaryLinkLabel: block.secondaryLinkLabel ?? base.secondaryLinkLabel,
    secondaryLinkHref: block.secondaryLinkHref ?? base.secondaryLinkHref,
  }
}

function formToBlock(form: PortalSupportFormState): PortalSupportLocaleBlock {
  const trim = (s: string) => s.trim()
  return {
    title: trim(form.title) || undefined,
    description: trim(form.description) || undefined,
    ctaLabel: trim(form.ctaLabel) || undefined,
    ctaHref: trim(form.ctaHref) || undefined,
    secondaryLinkLabel: trim(form.secondaryLinkLabel) || undefined,
    secondaryLinkHref: trim(form.secondaryLinkHref) || undefined,
  }
}

function emptyLocalesMap(): Record<Locale, PortalSupportFormState> {
  return {
    fr: initialPortalSupportForm(),
    en: initialPortalSupportForm(),
    it: initialPortalSupportForm(),
  }
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-gray-900">{label}</span>
      {hint ? <p className="text-xs text-gray-500">{hint}</p> : null}
      {children}
    </label>
  )
}

const inputClass =
  'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500'

export function PortalSupportEditor() {
  const router = useRouter()
  const [activeLocale, setActiveLocale] = useState<Locale>('fr')
  const [defaultLocaleState, setDefaultLocaleState] = useState<Locale>('fr')
  const [localesMap, setLocalesMap] = useState<Record<Locale, PortalSupportFormState>>(emptyLocalesMap)
  const [form, setForm] = useState<PortalSupportFormState>(() => initialPortalSupportForm())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const loadPayload = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/admin/portal-support')
      const data = await res.json()
      if (data.error === 'Unauthorized') {
        router.push('/admin/login')
        return
      }
      if (!data.locales || typeof data.locales !== 'object') {
        toastError('Réponse portail support inattendue')
        return
      }

      const dl = (data.defaultLocale as Locale) ?? 'fr'
      setDefaultLocaleState(supportedLocales.includes(dl) ? dl : 'fr')

      const nextMap = emptyLocalesMap()
      for (const loc of supportedLocales) {
        nextMap[loc] = blockToForm((data.locales[loc] as PortalSupportLocaleBlock) ?? {})
      }
      setLocalesMap(nextMap)
      setActiveLocale('fr')
      setForm(structuredClone(nextMap.fr))
    } catch (e) {
      console.error(e)
      toastError('Impossible de charger le module support portail')
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => {
    void loadPayload()
  }, [loadPayload])

  const completeness = useMemo(() => {
    const blocks = Object.fromEntries(
      supportedLocales.map((loc) => [loc, formToBlock(localesMap[loc])]),
    ) as Record<Locale, PortalSupportLocaleBlock>
    return computePortalSupportLocalesCompleteness(blocks)
  }, [localesMap])

  const handleLocaleChange = (next: Locale) => {
    if (next === activeLocale) return
    setLocalesMap((prev) => {
      const merged = { ...prev, [activeLocale]: structuredClone(form) }
      setActiveLocale(next)
      setForm(structuredClone(merged[next]))
      return merged
    })
  }

  const handleCopyFromDefault = () => {
    if (defaultLocaleState === activeLocale) {
      toastError('Sélectionnez une autre langue que la langue de secours.')
      return
    }
    setForm(structuredClone(localesMap[defaultLocaleState]))
    toastSuccess(`Contenu copié depuis ${LOCALE_LABEL[defaultLocaleState]}.`)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const mergedLocales = { ...localesMap, [activeLocale]: structuredClone(form) }
      const block = formToBlock(mergedLocales[activeLocale])

      const res = await fetch('/api/admin/portal-support', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'locale',
          locale: activeLocale,
          defaultLocale: defaultLocaleState,
          block,
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        toastError(typeof data.error === 'string' ? data.error : 'Enregistrement impossible')
        return
      }

      setLocalesMap(mergedLocales)
      toastSuccess('Module support portail enregistré.')
    } catch (e) {
      console.error(e)
      toastError('Enregistrement impossible')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">Chargement…</p>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Support portail (FAQ aside)</h1>
        <p className="mt-2 text-sm text-gray-600">
          Panneau affiché à droite dans l’app web connectée (dashboard, marchés, investissement).
          Publication immédiate après enregistrement.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {supportedLocales.map((loc) => (
          <button
            key={loc}
            type="button"
            onClick={() => handleLocaleChange(loc)}
            className={cn(
              'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
              activeLocale === loc
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
            )}
          >
            {LOCALE_LABEL[loc]}
          </button>
        ))}
        <LocaleCompletenessStrip levels={completeness} variant="inline" />
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <label className="flex items-center gap-2 text-sm text-gray-700">
          Langue de secours
          <select
            value={defaultLocaleState}
            onChange={(e) => setDefaultLocaleState(e.target.value as Locale)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            {supportedLocales.map((loc) => (
              <option key={loc} value={loc}>
                {LOCALE_LABEL[loc]}
              </option>
            ))}
          </select>
        </label>
        <Button type="button" variant="outline" size="sm" onClick={handleCopyFromDefault}>
          <Copy className="mr-2 h-4 w-4" />
          Copier depuis {LOCALE_LABEL[defaultLocaleState]}
        </Button>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <p className="mb-4 text-xs font-medium uppercase tracking-wide text-gray-500">
          Édition — {LOCALE_LABEL[activeLocale]}
        </p>

        <div className="grid gap-5">
          <Field label="Titre">
            <input
              className={inputClass}
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            />
          </Field>

          <Field label="Description">
            <textarea
              className={`${inputClass} min-h-[88px]`}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </Field>

          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Bouton principal — libellé">
              <input
                className={inputClass}
                value={form.ctaLabel}
                onChange={(e) => setForm((f) => ({ ...f, ctaLabel: e.target.value }))}
              />
            </Field>
            <Field label="Bouton principal — URL" hint="Chemin interne ou lien externe">
              <input
                className={inputClass}
                value={form.ctaHref}
                onChange={(e) => setForm((f) => ({ ...f, ctaHref: e.target.value }))}
              />
            </Field>
            <Field label="Lien secondaire — libellé">
              <input
                className={inputClass}
                value={form.secondaryLinkLabel}
                onChange={(e) => setForm((f) => ({ ...f, secondaryLinkLabel: e.target.value }))}
              />
            </Field>
            <Field label="Lien secondaire — URL">
              <input
                className={inputClass}
                value={form.secondaryLinkHref}
                onChange={(e) => setForm((f) => ({ ...f, secondaryLinkHref: e.target.value }))}
              />
            </Field>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <Button type="button" onClick={() => void handleSave()} disabled={saving}>
          {saving ? 'Enregistrement…' : 'Enregistrer'}
        </Button>
      </div>
    </div>
  )
}
