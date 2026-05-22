'use client'

import { useCallback, useLayoutEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { arquantixContentTextBlockClass } from '@/lib/design/contentMaxWidth'
import { cn } from '@/lib/utils'
import {
  VEyebrow,
  VEditorialTitle,
  VCmsMedia,
} from '@/components/design-system/vancelian'

export interface CompanyMapSectionProps {
  eyebrow?: string
  title?: string
  description?: string
  backgroundImageUrl?: string
  backgroundVideoUrl?: string
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
  backgroundVideoUrl,
  backgroundImageAlt,
  bodyContent,
}: CompanyMapSectionProps) {
  const e = eyebrow?.trim() ?? ''
  const t = title?.trim() ?? ''
  const d = description?.trim() ?? ''
  const body = bodyContent?.trim() ?? ''
  const img = typeof backgroundImageUrl === 'string' ? backgroundImageUrl.trim() : ''
  const video = typeof backgroundVideoUrl === 'string' ? backgroundVideoUrl.trim() : ''
  const hasMedia = Boolean(img || video)
  const hasHeader = Boolean(e || t || d)
  const hasBody = Boolean(body)
  const mediaWrapperRef = useRef<HTMLDivElement>(null)
  /** Espace titre → corps = 40 % de la hauteur rendue de l’image carte */
  const [titleToBodyGapPx, setTitleToBodyGapPx] = useState<number | null>(null)

  const recalcTitleBodyGap = useCallback(() => {
    requestAnimationFrame(() => {
      const el = mediaWrapperRef.current
      if (!el || !hasMedia) {
        setTitleToBodyGapPx(null)
        return
      }
      const h = el.getBoundingClientRect().height
      if (h > 0) {
        setTitleToBodyGapPx(Math.round(h * 0.4))
      }
    })
  }, [hasMedia])

  useLayoutEffect(() => {
    recalcTitleBodyGap()
    const el = mediaWrapperRef.current
    if (!el) return
    const ro = new ResizeObserver(() => recalcTitleBodyGap())
    ro.observe(el)
    window.addEventListener('resize', recalcTitleBodyGap)
    return () => {
      ro.disconnect()
      window.removeEventListener('resize', recalcTitleBodyGap)
    }
  }, [recalcTitleBodyGap])

  if (!hasHeader && !hasBody && !hasMedia) {
    return null
  }

  return (
    <section
      className="relative w-full overflow-hidden bg-v-bg"
      data-name="Company map"
    >
      <div className="relative mx-auto max-w-[1200px] px-4 pb-20 md:px-16 md:pb-28">
        {hasMedia ? (
          <div
            className="pointer-events-none absolute inset-x-0 top-0 z-0 flex justify-center md:inset-x-0"
            aria-hidden
          >
            <div
              ref={mediaWrapperRef}
              className="relative flex w-full max-w-[1080px] justify-center bg-v-bg px-2 md:px-0"
            >
              <VCmsMedia
                imageUrl={img || undefined}
                videoUrl={video || undefined}
                alt={backgroundImageAlt?.trim() || ''}
                objectFit="contain"
                autoPlay
                loop
                muted
                playsInline
                preload="auto"
                className="w-full max-w-[1080px] object-contain object-[center_33%] md:max-h-[min(88vh,920px)] md:object-[center_31%]"
                style={{
                  minHeight: 'min(76vh, 780px)',
                  maxHeight: 'min(90vh, 960px)',
                }}
              />
            </div>
          </div>
        ) : null}

        <div
          className={cn(
            'relative z-[2]',
            'pt-[72px] md:pt-[100px] lg:pt-[140px]',
          )}
        >
          {hasHeader ? (
            <div className="mx-auto flex w-full max-w-[900px] flex-col items-center gap-6 text-center md:gap-8 [&_h1]:drop-shadow-[0_2px_20px_rgba(247,247,244,0.95)] [&_h2]:drop-shadow-[0_2px_20px_rgba(247,247,244,0.95)]">
              {e || t ? (
                <div className="flex w-full flex-col items-center gap-4 [&>p:first-child]:drop-shadow-[0_1px_14px_rgba(247,247,244,0.95)]">
                  {e ? <VEyebrow>{e}</VEyebrow> : null}
                  {t ? (
                    <VEditorialTitle as="h2" size="module" tone="default">
                      {t}
                    </VEditorialTitle>
                  ) : null}
                </div>
              ) : null}
              {d ? (
                <p
                  className="m-0 max-w-[52rem] font-ui font-normal text-[18px] leading-[1.55] text-v-fg-body [text-wrap:balance]"
                  style={{ textShadow: '0 0 24px rgba(247,247,244,0.85), 0 0 12px rgba(247,247,244,0.6)' }}
                >
                  {d}
                </p>
              ) : null}
            </div>
          ) : null}

          {hasBody && hasHeader ? (
            <div
              aria-hidden
              className="w-full shrink-0"
              style={{
                height:
                  hasMedia && titleToBodyGapPx != null && titleToBodyGapPx > 0
                    ? titleToBodyGapPx
                    : hasMedia
                      ? 0
                      : 64,
              }}
            />
          ) : null}

          {hasBody ? (
            <div
              className={cn(
                arquantixContentTextBlockClass,
                !hasMedia && !hasHeader && 'mt-14 md:mt-20',
              )}
            >
              <div
                className={cn(
                  'prose prose-neutral max-w-none w-full px-0 font-ui text-[16px] leading-[1.7] text-v-fg-body',
                  'text-justify prose-p:text-justify prose-headings:text-left',
                  'prose-p:mb-4 prose-p:mt-0 last:prose-p:mb-0 prose-headings:font-semibold prose-headings:text-v-fg',
                  'prose-a:text-v-terracotta prose-strong:text-v-fg prose-ul:my-3 prose-li:my-1',
                  'prose-ul:text-left prose-ol:text-left',
                  '[&_p]:drop-shadow-[0_1px_12px_rgba(247,247,244,0.95)] [&_li]:drop-shadow-[0_1px_8px_rgba(247,247,244,0.9)]',
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
