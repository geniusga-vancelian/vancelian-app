import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * Typo **Label** (DS Figma) — hero offre exclusive :
 * Avenir, **poids 900** (Black), 10px, line-height 100%, letter-spacing 0%, uppercase.
 *
 * Conteneur : fond dark grey **opaque** (aucune opacité / alpha sur fond ni texte),
 * pas d’ombre portée (évite tout effet semi-transparent). Coins 8px, padding 6×8px.
 */
export const HERO_OFFER_TAG_GAP_CLASS = 'gap-2.5' /** 10px */

/** Fond dark grey opaque (~Tailwind neutral-700). */
const HERO_OFFER_TAG_BG_CLASS = 'bg-neutral-700'

/**
 * `font-black` = font-weight 900 (Tailwind). Face principale Avenir Black ; fallback sans-serif en 900.
 */
const labelTypography = cn(
  'text-center font-["Avenir:Black",sans-serif] text-[10px] font-black uppercase not-italic',
  'leading-none tracking-normal text-white',
)

const chipBase = cn(
  'inline-flex min-h-[23px] min-w-0 max-w-[min(100%,320px)] items-center justify-center',
  'rounded-[8px] px-[6px] py-2',
  labelTypography,
  HERO_OFFER_TAG_BG_CLASS,
)

export type HeroOfferTagChipVariant = 'onMedia' | 'onLight'

type HeroOfferTagChipProps = {
  children: React.ReactNode
  className?: string
  /**
   * Conservé pour compat ; les deux variantes utilisent le même rendu DS (fond dark grey).
   * `onLight` : hero sans image — même puce (contraste suffisant sur fond blanc).
   */
  variant?: HeroOfferTagChipVariant
}

export function HeroOfferTagChip({
  children,
  className,
  variant: _variant = 'onMedia',
}: HeroOfferTagChipProps) {
  return <span className={cn(chipBase, className)}>{children}</span>
}
