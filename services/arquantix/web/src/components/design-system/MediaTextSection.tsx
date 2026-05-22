'use client'

import { cn } from '@/lib/utils'
import {
  VEyebrow,
  VEditorialTitle,
} from '@/components/design-system/vancelian'
import { VCmsMedia } from '@/components/design-system/vancelian/VCmsMedia'

export interface MediaTextSectionProps {
  /** Surtitre / pastille au-dessus du titre. Optionnel (pas de fallback). */
  eyebrow?: string
  title: string
  description: string
  imageSrc?: string
  videoSrc?: string
  imageAlt?: string | null
  /** true : image à droite, texte à gauche · false : image à gauche, texte à droite */
  mediaRight: boolean
}

/**
 * Section deux colonnes texte + média — Vancelian Design System.
 *
 * Pattern DS : voir doctrine éditoriale du pack handoff (split block,
 * `journey` pour le rythme image/texte). Image en `rounded-v-card` (8px),
 * texte aligné à gauche desktop / centré mobile, eyebrow `v-caption`,
 * titre `module` (mix Inter/Newsreader via `<em>`), chapô body 16px lh 1.6.
 */
export function MediaTextSection({
  eyebrow,
  title,
  description,
  imageSrc,
  videoSrc,
  imageAlt,
  mediaRight,
}: MediaTextSectionProps) {
  const e = eyebrow?.trim() ?? ''
  const t = title.trim()
  const d = description.trim()
  const img = typeof imageSrc === 'string' ? imageSrc.trim() : ''
  const vid = typeof videoSrc === 'string' ? videoSrc.trim() : ''
  const hasImage = Boolean(img || vid)
  const hasText = Boolean(e || t || d)

  const textBlock = hasText ? (
    <div
      className={cn(
        'flex min-w-0 flex-col justify-center gap-6 items-center text-center lg:items-start lg:text-left',
        hasImage && (mediaRight ? 'order-2 lg:order-1' : 'order-2 lg:order-2'),
      )}
    >
      {e ? <VEyebrow>{e}</VEyebrow> : null}
      {t ? (
        <VEditorialTitle as="h2" size="module" align="left" className="text-center lg:text-left">
          {t}
        </VEditorialTitle>
      ) : null}
      {d ? (
        <p className="m-0 whitespace-pre-wrap font-ui font-normal text-[16px] leading-[1.6] text-v-fg-body text-center lg:text-left">
          {d}
        </p>
      ) : null}
    </div>
  ) : null

  const imageFigure = (orderClass?: string) => (
    <div
      className={cn(
        'relative min-h-[240px] w-full min-w-0 overflow-hidden rounded-v-card bg-v-card lg:min-h-[min(360px,50vh)]',
        orderClass,
      )}
    >
      <VCmsMedia
        imageUrl={img || undefined}
        videoUrl={vid || undefined}
        alt={imageAlt?.trim() || ''}
        autoPlay={Boolean(vid)}
        loop={Boolean(vid)}
        muted
        playsInline
        preload="metadata"
        className="absolute inset-0 size-full object-cover object-center"
      />
    </div>
  )

  const imageBlock =
    hasImage && hasText
      ? imageFigure(mediaRight ? 'order-1 lg:order-2' : 'order-1 lg:order-1')
      : hasImage
        ? imageFigure()
        : null

  if (!hasText && !hasImage) return null

  return (
    <section className="w-full bg-v-bg text-v-fg" data-name="Media & Text">
      <div className="mx-auto max-w-[1152px] px-4 py-20 sm:px-6 lg:px-8 lg:py-24">
        {hasImage && hasText ? (
          <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2 lg:gap-16">
            {textBlock}
            {imageBlock}
          </div>
        ) : hasImage ? (
          <div className="w-full">{imageFigure()}</div>
        ) : (
          <div className="mx-auto max-w-[640px]">{textBlock}</div>
        )}
      </div>
    </section>
  )
}
