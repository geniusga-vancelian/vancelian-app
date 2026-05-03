'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Copy, PlusCircle, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MediaField } from '@/components/admin/MediaField'
import { LanguageCheckActions } from '@/components/admin/LanguageCheckActions'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import type { FooterJsonInput, FooterSocialPlatform } from '@/lib/sections/library'
import type { Locale } from '@/config/locales'
import { supportedLocales } from '@/config/locales'
import { computeFooterLocalesCompleteness } from '@/lib/admin/footerLocaleCompleteness'
import { LocaleCompletenessStrip } from '@/components/admin/LocaleCompletenessStrip'
import { cn } from '@/lib/utils'

const SOCIAL_PLATFORM_OPTIONS: { value: FooterSocialPlatform; label: string }[] = [
  { value: 'youtube', label: 'YouTube' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'x', label: 'X' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'other', label: 'Autre (icône lien)' },
]

const LOCALE_LABEL: Record<Locale, string> = {
  fr: 'Français',
  en: 'English',
  it: 'Italiano',
}

type LinkRow = { label: string; href: string; category: string }

export type SiteFooterFormState = {
  copyright: string
  description: string
  backgroundColor: string
  logoMediaId: string | null
  newsletterVisible: boolean
  newsletterTitle: string
  newsletterPlaceholder: string
  newsletterButtonLabel: string
  legalTexts: string[]
  socialLinks: Array<{ platform: FooterSocialPlatform; href: string }>
  links: LinkRow[]
}

function emptyLinkRow(): LinkRow {
  return { label: '', href: '', category: '' }
}

export function initialFooterForm(): SiteFooterFormState {
  return {
    copyright: '',
    description: '',
    backgroundColor: '#000000',
    logoMediaId: null,
    newsletterVisible: true,
    newsletterTitle: 'Subscribe to our newsletter',
    newsletterPlaceholder: 'Enter your email',
    newsletterButtonLabel: 'subscribe',
    legalTexts: [''],
    socialLinks: [],
    links: [emptyLinkRow()],
  }
}

function cloneForm(f: SiteFooterFormState): SiteFooterFormState {
  return structuredClone(f)
}

function footerBlockToForm(f: Record<string, unknown>): SiteFooterFormState {
  const linksRaw = f.links as Array<{ label?: string; href?: string; category?: string }> | undefined
  const links: LinkRow[] =
    linksRaw && linksRaw.length > 0
      ? linksRaw.map((l) => ({
          label: l.label || '',
          href: l.href || '',
          category: l.category || '',
        }))
      : [emptyLinkRow()]

  return {
    copyright: typeof f.copyright === 'string' ? f.copyright : '',
    description: typeof f.description === 'string' ? f.description : '',
    backgroundColor: typeof f.backgroundColor === 'string' && f.backgroundColor ? f.backgroundColor : '#000000',
    logoMediaId: typeof f.logoMediaId === 'string' ? f.logoMediaId : null,
    newsletterVisible: f.newsletterVisible !== false,
    newsletterTitle:
      typeof f.newsletterTitle === 'string' && f.newsletterTitle
        ? f.newsletterTitle
        : 'Subscribe to our newsletter',
    newsletterPlaceholder:
      typeof f.newsletterPlaceholder === 'string' && f.newsletterPlaceholder
        ? f.newsletterPlaceholder
        : 'Enter your email',
    newsletterButtonLabel:
      typeof f.newsletterButtonLabel === 'string' && f.newsletterButtonLabel
        ? f.newsletterButtonLabel
        : 'subscribe',
    legalTexts: Array.isArray(f.legalTexts) && f.legalTexts.length ? [...(f.legalTexts as string[])] : [''],
    socialLinks: Array.isArray(f.socialLinks) ? [...(f.socialLinks as SiteFooterFormState['socialLinks'])] : [],
    links,
  }
}

