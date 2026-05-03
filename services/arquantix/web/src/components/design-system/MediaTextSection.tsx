'use client'

import { SectionTitle } from '@/components/design-system/extracted'
import { cn } from '@/lib/utils'

export interface MediaTextSectionProps {
  /**
   * Surtitre / pastille au-dessus du titre. Optionnel : si non fourni
   * (ou vide), aucun bandeau n'est rendu — pas de fallback hardcodé,
   * pour éviter qu'un texte non passé par le pipeline i18n CMS apparaisse
   * sur le site (cf. règle « surtitre piloté par le CMS uniquement »).
   */
  eyebrow?: string
  title: string
  description: string
  imageSrc?: string
  imageAlt?: string | null
  /** true : image à droite, texte à gauche · false : image à gauche, texte à droite */
  mediaRight: boolean
}

/**
 * Pastille « surtitre » alignée à gauche (filets verticaux gauche/droite,
 * 14px Heavy uppercase #62656e). Cohérent avec les autres surtitres du DS
 * (`SectionFigmaBlockHeader`, `ProjetGallery`, `CompanyMapSection`) mais
 * positionnée à gauche pour s'aligner au titre `align="left"` de ce module.
 */
function MediaTextEyebrow({ text }: { text: string }) {
  return (
    <div className="relative inline-flex shrink-0 items-center justify-center self-center rounded-[2px] px-[4px] py-[2px] lg:self-start">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 rounded-[2px] border-solid border-l border-r border-[#62656e]"
      />
      <p className="relative whitespace-nowrap font-['Avenir:Heavy',sans-serif] text-[14px] uppercase leading-none not-italic text-[#62656e]">
        {text}
      </p>
    </div>
  )
}

/**
 * Section deux colonnes (fond blanc pleine largeur, typo DS) : titre + description d’un côté,
 * visuel arrondi de l’autre. Comportement responsive : sur mobile, l’image en tête
 * quand elle est à gauche sur desktop ; sinon le texte en premier.
 */
export function MediaTextSection({
  eyebrow,
  title,
  description,
  imageSrc,
  imageAlt,
  mediaRight,
}: MediaTextSectionProps) {
  const e = eyebrow?.trim() ?? ''
  const t = title.trim()
  const d = description.trim()
  const img = typeof imageSrc === 'string' ? imageSrc.trim() : ''
  const hasImage = Boolean(img)

  const hasText = Boolean(e || t || d)

  const textBlock = hasText ? (
    <div
      className={cn(
        'flex min-w-0 flex-col justify-center gap-6 px-0 py-2 items-center text-center lg:items-start lg:text-left',
        hasImage && (mediaRight ? 'order-2 lg:order-1' : 'order-2 lg:order-2'),
      )}
    >
      {e ? <MediaTextEyebrow text={e} /> : null}
      {t ? (
        <SectionTitle align="left" color="#000000" size="module" className="text-center lg:text-left">
          {t}
        </SectionTitle>
      ) : null}
      {d ? (
        <p className="whitespace-pre-wrap text-center font-['Avenir:Roman',sans-serif] text-[18px] leading-[1.6] text-black/85 lg:text-left">
          {d}
        </p>
      ) : null}
    </div>
  ) : null

  const imageFigure = (orderClass?: string) => (
    <div
      className={cn(
        'relative min-h-[240px] w-full min-w-0 overflow-hidden rounded-2xl bg-neutral-100 lg:min-h-[min(360px,50vh)]',
        orderClass,
      )}
    >
      <img
        alt={imageAlt?.trim() || ''}
        className="absolute inset-0 size-full object-cover object-center"
        src={img}
        loading="lazy"
        decoding="async"
      />
    </div>
  )

  const imageBlock =
    hasImage && hasText
      ? imageFigure(mediaRight ? 'order-1 lg:order-2' : 'order-1 lg:order-1')
      : hasImage
        ? imageFigure()
        : null

  if (!hasText && !hasImage) {
    return null
  }

  return (
    <section
      className="w-full bg-white text-black"
      data-name="Media & Text"
    >
      <div className="mx-auto max-w-[1152px] px-4 py-12 sm:px-6 md:py-16 lg:px-8">
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
