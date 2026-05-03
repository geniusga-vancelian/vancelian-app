'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Heading2, Monitor, Package, Rows3, Smartphone } from 'lucide-react'
import { useAdminEditingLocale } from '@/components/admin/AdminEditingLocaleContext'
import { isValidLocale, supportedLocales, type Locale } from '@/config/locales'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { getCatalogLayoutGroupForTypeKey } from '@/lib/sections/heroSlotPolicy'
import { BLOG_LIST_TEMPLATE_RENDER_CANONICAL_KEYS } from '@/lib/cms/blogListTemplateSectionPolicy'

type SectionTypeRow = {
  key: string
  label: string
  category: string
  description?: string
  adminGuide?: string
  allowedOnTemplates?: string[]
}

type CommonModuleRow = {
  id: string
  label: string
  sectionKey: string
}

type Selection =
  | { kind: 'standard'; key: string; label: string; adminGuide: string }
  | { kind: 'common'; id: string; label: string; sectionKey: string; adminGuide: string }

const EXCLUDED_TYPE_KEYS = new Set([
  'common_module_ref',
  'footer',
  'blog_article_related',
  'share_sm',
])

/** Largeur logique iframe bureau (px) — même référence que `PagePreviewPanel`. */
const DESKTOP_PREVIEW_W = 1280
const DESKTOP_PREVIEW_MIN_H = 560
const DESKTOP_PREVIEW_MAX_H = 24000
const MOBILE_PREVIEW_W = 390
const MOBILE_PREVIEW_H = 844

type PreviewDevice = 'desktop' | 'mobile'

function normalizeCatalogSearch(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
}

