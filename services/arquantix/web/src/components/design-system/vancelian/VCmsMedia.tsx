'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

export interface VCmsMediaProps {
  imageUrl?: string
  videoUrl?: string
  alt?: string
  className?: string
  /** `cover` par défaut — plein cadre. */
  objectFit?: 'cover' | 'contain'
  autoPlay?: boolean
  loop?: boolean
  muted?: boolean
  playsInline?: boolean
  preload?: 'auto' | 'metadata' | 'none'
  style?: React.CSSProperties
}

/** Média CMS inline — image ou vidéo MP4 selon les URLs résolues. */
export function VCmsMedia({
  imageUrl,
  videoUrl,
  alt = '',
  className,
  objectFit = 'cover',
  autoPlay = false,
  loop = false,
  muted = true,
  playsInline = true,
  preload = 'metadata',
  style,
}: VCmsMediaProps) {
  const fitClass = objectFit === 'contain' ? 'object-contain' : 'object-cover'

  if (videoUrl?.trim()) {
    return (
      <video
        className={cn('h-full w-full', fitClass, className)}
        style={style}
        src={videoUrl}
        autoPlay={autoPlay}
        muted={muted}
        loop={loop}
        playsInline={playsInline}
        preload={preload}
        aria-hidden={!alt ? true : undefined}
        aria-label={alt || undefined}
      />
    )
  }

  if (imageUrl?.trim()) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- média CMS
      <img
        alt={alt}
        src={imageUrl}
        className={cn('h-full w-full', fitClass, className)}
        style={style}
        loading="lazy"
        decoding="async"
      />
    )
  }

  return null
}
