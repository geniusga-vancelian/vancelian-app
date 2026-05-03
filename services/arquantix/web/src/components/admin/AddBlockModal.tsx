'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { Monitor, Smartphone } from 'lucide-react'
import { isValidLocale, supportedLocales, type Locale, defaultLocale } from '@/config/locales'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  BLOCK_CATALOG,
  type AddableBlockType,
} from '@/lib/admin/articleBlockCatalog'

const DESKTOP_PREVIEW_W = 1280
const DESKTOP_PREVIEW_MIN_H = 560
const DESKTOP_PREVIEW_MAX_H = 24000
const MOBILE_PREVIEW_W = 390
const MOBILE_PREVIEW_H = 844

type PreviewDevice = 'desktop' | 'mobile'

export type AddBlockSelection = {
  type: AddableBlockType
  label: string
  category: string
  description: string
  hint?: string
}

export interface AddBlockModalProps {
  /** Lien de retour (vers l'éditeur de l'entité parent). */
  backHref: string
  /** Titre principal du header. */
  headerTitle: string
  /** Sous-titre du header (1 ligne). */
  headerSubtitle?: string
  /** Libellé bouton retour. */
  backLabel?: string
  /** Callback de validation : le parent appelle l'API ad hoc et navigue. */
  onValidate: (selection: AddBlockSelection, previewLocale: Locale) => Promise<void>
  /** Locale initiale pour la preview (par défaut `defaultLocale`). */
  initialPreviewLocale?: Locale
}

function normalizeCatalogSearch(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
}

/**
 * Modale plein écran « Ajouter un bloc » réutilisable. Extraite de
 * `src/app/admin/articles/[id]/add-block/page.tsx` pour permettre l'admin
 * Help (et le futur hub `/admin/content`) d'utiliser exactement le même
 * pattern Page Builder (liste catégorisée à gauche + aperçu live à droite +
 * footer sticky), sans dupliquer la logique iframe / mesure / catalogue.
 *
 * La preview utilise `/preview/article-block-demo/[type]` (déjà partagé entre
 * tous les types de blocs `ArticleBlockType`).
 */