export default function AddModulePage() {
  const router = useRouter()
  const params = useParams()
  const slug = (params?.slug as string | undefined) ?? ''
  const { locale: editingLocale, setLocale: setEditingLocale } = useAdminEditingLocale()

  const [types, setTypes] = useState<SectionTypeRow[]>([])
  const [commonModules, setCommonModules] = useState<CommonModuleRow[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selected, setSelected] = useState<Selection | null>(null)
  const [previewLocale, setPreviewLocale] = useState<Locale>(editingLocale)
  const [pageTemplate, setPageTemplate] = useState<string>('homepage')
  /** Une page ne peut avoir qu’un module Hero au total (types catalogue ou module commun). */
  const [pageHasHero, setPageHasHero] = useState(false)
  const [catalogQuery, setCatalogQuery] = useState('')
  const [previewDevice, setPreviewDevice] = useState<PreviewDevice>('desktop')
  const previewViewportRef = useRef<HTMLDivElement>(null)
  const [desktopPreviewLayout, setDesktopPreviewLayout] = useState({ scale: 1, logicalH: 900 })

  useEffect(() => {
    setPreviewLocale(editingLocale)
  }, [editingLocale])

  useEffect(() => {
    if (!slug) {
      setLoading(false)
      return
    }
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const pageRes = await fetch(`/api/admin/pages/${encodeURIComponent(slug)}`)
        const pageJson = pageRes.ok ? await pageRes.json() : {}
        if (cancelled) return

        const template = pageJson.page?.template ?? 'homepage'
        const [tRes, mRes] = await Promise.all([
          fetch('/api/admin/section-types'),
          fetch('/api/admin/site-common-modules'),
        ])
        const tJson = tRes.ok ? await tRes.json() : {}
        const mJson = mRes.ok ? await mRes.json() : {}
        if (cancelled) return

        if (!cancelled) setPageTemplate(template)
        if (!cancelled) setPageHasHero(pageJson.page?.hasHeroModule === true)

        if (Array.isArray(mJson.modules)) {
          setCommonModules(mJson.modules)
        } else {
          setCommonModules([])
        }

        if (Array.isArray(tJson.types)) {
          const filtered = (tJson.types as SectionTypeRow[]).filter((t) => {
            if (EXCLUDED_TYPE_KEYS.has(t.key)) return false
            const allowed = t.allowedOnTemplates ?? []
            if (!allowed.includes(template) && !allowed.includes('default')) return false
            if (
              template === 'blog' &&
              !BLOG_LIST_TEMPLATE_RENDER_CANONICAL_KEYS.has(t.key)
            ) {
              return false
            }
            return true
          })
          setTypes(filtered)
        } else {
          setTypes([])
        }
      } catch (e) {
        console.error(e)
        toastError('Impossible de charger le catalogue')
        setTypes([])
        setCommonModules([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [slug])

  const filteredTypes = useMemo(() => {
    const q = normalizeCatalogSearch(catalogQuery)
    if (!q) return types
    return types.filter((t) => {
      const hay = normalizeCatalogSearch(
        [t.label, t.key, t.category, t.description ?? '', t.adminGuide ?? ''].join(' '),
      )
      return hay.includes(q)
    })
  }, [types, catalogQuery])

  const heroTypes = useMemo(
    () =>
      [...filteredTypes.filter((t) => getCatalogLayoutGroupForTypeKey(t.key) === 'hero')].sort((a, b) =>
        a.label.localeCompare(b.label, 'fr'),
      ),
    [filteredTypes],
  )

  const contentTypes = useMemo(
    () =>
      [...filteredTypes.filter((t) => getCatalogLayoutGroupForTypeKey(t.key) === 'content')].sort((a, b) =>
        a.label.localeCompare(b.label, 'fr'),
      ),
    [filteredTypes],
  )

  /** Tous les modules communs (Hero ou Contenu), filtrés par la recherche — section dédiée au milieu du catalogue. */
  const filteredCommonModules = useMemo(() => {
    const q = normalizeCatalogSearch(catalogQuery)
    let list = [...commonModules]
    if (pageTemplate === 'blog') {
      list = list.filter((m) =>
        BLOG_LIST_TEMPLATE_RENDER_CANONICAL_KEYS.has(m.sectionKey),
      )
    }
    if (q) {
      list = list.filter((m) => {
        const hay = normalizeCatalogSearch([m.label, m.sectionKey].join(' '))
        return hay.includes(q)
      })
    }
    return list.sort((a, b) => a.label.localeCompare(b.label, 'fr'))
  }, [commonModules, catalogQuery, pageTemplate])

  const previewUrl = useMemo(() => {
    if (!selected) return ''
    const loc = encodeURIComponent(previewLocale)
    if (selected.kind === 'common') {
      return `/preview/common-module/${encodeURIComponent(selected.id)}?locale=${loc}`
    }
    return `/preview/section-demo/${encodeURIComponent(selected.key)}?locale=${loc}`
  }, [selected, previewLocale])

  const iframeKey = previewUrl

  useEffect(() => {
    if (!selected || previewDevice !== 'desktop') return
    const el = previewViewportRef.current
    if (!el) return

    const measure = () => {
      const pad = 8
      const cw = Math.max(120, el.clientWidth - pad)
      const ch = Math.max(160, el.clientHeight - pad)
      const scale = Math.min(1, cw / DESKTOP_PREVIEW_W)
      const rawH = Math.ceil(ch / scale)
      const logicalH = Math.min(
        DESKTOP_PREVIEW_MAX_H,
        Math.max(DESKTOP_PREVIEW_MIN_H, rawH),
      )
      setDesktopPreviewLayout({ scale, logicalH })
    }

    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [selected, previewDevice, previewUrl])

  const selectStandard = useCallback((t: SectionTypeRow) => {
    const guide = (t.adminGuide || t.description || '').trim()
    setSelected({
      kind: 'standard',
      key: t.key,
      label: t.label,
      adminGuide: guide || 'Aucune description détaillée pour ce type.',
    })
  }, [])

  const selectCommon = useCallback((m: CommonModuleRow) => {
    setSelected({
      kind: 'common',
      id: m.id,
      label: m.label,
      sectionKey: m.sectionKey,
      adminGuide:
        `Module commun « ${m.label} » (type ${m.sectionKey}). Le rendu utilise le contenu et les traductions ` +
        `définis dans la zone 2 — Structure du site. Insérer ici ne fait que référencer ce bloc sur la page courante.`,
    })
  }, [])

  /** Hero déjà sur la page : prévisualisation OK, mais pas d’ajout d’un second Hero. */
  const validateHeroBlocked = useMemo(() => {
    if (!pageHasHero || !selected) return false
    if (selected.kind === 'standard') {
      return getCatalogLayoutGroupForTypeKey(selected.key) === 'hero'
    }
    return getCatalogLayoutGroupForTypeKey(selected.sectionKey) === 'hero'
  }, [pageHasHero, selected])

  const handleValidate = async () => {
    if (!selected || !slug) return
    setSaving(true)
    try {
      const body =
        selected.kind === 'common'
          ? { typeKey: 'common_module_ref', commonModuleId: selected.id }
          : { typeKey: selected.key }

      const res = await fetch(`/api/admin/pages/${encodeURIComponent(slug)}/sections/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(
          typeof data.error === 'string' ? data.error : 'Impossible d’ajouter ce module pour le moment.',
        )
      }
      toastSuccess(selected.kind === 'common' ? 'Module commun ajouté' : 'Module ajouté')
      router.push(`/admin/pages/${encodeURIComponent(slug)}`)
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  const backHref = `/admin/pages/${encodeURIComponent(slug)}`

  if (!slug) {
    return (
      <div className="p-8">
        <p className="text-slate-600">Slug de page manquant.</p>
        <Link href="/admin/pages" className="text-indigo-600">
          Retour
        </Link>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-[80] flex flex-col bg-slate-100">
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex min-w-0 items-center gap-3">
          <Link
            href={backHref}
            className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            ← Retour à la page
          </Link>
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold text-slate-900">Choisir un module</h1>
            <p className="truncate text-xs text-slate-500">
              Page <span className="font-mono">{slug}</span> — sélectionnez un type, vérifiez l’aperçu, puis validez.
              {pageTemplate === 'blog' ? (
                <>
                  {' '}
                  <span className="font-medium text-slate-600">
                    Gabarit blog : seuls les modules affichés sur la liste publique sont proposés (à la une,
                    mosaïque, flux, CTA).
                  </span>
                </>
              ) : null}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-[10px] font-semibold uppercase text-slate-400">Aperçu</span>
          <select
            value={previewLocale}
            onChange={(e) => {
              const v = e.target.value
              if (isValidLocale(v)) {
                setPreviewLocale(v)
                setEditingLocale(v)
              }
            }}
            className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs font-medium text-slate-800"
          >
            {supportedLocales.map((loc) => (
              <option key={loc} value={loc}>
                {loc.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className="grid min-h-0 min-w-0 flex-1 grid-cols-1 gap-0 md:grid-cols-[minmax(0,3fr)_minmax(0,7fr)]">
        <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden border-r border-slate-200 bg-white">
          <div className="shrink-0 border-b border-slate-100 bg-white px-3 py-2">
            <label htmlFor="add-module-search" className="sr-only">
              Filtrer les modules
            </label>
            <input
              id="add-module-search"
              type="search"
              value={catalogQuery}
              onChange={(e) => setCatalogQuery(e.target.value)}
              placeholder="Rechercher (média, stats, blog…)"
              autoComplete="off"
              className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            {pageTemplate === 'vault_builder' ? (
              <p className="mt-1.5 text-[10px] leading-snug text-amber-900/90">
                Offre <span className="font-mono">vault_builder</span> : contenu Vault dans{' '}
                <Link href="/admin/vault-builder" className="font-medium text-indigo-700 underline">
                  Vault Builder
                </Link>
                . Ici : blocs CMS pour la page.
              </p>
            ) : null}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            {loading ? (
              <div className="p-4 text-xs text-slate-500">Chargement du catalogue…</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {pageHasHero ? (
                  <div className="border-b border-amber-200 bg-amber-50 px-2.5 py-2 text-[11px] leading-snug text-amber-950">
                    <strong className="font-semibold">Un Hero est déjà présent sur cette page.</strong>{' '}
                    Vous pouvez toutefois cliquer sur un module Hero pour{' '}
                    <span className="font-medium">l’aperçu catalogue</span> ; le bouton{' '}
                    <span className="font-medium">Valider</span> ne s’active pas pour un Hero tant que le bloc
                    actuel n’a pas été retiré (un seul Hero par page).
                  </div>
                ) : null}

                <div className="sticky top-0 z-[1] bg-violet-50/95 px-2.5 py-1 backdrop-blur-sm">
                  <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-violet-900">
                    <Heading2 className="h-3.5 w-3.5 shrink-0" aria-hidden />
                    Hero
                  </div>
                  <p className="mt-0.5 text-[10px] font-normal normal-case leading-snug text-violet-800/90">
                    Types catalogue — en-tête principal. <span className="font-medium">Un seul</span> Hero par page
                    (y compris si vous insérez un <span className="font-medium">module commun</span> de type Hero
                    ci-dessous).
                  </p>
                </div>
                {heroTypes.length === 0 ? (
                  <p className="px-2.5 py-3 text-[11px] text-slate-500">
                    {normalizeCatalogSearch(catalogQuery)
                      ? 'Aucun type Hero ne correspond à votre recherche.'
                      : 'Aucun type Hero disponible pour ce gabarit.'}
                  </p>
                ) : (
                  <>
                    {heroTypes.map((t) => {
                      const active = selected?.kind === 'standard' && selected.key === t.key
                      return (
                        <button
                          key={t.key}
                          type="button"
                          title={`${t.category} · ${t.key}`}
                          onClick={() => selectStandard(t)}
                          className={cn(
                            'flex w-full items-center gap-2 border-l-[3px] border-transparent px-2 py-1.5 text-left text-xs transition hover:bg-slate-50',
                            active && 'border-l-indigo-600 bg-indigo-50/70',
                          )}
                        >
                          <span className="min-w-0 flex-1 truncate font-medium text-slate-900">{t.label}</span>
                          <span className="shrink-0 truncate font-mono text-[10px] text-slate-400">{t.key}</span>
                        </button>
                      )
                    })}
                  </>
                )}

                <div className="sticky top-0 z-[1] bg-sky-50/95 px-2.5 py-1 backdrop-blur-sm">
                  <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-sky-900">
                    <Package className="h-3.5 w-3.5 shrink-0" aria-hidden />
                    Module commun
                  </div>
                  <p className="mt-0.5 text-[10px] font-normal normal-case leading-snug text-sky-900/85">
                    Réutilisables — gérés dans <span className="font-medium">Structure du site</span> (zone modules
                    communs). Peuvent être de type Hero ou Contenu.
                  </p>
                </div>
                {filteredCommonModules.length === 0 ? (
                  <p className="px-2.5 py-3 text-[11px] text-slate-500">
                    {commonModules.length === 0
                      ? 'Aucun module commun — créez-en dans Structure du site.'
                      : normalizeCatalogSearch(catalogQuery)
                        ? 'Aucun module commun ne correspond à votre recherche.'
                        : 'Aucun module commun pour ce site.'}
                  </p>
                ) : (
                  filteredCommonModules.map((m) => {
                    const active = selected?.kind === 'common' && selected.id === m.id
                    const isHeroCommon = getCatalogLayoutGroupForTypeKey(m.sectionKey) === 'hero'
                    return (
                      <button
                        key={m.id}
                        type="button"
                        title={`${m.sectionKey}${isHeroCommon ? ' · Hero' : ''}`}
                        onClick={() => selectCommon(m)}
                        className={cn(
                          'flex w-full items-center gap-2 border-l-[3px] border-transparent px-2 py-1.5 text-left text-xs transition hover:bg-slate-50',
                          active && 'border-l-indigo-600 bg-indigo-50/70',
                        )}
                      >
                        <span className="min-w-0 flex-1 truncate font-medium text-slate-900">
                          {m.label}
                          <span className="ml-1 font-normal text-slate-500">(commun)</span>
                          {isHeroCommon ? (
                            <span className="ml-1.5 rounded bg-violet-100 px-1 py-px text-[9px] font-semibold uppercase tracking-wide text-violet-800">
                              Hero
                            </span>
                          ) : null}
                        </span>
                        <span className="shrink-0 truncate font-mono text-[10px] text-slate-400">{m.sectionKey}</span>
                      </button>
                    )
                  })
                )}

                <div className="sticky top-0 z-[1] bg-slate-100/95 px-2.5 py-1 backdrop-blur-sm">
                  <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-700">
                    <Rows3 className="h-3.5 w-3.5 shrink-0" aria-hidden />
                    Contenu
                  </div>
                  <p className="mt-0.5 text-[10px] font-normal normal-case leading-snug text-slate-600">
                    Types catalogue hors Hero (FAQ, média, grilles, blog, etc.).
                  </p>
                </div>
                {contentTypes.length === 0 ? (
                  <p className="px-2.5 py-4 text-center text-[11px] text-slate-500">
                    Aucun résultat — effacez le filtre ou essayez « figma », « blog », « FAQ »…
                  </p>
                ) : (
                  <>
                    {contentTypes.map((t) => {
                      const active = selected?.kind === 'standard' && selected.key === t.key
                      return (
                        <button
                          key={t.key}
                          type="button"
                          title={`${t.category} · ${t.key}`}
                          onClick={() => selectStandard(t)}
                          className={cn(
                            'flex w-full items-center gap-2 border-l-[3px] border-transparent px-2 py-1.5 text-left text-xs transition hover:bg-slate-50',
                            active && 'border-l-indigo-600 bg-indigo-50/70',
                          )}
                        >
                          <span className="min-w-0 flex-1 truncate font-medium text-slate-900">{t.label}</span>
                          <span className="shrink-0 truncate font-mono text-[10px] text-slate-400">{t.key}</span>
                        </button>
                      )
                    })}
                  </>
                )}
              </div>
            )}
          </div>
        </aside>

        <section className="flex min-h-0 min-w-0 flex-col bg-slate-200/80">
          {!selected ? (
            <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-slate-500">
              Choisissez un module dans la liste à gauche pour afficher sa description et un aperçu générique (données
              d’exemple du catalogue).
            </div>
          ) : (
            <>
              <div className="shrink-0 border-b border-slate-200 bg-white px-6 py-4 shadow-sm">
                <h2 className="text-base font-semibold text-slate-900">{selected.label}</h2>
                {selected.kind === 'common' ? (
                  <p className="mt-0.5 font-mono text-xs text-slate-500">{selected.sectionKey}</p>
                ) : (
                  <p className="mt-0.5 font-mono text-xs text-slate-500">{selected.key}</p>
                )}
                <p className="mt-3 text-sm leading-relaxed text-slate-700">{selected.adminGuide}</p>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-slate-200 bg-slate-50/90 px-4 py-2">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Vue</span>
                <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 shadow-sm">
                  <button
                    type="button"
                    onClick={() => setPreviewDevice('desktop')}
                    className={cn(
                      'inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium transition',
                      previewDevice === 'desktop'
                        ? 'bg-slate-100 text-slate-900 shadow-sm'
                        : 'text-slate-500 hover:text-slate-800',
                    )}
                    aria-pressed={previewDevice === 'desktop'}
                  >
                    <Monitor className="h-3.5 w-3.5" aria-hidden />
                    Bureau
                  </button>
                  <button
                    type="button"
                    onClick={() => setPreviewDevice('mobile')}
                    className={cn(
                      'inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium transition',
                      previewDevice === 'mobile'
                        ? 'bg-slate-100 text-slate-900 shadow-sm'
                        : 'text-slate-500 hover:text-slate-800',
                    )}
                    aria-pressed={previewDevice === 'mobile'}
                  >
                    <Smartphone className="h-3.5 w-3.5" aria-hidden />
                    Mobile
                  </button>
                </div>
                {previewDevice === 'desktop' && desktopPreviewLayout.scale < 0.999 ? (
                  <span className="text-[10px] tabular-nums text-slate-500">
                    Zoom {Math.round(desktopPreviewLayout.scale * 100)} % · {DESKTOP_PREVIEW_W}×
                    {desktopPreviewLayout.logicalH}px
                  </span>
                ) : null}
              </div>
              <div
                ref={previewViewportRef}
                className={cn(
                  'min-h-0 flex-1 overflow-auto bg-slate-200/90 p-2',
                  previewDevice === 'mobile' && 'flex flex-col items-center',
                )}
              >
                {previewDevice === 'mobile' ? (
                  <div
                    className="shrink-0 overflow-hidden rounded-[2rem] border-[10px] border-slate-800 bg-slate-800 shadow-2xl"
                    style={{
                      width: MOBILE_PREVIEW_W + 20,
                      maxWidth: '100%',
                    }}
                  >
                    <div className="overflow-hidden rounded-[1.35rem] bg-white">
                      <iframe
                        key={iframeKey}
                        title="Aperçu module — mobile"
                        src={previewUrl}
                        className="block border-0 bg-white"
                        sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
                        style={{ width: MOBILE_PREVIEW_W, height: MOBILE_PREVIEW_H }}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="flex min-h-full min-w-0 w-full flex-1 items-start justify-center">
                    <div
                      className="shrink-0"
                      style={{
                        width: DESKTOP_PREVIEW_W * desktopPreviewLayout.scale,
                        height: desktopPreviewLayout.logicalH * desktopPreviewLayout.scale,
                        position: 'relative',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          width: DESKTOP_PREVIEW_W,
                          height: desktopPreviewLayout.logicalH,
                          transform: `scale(${desktopPreviewLayout.scale})`,
                          transformOrigin: 'top left',
                          position: 'absolute',
                          top: 0,
                          left: 0,
                        }}
                      >
                        <iframe
                          key={iframeKey}
                          title="Aperçu module — bureau"
                          src={previewUrl}
                          className="block border-0 bg-white"
                          sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
                          style={{
                            width: DESKTOP_PREVIEW_W,
                            height: desktopPreviewLayout.logicalH,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </div>

      <footer className="flex shrink-0 flex-wrap items-center justify-end gap-3 border-t border-slate-200 bg-white px-6 py-4 shadow-[0_-4px_12px_rgba(0,0,0,0.06)]">
        {validateHeroBlocked ? (
          <p className="mr-auto max-w-xl text-xs leading-snug text-amber-900">
            <span className="font-medium">Ajout impossible :</span> cette page a déjà son Hero. Retirez ou remplacez
            le bloc existant pour en ajouter un autre — l’aperçu ci-dessus reste consultable.
          </p>
        ) : null}
        <Link
          href={backHref}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Annuler
        </Link>
        <Button
          type="button"
          disabled={!selected || saving || validateHeroBlocked}
          title={
            validateHeroBlocked
              ? 'Un seul Hero par page : retirez le bloc Hero actuel pour valider celui-ci.'
              : undefined
          }
          onClick={() => void handleValidate()}
          className="min-w-[200px]"
        >
          {saving ? 'Ajout…' : 'Valider ce module'}
        </Button>
      </footer>
    </div>
  )
}
