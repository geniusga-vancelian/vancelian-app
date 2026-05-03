'use client'

import { useCallback, useLayoutEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { SectionTitle } from '@/components/design-system/extracted'
import { arquantixContentTextBlockClass } from '@/lib/design/contentMaxWidth'
import { cn } from '@/lib/utils'

function HomepageStyleEyebrow({ text }: { text: string }) {
  const t = text.trim()
  if (!t) return null
  return (
    <div className="relative flex shrink-0 content-stretch items-center justify-center rounded-[2px] px-[4px] py-[2px]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 rounded-[2px] border-solid border-[#62656e] border-l border-r"
      />
      <p className="relative whitespace-nowrap font-['Avenir:Heavy',sans-serif] text-[14px] uppercase leading-none not-italic text-[#62656e]">
        {t}
      </p>
    </div>
  )
}

export interface CompanyMapSectionProps {
  eyebrow?: string
  title?: string
  description?: string
  backgroundImageUrl?: string
  backgroundImageAlt?: string | null
  bodyContent?: string
}

/**
 * Carte monde en arrière-plan continu (z-0) : remonte derrière surtitre + titre + chapô,
 * et s’étend derrière le début du corps — le contenu est au premier plan (z-10).
 * Écart titre/chapô → corps : **40 %** de la hauteur rendue de l’image (mesurée + ResizeObserver).
 * Sans image : 64 px entre le bloc titre et le corps.
 * Gouttières ~64px (md:px-16), padding haut ~140px (spec maquette).
 */
export function CompanyMapSection({
  eyebrow,
  title,
  description,
  backgroundImageUrl,
  backgroundImageAlt,
  bodyContent,
}: CompanyMapSectionProps) {
  const e = eyebrow?.trim() ?? ''
  const t = title?.trim() ?? ''
  const d = description?.trim() ?? ''
  const body = bodyContent?.trim() ?? ''
  const img = typeof backgroundImageUrl === 'string' ? backgroundImageUrl.trim() : ''
  const hasHeader = Boolean(e || t || d)
  const hasBody = Boolean(body)
  const mapImgRef = useRef<HTMLImageElement>(null)
  /** Espace titre → corps = 40 % de la hauteur rendue de l’image carte */
  const [titleToBodyGapPx, setTitleToBodyGapPx] = useState<number | null>(null)

  const recalcTitleBodyGap = useCallback(() => {
    requestAnimationFrame(() => {
      const el = mapImgRef.current
      if (!el || !img) {
        setTitleToBodyGapPx(null)
        return
      }
      const h = el.getBoundingClientRect().height
      if (h > 0) {
        setTitleToBodyGapPx(Math.round(h * 0.4))
      }
    })
  }, [img])

  useLayoutEffect(() => {
    recalcTitleBodyGap()
    const el = mapImgRef.current
    if (!el) return
    const ro = new ResizeObserver(() => recalcTitleBodyGap())
    ro.observe(el)
    window.addEventListener('resize', recalcTitleBodyGap)
    return () => {
      ro.disconnect()
      window.removeEventListener('resize', recalcTitleBodyGap)
    }
  }, [recalcTitleBodyGap])

  if (!hasHeader && !hasBody && !img) {
    return null
  }

  return (
    <section
      className="relative w-full overflow-hidden bg-white"
      data-name="Company map"
    >
      {/* Conteneur large : 64px de gouttière à partir de md (maquette) */}
      <div className="relative mx-auto max-w-[1200px] px-4 pb-20 md:px-16 md:pb-28">
        {img ? (
          <div
            className="pointer-events-none absolute inset-x-0 top-0 z-0 flex justify-center md:inset-x-0"
            aria-hidden
          >
            {/* Zone carte très haute : le visuel déborde derrière le bloc titre (haut) et le corps (bas) */}
            <div className="relative flex w-full max-w-[1080px] justify-center bg-white px-2 md:px-0">
              {/* Carte large, centrée : object-position légèrement vers le nord pour que le bas du visuel arrive derrière le corps */}
              <img
                ref={mapImgRef}
                alt={backgroundImageAlt?.trim() || ''}
                className="w-full max-w-[1080px] object-contain object-[center_33%] md:max-h-[min(88vh,920px)] md:object-[center_31%]"
                src={img}
                loading="lazy"
                decoding="async"
                onLoad={recalcTitleBodyGap}
                style={{
                  minHeight: 'min(76vh, 780px)',
                  maxHeight: 'min(90vh, 960px)',
                }}
              />
            </div>
          </div>
        ) : null}

        {/* Tout le texte au-dessus de la carte */}
        <div
          className={cn(
            'relative z-[2]',
            /* ~140px haut (maquette) — un peu moins sur mobile */
            'pt-[72px] md:pt-[100px] lg:pt-[140px]',
          )}
        >
          {hasHeader ? (
            <div className="mx-auto flex w-full max-w-[900px] flex-col items-center gap-6 text-center md:gap-8 [&_h1]:drop-shadow-[0_2px_20px_rgba(255,255,255,0.95)] [&_h2]:drop-shadow-[0_2px_20px_rgba(255,255,255,0.95)]">
              {e || t ? (
                <div className="flex w-full flex-col items-center gap-[10px] [&>div:first-child]:drop-shadow-[0_1px_14px_rgba(255,255,255,0.95)]">
                  {e ? <HomepageStyleEyebrow text={e} /> : null}
                  {t ? (
                    <SectionTitle size="module" align="center" color="#1d1d1f">
                      {t}
                    </SectionTitle>
                  ) : null}
                </div>
              ) : null}
              {d ? (
                <p
                  className="max-w-[52rem] font-['Avenir:Roman',sans-serif] text-[18px] leading-[1.6] text-black/90 [text-wrap:balance]"
                  style={{ textShadow: '0 0 24px rgba(255,255,255,0.85), 0 0 12px rgba(255,255,255,0.6)' }}
                >
                  {d}
                </p>
              ) : null}
            </div>
          ) : null}

          {/* Espace titre → corps : 40 % de la hauteur rendue de l’image (sinon écart fixe sans carte) */}
          {hasBody && hasHeader ? (
            <div
              aria-hidden
              className="w-full shrink-0"
              style={{
                height:
                  img && titleToBodyGapPx != null && titleToBodyGapPx > 0
                    ? titleToBodyGapPx
                    : img
                      ? 0
                      : 64,
              }}
            />
          ) : null}

          {hasBody ? (
            <div
              className={cn(
                arquantixContentTextBlockClass,
                !img && !hasHeader && 'mt-14 md:mt-20',
              )}
            >
              <div
                className={cn(
                  'prose prose-neutral max-w-none w-full px-0 font-[\'Avenir:Roman\',sans-serif] text-[17px] leading-[1.7] text-black/90',
                  'text-justify prose-p:text-justify prose-headings:text-left',
                  'prose-p:mb-4 prose-p:mt-0 last:prose-p:mb-0 prose-headings:font-semibold prose-headings:text-black',
                  'prose-a:text-indigo-700 prose-strong:text-black prose-ul:my-3 prose-li:my-1',
                  'prose-ul:text-left prose-ol:text-left',
                  /* léger halo pour lisibilité sur la carte sous le texte */
                  '[&_p]:drop-shadow-[0_1px_12px_rgba(255,255,255,0.95)] [&_li]:drop-shadow-[0_1px_8px_rgba(255,255,255,0.9)]',
                )}
              >
                <ReactMarkdown>{body}</ReactMarkdown>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
