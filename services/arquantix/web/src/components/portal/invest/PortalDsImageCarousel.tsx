'use client'

import { useEffect, useState, type ReactNode } from 'react'

import { PortalHeroBackgroundVideo } from '@/components/portal/invest/PortalHeroBackgroundVideo'
import { cn } from '@/lib/utils'

const COVER_GRAD =
  'linear-gradient(160deg, #1a2840 0%, #38597d 40%, #c7d4e3 100%)'

type Props = {
  photos: string[]
  /** Vidéo promo TitlePage — prioritaire sur `photos` en variant hero (lecture auto). */
  backgroundVideoUrl?: string | null
  /** Hero `.dh-article` (3:4 → 16:9) ou galerie in-page preview/30 (16:9). */
  variant?: 'hero' | 'gallery'
  className?: string
  /** Libellé accessibilité quand plusieurs images. */
  ariaLabel?: string
  children?: ReactNode
}

/**
 * Carrousel image DS portail — handoff `.carousel` · `.carousel__progress` (preview/30).
 */
export function PortalDsImageCarousel({
  photos,
  backgroundVideoUrl,
  variant = 'gallery',
  className,
  ariaLabel = 'Galerie photos',
  children,
}: Props) {
  const urls = photos.filter(Boolean)
  const [idx, setIdx] = useState(0)
  const [paused, setPaused] = useState(false)
  const heroVideoUrl =
    variant === 'hero' && typeof backgroundVideoUrl === 'string' ? backgroundVideoUrl.trim() : ''
  const useHeroVideo = Boolean(heroVideoUrl)

  useEffect(() => {
    if (useHeroVideo || paused || urls.length <= 1) return
    const t = window.setInterval(() => setIdx((i) => (i + 1) % urls.length), 5000)
    return () => window.clearInterval(t)
  }, [paused, urls.length, useHeroVideo])

  const current = urls[idx]
  const showGalleryNav = variant === 'gallery' && urls.length > 1

  const goPrev = () => {
    setIdx((i) => (i - 1 + urls.length) % urls.length)
    setPaused(true)
  }

  const goNext = () => {
    setIdx((i) => (i + 1) % urls.length)
    setPaused(true)
  }

  return (
    <div
      className={cn(
        'carousel',
        variant === 'hero' && 'dh-article',
        variant === 'hero' && useHeroVideo && 'dh-article--video',
        variant === 'gallery' && 'carousel--gallery',
        className,
      )}
      role={!useHeroVideo && urls.length > 1 ? 'region' : undefined}
      aria-label={!useHeroVideo && urls.length > 1 ? ariaLabel : undefined}
      style={
        useHeroVideo
          ? undefined
          : {
              backgroundImage: current ? `url('${current}')` : undefined,
              background: !current ? COVER_GRAD : undefined,
            }
      }
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {useHeroVideo ? <PortalHeroBackgroundVideo videoUrl={heroVideoUrl} /> : null}
      {!useHeroVideo && urls.length > 1 ? (
        <div className="carousel__progress" aria-hidden="true">
          {urls.map((_, i) => (
            <button
              key={i}
              type="button"
              className={cn(i < idx && 'on', i === idx && 'playing')}
              onClick={() => setIdx(i)}
              aria-label={`Photo ${i + 1}`}
            />
          ))}
        </div>
      ) : null}
      {showGalleryNav ? (
        <>
          <button
            type="button"
            className="carousel__nav carousel__nav--prev"
            onClick={goPrev}
            aria-label="Photo précédente"
          />
          <button
            type="button"
            className="carousel__nav carousel__nav--next"
            onClick={goNext}
            aria-label="Photo suivante"
          />
        </>
      ) : null}
      {children}
    </div>
  )
}