function formToFooterBlock(form: SiteFooterFormState): Record<string, unknown> {
  const links = form.links
    .filter((l) => l.label.trim() && l.href.trim())
    .map((l) => ({
      label: l.label.trim(),
      href: l.href.trim(),
      ...(l.category.trim() ? { category: l.category.trim() } : {}),
    }))
  const legalTexts = form.legalTexts.map((t) => t.trim()).filter(Boolean)
  const socialLinks = form.socialLinks.filter((s) => s.href.trim())

  return {
    copyright: form.copyright.trim() || undefined,
    description: form.description.trim() || undefined,
    backgroundColor: form.backgroundColor.trim() || undefined,
    logoMediaId: form.logoMediaId,
    newsletterVisible: form.newsletterVisible,
    newsletterTitle: form.newsletterTitle.trim() || undefined,
    newsletterPlaceholder: form.newsletterPlaceholder.trim() || undefined,
    newsletterButtonLabel: form.newsletterButtonLabel.trim() || undefined,
    legalTexts: legalTexts.length ? legalTexts : undefined,
    socialLinks: socialLinks.length ? socialLinks : undefined,
    links: links.length ? links : undefined,
  }
}

function emptyLocalesMap(): Record<Locale, SiteFooterFormState> {
  return {
    fr: initialFooterForm(),
    en: initialFooterForm(),
    it: initialFooterForm(),
  }
}

