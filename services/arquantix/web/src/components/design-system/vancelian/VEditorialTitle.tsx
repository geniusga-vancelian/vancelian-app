import * as React from 'react'
import { cn } from '@/lib/utils'

export type VEditorialTitleSize =
  | 'display' // hero — clamp(56–96px)
  | 'page'    // section principale — clamp(40–56px)
  | 'module'  // sous-titre de bloc — clamp(28–40px)

export interface VEditorialTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  /** Niveau hN du heading (h1 par défaut). */
  as?: 'h1' | 'h2' | 'h3'
  /** Échelle DS : display (hero) / page (section) / module (bloc). */
  size?: VEditorialTitleSize
  /** Couleur — `default` = anthracite ; `inverse` = blanc cassé (fonds sombres). */
  tone?: 'default' | 'inverse'
  /** Alignement texte (défaut centre — la majorité des sections marketing DS). */
  align?: 'left' | 'center'
  children: React.ReactNode
}

const SIZE_CLASSES: Record<VEditorialTitleSize, string> = {
  // Hero — titre principal page d'accueil (spec Home.html)
  display:
    'text-[clamp(48px,6.4vw,88px)] leading-[1.05] tracking-[-0.03em] font-bold',
  // Section principale — testimonials, final-cta, ecosystem header
  page:
    'text-[clamp(40px,4.6vw,56px)] leading-[1.05] tracking-[0] font-semibold',
  // Sous-titre / bloc — how it works, faq header
  module:
    'text-[clamp(28px,3vw,40px)] leading-[1.1] tracking-[0] font-semibold',
}

const TONE_CLASSES: Record<'default' | 'inverse', string> = {
  default: 'text-v-fg',
  inverse: 'text-v-dark-fg',
}

/**
 * Vancelian — titre éditorial avec accents Newsreader italic.
 *
 * Doctrine DS : Inter SemiBold pour le corps du titre, **Newsreader italic
 * pour le ou les mots-clés** mis en valeur (via `<em>` HTML). C'est la
 * signature typographique Vancelian : *« le mot juste »*.
 *
 * Exemples de doctrine (pack handoff) :
 * - Hero : « Bâtir son patrimoine, *aujourd'hui*. »
 * - Final CTA : « Le patrimoine commence *aujourd'hui*. »
 * - Section testimonials : « Ce qu'en disent *celles et ceux* qui investissent. »
 *
 * Le `font-size` Newsreader est légèrement augmenté (1.28em) pour compenser
 * la x-height plus basse du serif — c'est la règle des optical sizes Vancelian.
 *
 * Usage :
 * ```tsx
 * <VEditorialTitle size="page">
 *   Ce qu'en disent <em>celles et ceux</em> qui investissent.
 * </VEditorialTitle>
 * ```
 */
export function VEditorialTitle({
  as = 'h2',
  size = 'page',
  tone = 'default',
  align = 'center',
  className,
  children,
  ...rest
}: VEditorialTitleProps) {
  const Tag = as
  return (
    <Tag
      {...rest}
      className={cn(
        'font-ui m-0 text-balance',
        align === 'center' ? 'text-center' : 'text-left',
        SIZE_CLASSES[size],
        TONE_CLASSES[tone],
        // Italic interne — Newsreader Display, weight 300, slightly larger
        '[&_em]:font-display [&_em]:font-light [&_em]:italic [&_em]:text-[1.28em] [&_em]:leading-[0.95] [&_em]:tracking-[-0.01em]',
        className,
      )}
    >
      {children}
    </Tag>
  )
}