export function AddBlockModal({
  backHref,
  headerTitle,
  headerSubtitle = 'Sélectionnez un type de bloc à gauche, vérifiez l\u2019aperçu, puis validez.',
  backLabel = '← Retour',
  onValidate,
  initialPreviewLocale = defaultLocale,
}: AddBlockModalProps) {
  const [selected, setSelected] = useState<AddBlockSelection | null>(null)
  const [previewLocale, setPreviewLocale] = useState<Locale>(initialPreviewLocale)
  const [catalogQuery, setCatalogQuery] = useState('')
  const [previewDevice, setPreviewDevice] = useState<PreviewDevice>('desktop')
  const [saving, setSaving] = useState(false)
  const previewViewportRef = useRef<HTMLDivElement>(null)
  const [desktopPreviewLayout, setDesktopPreviewLayout] = useState({ scale: 1, logicalH: 900 })

  const filteredCatalog = useMemo(() => {
    const q = normalizeCatalogSearch(catalogQuery)
    if (!q) return BLOCK_CATALOG
    return BLOCK_CATALOG
      .map((cat) => ({
        category: cat.category,
        items: cat.items.filter((it) => {
          const hay = normalizeCatalogSearch(
            [it.label, it.type, it.hint ?? '', it.description ?? '', cat.category].join(' '),
          )
          return hay.includes(q)
        }),
      }))
      .filter((cat) => cat.items.length > 0)
  }, [catalogQuery])

  const previewUrl = useMemo(() => {
    if (!selected) return ''
    const t = encodeURIComponent(selected.type)
    const loc = encodeURIComponent(previewLocale)
    return `/preview/article-block-demo/${t}?locale=${loc}`
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

  const select = useCallback(
    (it: { type: AddableBlockType; label: string; hint?: string; description?: string }, category: string) => {
      setSelected({
        type: it.type,
        label: it.label,
        category,
        description: it.description ?? 'Aucune description disponible.',
        ...(it.hint ? { hint: it.hint } : {}),
      })
    },
    [],
  )

  const handleValidate = async () => {
    if (!selected) return
    setSaving(true)
    try {
      await onValidate(selected, previewLocale)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[80] flex flex-col bg-slate-100">
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex min-w-0 items-center gap-3">
          <Link
            href={backHref}
            className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {backLabel}
          </Link>
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold text-slate-900">{headerTitle}</h1>
            <p className="truncate text-xs text-slate-500">{headerSubtitle}</p>
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
            <label htmlFor="add-block-search" className="sr-only">
              Filtrer les blocs
            </label>
            <input
              id="add-block-search"
              type="search"
              value={catalogQuery}
              onChange={(e) => setCatalogQuery(e.target.value)}
              placeholder="Rechercher (titre, paragraphe, vidéo, étape…)"
              autoComplete="off"
              className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            {filteredCatalog.length === 0 ? (
              <p className="px-2.5 py-4 text-center text-[11px] text-slate-500">
                Aucun bloc ne correspond à votre recherche.
              </p>
            ) : (
              <div className="divide-y divide-slate-100">
                {filteredCatalog.map((cat) => (
                  <div key={cat.category}>
                    <div className="sticky top-0 z-[1] bg-slate-100/95 px-2.5 py-1 backdrop-blur-sm">
                      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-700">
                        {cat.category}
                      </div>
                    </div>
                    {cat.items.map((it) => {
                      const active = selected?.type === it.type
                      return (
                        <button
                          key={it.type}
                          type="button"
                          title={it.hint ?? it.label}
                          onClick={() => select(it, cat.category)}
                          className={cn(
                            'flex w-full items-start gap-2 border-l-[3px] border-transparent px-2.5 py-2 text-left text-xs transition hover:bg-slate-50',
                            active && 'border-l-indigo-600 bg-indigo-50/70',
                          )}
                        >
                          <div className="min-w-0 flex-1">
                            <div className="truncate font-medium text-slate-900">{it.label}</div>
                            {it.hint ? (
                              <div className="truncate text-[10px] text-slate-500">{it.hint}</div>
                            ) : null}
                          </div>
                          <span className="shrink-0 truncate font-mono text-[10px] text-slate-400">
                            {it.type}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>

        <section className="flex min-h-0 min-w-0 flex-col bg-slate-200/80">
          {!selected ? (
            <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-slate-500">
              Choisissez un bloc dans la liste à gauche pour afficher sa description et un aperçu
              avec des données fictives.
            </div>
          ) : (
            <>
              <div className="shrink-0 border-b border-slate-200 bg-white px-6 py-4 shadow-sm">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                    {selected.category}
                  </span>
                  <h2 className="text-base font-semibold text-slate-900">{selected.label}</h2>
                </div>
                <p className="mt-0.5 font-mono text-xs text-slate-500">{selected.type}</p>
                <p className="mt-3 text-sm leading-relaxed text-slate-700">{selected.description}</p>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-slate-200 bg-slate-50/90 px-4 py-2">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                  Vue
                </span>
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
                    style={{ width: MOBILE_PREVIEW_W + 20, maxWidth: '100%' }}
                  >
                    <div className="overflow-hidden rounded-[1.35rem] bg-white">
                      <iframe
                        key={iframeKey}
                        title="Aperçu bloc — mobile"
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
                          title="Aperçu bloc — bureau"
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
        <Link
          href={backHref}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Annuler
        </Link>
        <Button
          type="button"
          disabled={!selected || saving}
          onClick={() => void handleValidate()}
          className="min-w-[200px]"
        >
          {saving ? 'Ajout…' : 'Ajouter ce bloc'}
        </Button>
      </footer>
    </div>
  )
}
