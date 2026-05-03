'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { Monitor, Pencil, Smartphone, X } from 'lucide-react'
import { supportedLocales, type Locale } from '@/config/locales'
import type { LocaleCompletenessLevel } from '@/lib/admin/pageLocaleCompleteness'
import { localeCompletenessLabel } from '@/lib/admin/pageLocaleCompleteness'
import { cn } from '@/lib/utils'

const DESKTOP_CANVAS_W = 1280
/** Hauteur minimale du viewport logique (px) avant mise à l’échelle. */
const DESKTOP_MIN_LOGICAL_H = 560
/**
 * Plafond large : colonne étroite → scale inférieur à 1 et hauteur affichée = logicalH × scale.
 * Un plafond trop bas laissait une bande grise sous l’iframe.
 */
const DESKTOP_MAX_LOGICAL_H = 24000
const MOBILE_W = 390
const MOBILE_H = 844

export type PagePreviewToolbarProps = {
  locale: Locale
  onLocaleChange: (l: Locale) => void
  localeLevels?: Record<Locale, LocaleCompletenessLevel>
  device: 'desktop' | 'mobile'
  onDeviceChange: (d: 'desktop' | 'mobile') => void
  /** Lien vers le CMS (page, gabarit, vault, article…). */
  editPageHref?: string | null
}

function localeButtonClasses(level: LocaleCompletenessLevel | undefined): string {
  if (!level) {
    return 'border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-200'
  }
  if (level === 'complete') {
    return 'border-emerald-400 bg-emerald-50 text-emerald-900 shadow-sm hover:bg-emerald-100'
  }
  if (level === 'partial') {
    return 'border-amber-300 bg-amber-50 text-amber-950 hover:bg-amber-100'
  }
  if (level === 'missing') {
    return 'border-red-400 bg-red-50 text-red-900 hover:bg-red-100'
  }
  return 'border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-200'
}

export type PagePreviewPanelProps = {
  title: string
  previewUrl: string
  /** Fermeture (tiroir / structure). Omis si `dismissible={false}`. */
  onClose?: () => void
  className?: string
  /** Langues + mobile/desktop (aperçu structure du site). */
  toolbar?: PagePreviewToolbarProps
  /** Incrémenté pour forcer le rechargement de l’iframe (ex. menu / boutons mis à jour). */
  reloadEpoch?: number
  /** Si false, pas de bouton X (aperçu ancré dans un split éditeur). Défaut : true. */
  dismissible?: boolean
}

/**
 * En-tête + iframe d’aperçu public (même origine). Réutilisable en tiroir mobile ou colonne desktop.
 */
type DesktopLayout = { scale: number; logicalH: number }

