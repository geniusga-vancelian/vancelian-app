'use client'

import { useEffect, useState, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

const COVER_GRAD =
  'linear-gradient(160deg, #1a2840 0%, #38597d 40%, #c7d4e3 100%)'

type Props = {
  photos: string[]
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
  variant = 'gallery',
  className,
  ariaLabel = 'Galerie photos',
  children,
}: Props) {
  const urls = photos.filter(Boolean)
  const [idx, setIdx] = useState(0)
  const [paused, setPaused] = useState(false)
  const count = urls.length || 1

  useEffect(() => {
    if (paused || urls.length <= 1) return
    const t = window.setInterval(() => setIdx((i) => (i + 1) % urls.length), 5000)
    return () => window.clearInterval(t)
  }, [paused, urls.length])

  const current = urls[idx]

  return (
    <div
      className={cn(
        'carousel',
        variant === 'hero' && 'dh-article',
        variant === 'gallery' && 'carousel--gallery',
        className,
      )}
      role={urls.length > 1 ? 'region' : undefined}
      aria-label={urls.length > 1 ? ariaLabel : undefined}
      style={{
        backgroundImage: current ? `url('${current}')` : undefined,
        background: !current ? COVER_GRAD : undefined,
      }}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {urls.length > 1 ? (
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
      {children}
    </div>
  )
}