export function SiteFooterEditor() {
  const router = useRouter()
  const [activeLocale, setActiveLocale] = useState<Locale>('fr')
  const [defaultLocale, setDefaultLocale] = useState<Locale>('fr')
  const [localesMap, setLocalesMap] = useState<Record<Locale, SiteFooterFormState>>(emptyLocalesMap)
  const [form, setForm] = useState<SiteFooterFormState>(() => initialFooterForm())
  const [isLegacyStorage, setIsLegacyStorage] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const loadPayload = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/admin/site-footer')
      const data = await res.json()
      if (data.error === 'Unauthorized') {
        router.push('/admin/login')
        return
      }
      if (!data.locales || typeof data.locales !== 'object') {
        toastError('Réponse footer inattendue')
        return
      }

      const dl = (data.defaultLocale as Locale) ?? 'fr'
      setDefaultLocale(supportedLocales.includes(dl) ? dl : 'fr')
      setIsLegacyStorage(Boolean(data.isLegacyStorage))

      const nextMap = emptyLocalesMap()
      for (const loc of supportedLocales) {
        nextMap[loc] = footerBlockToForm((data.locales[loc] as Record<string, unknown>) ?? {})
      }
      setLocalesMap(nextMap)
      setActiveLocale('fr')
      setForm(cloneForm(nextMap.fr))
    } catch (e) {
      console.error(e)
      toastError('Impossible de charger le footer')
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => {
    loadPayload()
  }, [loadPayload])

  const commitCurrentToMap = useCallback(
    (map: Record<Locale, SiteFooterFormState>, locale: Locale, state: SiteFooterFormState) => ({
      ...map,
      [locale]: state,
    }),
    [],
  )

  const handleLocaleChange = (next: Locale) => {
    if (next === activeLocale) return
    setLocalesMap((prev) => {
      const merged = commitCurrentToMap(prev, activeLocale, form)
      setActiveLocale(next)
      setForm(cloneForm(merged[next]))
      return merged
    })
  }

  const handleCopyFromDefault = () => {
    if (defaultLocale === activeLocale) {
      toastError('Vous éditez déjà la langue par défaut.')
      return
    }
    setLocalesMap((prev) => {
      const merged = commitCurrentToMap(prev, activeLocale, form)
      const src = merged[defaultLocale]
      const nextForm = src ? cloneForm(src) : initialFooterForm()
      setForm(nextForm)
      return { ...merged, [activeLocale]: nextForm }
    })
    toastSuccess(`Contenu copié depuis ${LOCALE_LABEL[defaultLocale]}`)
  }

  /** Pastilles FR/EN/IT : reflètent le brouillon courant (toutes les langues du formulaire). */
  const footerCompletenessByLocale = useMemo(() => {
    const locales = {} as Record<Locale, FooterJsonInput>
    for (const loc of supportedLocales) {
      const st = loc === activeLocale ? form : localesMap[loc]
      locales[loc] = formToFooterBlock(st) as FooterJsonInput
    }
    return computeFooterLocalesCompleteness(locales)
  }, [localesMap, activeLocale, form])

  const handleSave = async () => {
    setSaving(true)
    try {
      const merged = commitCurrentToMap(localesMap, activeLocale, form)
      const block = formToFooterBlock(merged[activeLocale])

      const res = await fetch('/api/admin/site-footer', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'locale',
          locale: activeLocale,
          defaultLocale,
          block,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Save failed')
      }
      toastSuccess('Footer enregistré')
      await loadPayload()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur à l’enregistrement')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="py-12 text-center text-gray-500">Chargement…</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">Footer du site</h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-600">
              Module global en pied de page : textes par langue du visiteur. Les changements non enregistrés sont inclus
              dans l’aperçu des pastilles ci-dessous.
            </p>
          </div>
          <div className="flex flex-col gap-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
              Complétude (brouillon)
            </span>
            <LocaleCompletenessStrip levels={footerCompletenessByLocale} variant="inline" />
          </div>
        </div>

        {isLegacyStorage ? (
          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <strong className="font-medium">Format classique détecté.</strong> Le contenu est chargé en français. Le
            prochain enregistrement le convertira au format multilingue (v2) dans la base, sans perte de données.
          </div>
        ) : null}

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50/70 px-4 py-3">
          <div className="text-xs text-slate-600">
            <p className="font-semibold uppercase tracking-wide text-slate-700">Contrôle linguistique</p>
            <p className="mt-1 max-w-md leading-snug">
              Analyse (copyright, description, liens, newsletter, mentions) pour la langue sélectionnée, puis correction
              assistée si besoin.
            </p>
          </div>
          <LanguageCheckActions
            domainLabel="footer"
            scanUrl="/api/admin/site-footer/check-language/scan"
            applyUrl="/api/admin/site-footer/check-language/apply"
            activeLocale={activeLocale}
            localeLabel={LOCALE_LABEL[activeLocale]}
            onApplied={loadPayload}
            disabled={loading || saving}
          />
        </div>

        <div className="mt-6 flex flex-col gap-4 rounded-xl border border-indigo-100 bg-indigo-50/40 p-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-900">Langue éditée</p>
            <p className="mt-0.5 text-[11px] text-indigo-900/85">
              Un seul ensemble de champs à l’écran ; enregistrez pour persister cette locale sans toucher aux autres.
            </p>
            <div className="mt-3 flex flex-wrap gap-2" role="tablist" aria-label="Choisir la langue du footer">
              {supportedLocales.map((loc) => (
                <button
                  key={loc}
                  type="button"
                  role="tab"
                  aria-selected={activeLocale === loc}
                  onClick={() => handleLocaleChange(loc)}
                  className={cn(
                    'rounded-lg border px-3 py-2 text-sm font-medium transition',
                    activeLocale === loc
                      ? 'border-indigo-500 bg-white text-indigo-950 shadow-sm'
                      : 'border-transparent bg-white/60 text-slate-700 hover:border-slate-200 hover:bg-white',
                  )}
                >
                  {LOCALE_LABEL[loc]}{' '}
                  <span className="text-xs font-normal text-slate-500">({loc})</span>
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 border-t border-indigo-100/80 pt-3">
            <Button type="button" variant="outline" size="sm" onClick={handleCopyFromDefault}>
              <Copy className="mr-2 h-4 w-4" />
              Copier depuis {LOCALE_LABEL[defaultLocale]}
            </Button>
          </div>
          <details className="rounded-lg border border-indigo-200/80 bg-white/80 p-3 text-sm">
            <summary className="cursor-pointer font-medium text-indigo-950">
              Paramètres du document — langue de secours
            </summary>
            <div className="mt-3 max-w-md">
              <label className="block text-xs text-slate-600">
                <span className="mb-1 block font-medium text-slate-800">Fallback runtime</span>
                <select
                  value={defaultLocale}
                  onChange={(e) => setDefaultLocale(e.target.value as Locale)}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
                  aria-label="Locale par défaut du document footer"
                >
                  {supportedLocales.map((loc) => (
                    <option key={loc} value={loc}>
                      {LOCALE_LABEL[loc]}
                    </option>
                  ))}
                </select>
                <span className="mt-1 block text-[11px] text-slate-500">
                  Utilisée si une langue n’a pas encore de bloc enregistré côté serveur.
                </span>
              </label>
            </div>
          </details>
        </div>

        <div className="mt-8 space-y-6">
          <section className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/40 p-5">
            <h3 className="text-lg font-medium text-gray-900">Apparence</h3>
            <div className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Couleur de fond</label>
                <div className="flex flex-wrap items-center gap-3">
                  <input
                    type="color"
                    value={form.backgroundColor.match(/^#([0-9a-fA-F]{6})$/) ? form.backgroundColor : '#000000'}
                    onChange={(e) => setForm((f) => ({ ...f, backgroundColor: e.target.value }))}
                    className="h-10 w-14 cursor-pointer rounded border border-gray-300 bg-white"
                    aria-label="Choix couleur"
                  />
                  <input
                    type="text"
                    value={form.backgroundColor}
                    onChange={(e) => setForm((f) => ({ ...f, backgroundColor: e.target.value }))}
                    className="min-w-[10rem] flex-1 rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500"
                    placeholder="#000000"
                  />
                </div>
                <p className="mt-1 text-xs text-gray-500">Valeur CSS (hex recommandé, ex. #0a0a0a).</p>
              </div>
            </div>
          </section>

          <section className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/40 p-5">
            <h3 className="text-lg font-medium text-gray-900">Logo (marque)</h3>
            <MediaField
              label="Image du logo"
              value={form.logoMediaId}
              onChange={(id) => setForm((f) => ({ ...f, logoMediaId: id }))}
              allowClear
            />
            <p className="text-xs text-gray-500">
              Si aucun média n’est choisi, le logo vectoriel Arquantix par défaut est utilisé.
            </p>
          </section>

          <section className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/40 p-5">
            <h3 className="text-lg font-medium text-gray-900">Textes principaux</h3>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Copyright</label>
              <input
                type="text"
                value={form.copyright}
                onChange={(e) => setForm((f) => ({ ...f, copyright: e.target.value }))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                placeholder="© 2026 Arquantix…"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Description (sous le logo)</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                rows={3}
                className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                placeholder="Tagline institutionnelle…"
              />
            </div>
          </section>

          <section className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/40 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-lg font-medium text-gray-900">Newsletter</h3>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={form.newsletterVisible}
                  onChange={(e) => setForm((f) => ({ ...f, newsletterVisible: e.target.checked }))}
                  className="rounded border-gray-300"
                />
                Afficher le bloc newsletter
              </label>
            </div>
            {form.newsletterVisible ? (
              <div className="grid gap-4 md:grid-cols-1">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Titre</label>
                  <input
                    type="text"
                    value={form.newsletterTitle}
                    onChange={(e) => setForm((f) => ({ ...f, newsletterTitle: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Placeholder e-mail</label>
                  <input
                    type="text"
                    value={form.newsletterPlaceholder}
                    onChange={(e) => setForm((f) => ({ ...f, newsletterPlaceholder: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Libellé du bouton</label>
                  <input
                    type="text"
                    value={form.newsletterButtonLabel}
                    onChange={(e) => setForm((f) => ({ ...f, newsletterButtonLabel: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                    placeholder="subscribe"
                  />
                </div>
              </div>
            ) : null}
          </section>

          <section className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/40 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-lg font-medium text-gray-900">Réseaux sociaux</h3>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    socialLinks: [...f.socialLinks, { platform: 'youtube', href: '' }],
                  }))
                }
              >
                <PlusCircle className="mr-2 h-4 w-4" />
                Ajouter un lien
              </Button>
            </div>
            {form.socialLinks.length === 0 ? (
              <p className="text-sm text-gray-500">Aucune icône affichée tant qu’aucun lien n’est défini.</p>
            ) : (
              <div className="space-y-2">
                {form.socialLinks.map((row, index) => (
                  <div key={index} className="flex flex-wrap items-center gap-2 rounded-lg border border-gray-200 p-3">
                    <select
                      value={row.platform}
                      onChange={(e) => {
                        const platform = e.target.value as FooterSocialPlatform
                        setForm((f) => {
                          const socialLinks = [...f.socialLinks]
                          socialLinks[index] = { ...socialLinks[index], platform }
                          return { ...f, socialLinks }
                        })
                      }}
                      className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                    >
                      {SOCIAL_PLATFORM_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                    <input
                      type="text"
                      value={row.href}
                      onChange={(e) => {
                        const href = e.target.value
                        setForm((f) => {
                          const socialLinks = [...f.socialLinks]
                          socialLinks[index] = { ...socialLinks[index], href }
                          return { ...f, socialLinks }
                        })
                      }}
                      className="min-w-[12rem] flex-1 rounded-md border border-gray-300 px-2 py-1.5 font-mono text-sm"
                      placeholder="https://…"
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setForm((f) => ({
                          ...f,
                          socialLinks: f.socialLinks.filter((_, i) => i !== index),
                        }))
                      }
                      className="text-gray-500 hover:text-red-600"
                      aria-label="Retirer"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/40 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-lg font-medium text-gray-900">Textes légaux (disclaimers)</h3>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setForm((f) => ({ ...f, legalTexts: [...f.legalTexts, ''] }))}
              >
                <PlusCircle className="mr-2 h-4 w-4" />
                Ajouter un paragraphe
              </Button>
            </div>
            <p className="text-xs text-gray-500">
              Affichés sous le copyright, en gris. Laissez vide pour ne rien afficher (sauf copyright).
            </p>
            <div className="space-y-2">
              {form.legalTexts.map((text, index) => (
                <div key={index} className="flex gap-2">
                  <textarea
                    value={text}
                    onChange={(e) => {
                      const v = e.target.value
                      setForm((f) => {
                        const legalTexts = [...f.legalTexts]
                        legalTexts[index] = v
                        return { ...f, legalTexts }
                      })
                    }}
                    rows={3}
                    className="min-h-[80px] flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
                    placeholder="Mentions légales, risques, etc."
                  />
                  <button
                    type="button"
                    onClick={() =>
                      setForm((f) => ({
                        ...f,
                        legalTexts:
                          f.legalTexts.length <= 1 ? [''] : f.legalTexts.filter((_, i) => i !== index),
                      }))
                    }
                    className="self-start text-gray-500 hover:text-red-600"
                    aria-label="Retirer"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-4 rounded-xl border border-slate-200 bg-slate-50/40 p-5">
            <div className="flex justify-between">
              <h3 className="text-lg font-medium text-gray-900">Liens par colonne</h3>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setForm((f) => ({ ...f, links: [...f.links, emptyLinkRow()] }))}
              >
                <PlusCircle className="mr-2 h-4 w-4" />
                Ajouter un lien
              </Button>
            </div>
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Catégorie</th>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Libellé</th>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">URL</th>
                    <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {form.links.map((row, index) => (
                    <tr key={index}>
                      <td className="px-4 py-2">
                        <input
                          type="text"
                          value={row.category}
                          onChange={(e) => {
                            const v = e.target.value
                            setForm((f) => {
                              const links = [...f.links]
                              links[index] = { ...links[index], category: v }
                              return { ...f, links }
                            })
                          }}
                          className="w-full min-w-[120px] rounded border border-gray-200 px-2 py-1 text-sm"
                          placeholder="ex. Legal"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <input
                          type="text"
                          value={row.label}
                          onChange={(e) => {
                            const v = e.target.value
                            setForm((f) => {
                              const links = [...f.links]
                              links[index] = { ...links[index], label: v }
                              return { ...f, links }
                            })
                          }}
                          className="w-full min-w-[140px] rounded border border-gray-200 px-2 py-1 text-sm"
                          placeholder="Privacy"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <input
                          type="text"
                          value={row.href}
                          onChange={(e) => {
                            const v = e.target.value
                            setForm((f) => {
                              const links = [...f.links]
                              links[index] = { ...links[index], href: v }
                              return { ...f, links }
                            })
                          }}
                          className="w-full min-w-[160px] rounded border border-gray-200 px-2 py-1 font-mono text-sm"
                          placeholder="/privacy"
                        />
                      </td>
                      <td className="px-4 py-2 text-right">
                        <button
                          type="button"
                          onClick={() =>
                            setForm((f) => ({
                              ...f,
                              links: f.links.length <= 1 ? [emptyLinkRow()] : f.links.filter((_, i) => i !== index),
                            }))
                          }
                          className="text-sm text-red-600 hover:text-red-800"
                        >
                          Retirer
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

        </div>
      </div>

      <div className="sticky bottom-2 z-10 flex flex-col gap-2 rounded-xl border border-slate-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-slate-600">
          Persistance :{' '}
          <span className="font-semibold text-slate-900">{LOCALE_LABEL[activeLocale]}</span> — les autres langues ne sont
          pas modifiées tant que vous ne les enregistrez pas.
        </p>
        <Button type="button" onClick={() => void handleSave()} disabled={saving}>
          {saving ? 'Enregistrement…' : `Enregistrer · ${LOCALE_LABEL[activeLocale]}`}
        </Button>
      </div>
    </div>
  )
}