export function PagePreviewPanel({
  title,
  previewUrl,
  onClose,
  className,
  toolbar,
  reloadEpoch = 0,
  dismissible = true,
}: PagePreviewPanelProps) {
  const viewportRef = useRef<HTMLDivElement>(null)
  const [desktopLayout, setDesktopLayout] = useState<DesktopLayout>({ scale: 1, logicalH: 900 })
  const iframeKey = `${previewUrl}::${reloadEpoch}`

  useEffect(() => {
    if (!toolbar || toolbar.device !== 'desktop') return
    const el = viewportRef.current
    if (!el) return

    const measure = () => {
      const pad = 8
      const cw = Math.max(120, el.clientWidth - pad)
      const ch = Math.max(160, el.clientHeight - pad)
      // Largeur : rentrer dans la zone (pas d’upscale). Hauteur : remplir le conteneur (logicalH × scale ≈ ch).
      const scale = Math.min(1, cw / DESKTOP_CANVAS_W)
      const rawH = Math.ceil(ch / scale)
      const logicalH = Math.min(
        DESKTOP_MAX_LOGICAL_H,
        Math.max(DESKTOP_MIN_LOGICAL_H, rawH),
      )
      setDesktopLayout({ scale, logicalH })
    }

    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [toolbar?.device, previewUrl])

  const iframeMobile = (
    <iframe
      key={iframeKey}
      title={title}
      src={previewUrl}
      className="block border-0 bg-white"
      sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
      style={{ width: MOBILE_W, height: MOBILE_H }}
    />
  )

  const iframeDesktop = (
    <iframe
      key={iframeKey}
      title={title}
      src={previewUrl}
      className="block border-0 bg-white"
      sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
      style={{ width: DESKTOP_CANVAS_W, height: desktopLayout.logicalH }}
    />
  )

  return (
    <div className={cn('flex min-h-0 min-w-0 flex-1 flex-col bg-white', className)}>
      <header className="flex shrink-0 flex-col gap-2 border-b border-slate-100 px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Aperçu</p>
            <p className="truncate text-sm font-medium text-slate-900">{title}</p>
            <p className="truncate font-mono text-[11px] text-slate-500">{previewUrl}</p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {toolbar?.editPageHref ? (
              <Link
                href={toolbar.editPageHref}
                className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white shadow-sm transition hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2"
              >
                <Pencil className="h-3.5 w-3.5" aria-hidden />
                Éditer cette page
              </Link>
            ) : null}
            {dismissible && onClose ? (
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                aria-label="Fermer"
              >
                <X className="h-5 w-5" />
              </button>
            ) : null}
          </div>
        </div>

        {toolbar ? (
          <div className="flex flex-wrap items-center gap-2 border-t border-slate-100/80 pt-2">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Langue</span>
            <div className="flex flex-wrap gap-1">
              {supportedLocales.map((loc) => {
                const lv = toolbar.localeLevels?.[loc]
                const active = toolbar.locale === loc
                return (
                  <button
                    key={loc}
                    type="button"
                    title={localeCompletenessLabel(lv ?? 'no_sections')}
                    onClick={() => toolbar.onLocaleChange(loc)}
                    className={cn(
                      'rounded-md border px-2 py-1 font-mono text-[11px] font-semibold transition',
                      localeButtonClasses(lv),
                      active && 'ring-2 ring-indigo-400 ring-offset-1',
                    )}
                  >
                    {loc.toUpperCase()}
                  </button>
                )
              })}
            </div>
            <span className="mx-1 hidden h-4 w-px bg-slate-200 sm:inline" aria-hidden />
            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Vue</span>
            <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
              <button
                type="button"
                onClick={() => toolbar.onDeviceChange('desktop')}
                className={cn(
                  'inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition',
                  toolbar.device === 'desktop'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800',
                )}
                aria-pressed={toolbar.device === 'desktop'}
              >
                <Monitor className="h-3.5 w-3.5" aria-hidden />
                Bureau
              </button>
              <button
                type="button"
                onClick={() => toolbar.onDeviceChange('mobile')}
                className={cn(
                  'inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition',
                  toolbar.device === 'mobile'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800',
                )}
                aria-pressed={toolbar.device === 'mobile'}
              >
                <Smartphone className="h-3.5 w-3.5" aria-hidden />
                Mobile
              </button>
            </div>
          </div>
        ) : null}
      </header>

      <div
        ref={viewportRef}
        className={cn(
          'flex min-h-0 flex-1 flex-col overflow-auto bg-slate-200/90 p-1',
          toolbar?.device === 'mobile' && 'items-center',
        )}
      >
        {!toolbar ? (
          <iframe
            key={iframeKey}
            title={title}
            src={previewUrl}
            className="h-full min-h-[280px] w-full rounded-md border border-slate-200 bg-white shadow-inner lg:min-h-0"
            sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
          />
        ) : toolbar.device === 'mobile' ? (
          <div
            className="shrink-0 overflow-hidden rounded-[2rem] border-[10px] border-slate-800 bg-slate-800 shadow-2xl"
            style={{
              width: MOBILE_W + 20,
              maxWidth: '100%',
            }}
          >
            <div className="overflow-hidden rounded-[1.35rem] bg-white">{iframeMobile}</div>
          </div>
        ) : (
          <div className="flex min-h-0 min-w-0 w-full flex-1 items-start justify-center">
            <div
              className="shrink-0"
              style={{
                width: DESKTOP_CANVAS_W * desktopLayout.scale,
                height: desktopLayout.logicalH * desktopLayout.scale,
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: DESKTOP_CANVAS_W,
                  height: desktopLayout.logicalH,
                  transform: `scale(${desktopLayout.scale})`,
                  transformOrigin: 'top left',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                }}
              >
                {iframeDesktop}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
