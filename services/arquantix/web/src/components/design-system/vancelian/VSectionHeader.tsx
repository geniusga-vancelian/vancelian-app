import * as React from 'react'
import { cn } from '@/lib/utils'
import { VEyebrow } from './VEyebrow'
import { VEditorialTitle, type VEditorialTitleSize } from './VEditorialTitle'

export interface VSectionHeaderProps {
  /** Surtitre (caption uppercase). Optionnel — pas de fallback. */
  eyebrow?: string
  /**
   * Titre éditorial. Peut contenir des `<em>` ou être passé en JSX pour le
   * support natif des accents Newsreader italic via {@link VEditorialTitle}.
   */
  title?: React.ReactNode
  /** Chapô sous le titre — body 18px Inter normal. */
  description?: React.ReactNode
  /** Niveau hN du titre (par défaut h2). */
  titleAs?: 'h1' | 'h2' | 'h3'
  /** Échelle de titre — page (défaut) / module / display. */
  titleSize?: VEditorialTitleSize
  /** `default` (fond clair) ou `inverse` (fond sombre — hero photo, final-cta). */
  tone?: 'default' | 'inverse'
  /** Alignement global (défaut centre). */
  align?: 'left' | 'center'
  /** Largeur max du chapô. */
  maxWidth?: string | number
  className?: string
}

/**
 * Vancelian — header de section composé (eyebrow + titre + chapô).
 *
 * Structure DS officielle des sections (cf. README pack handoff §«content
 * fundamentals», §«editorial scale») :
 *
 *   ┌────────────────────────────────────────────────┐
 *   │           EYEBROW · UPPERCASE 11px             │
 *   │                                                │
 *   │     Titre éditorial avec accent *italic*       │
 *   │                                                │
 *   │       Chapô descriptif, body 18px,             │
 *   │       Inter normal, lh 1.55                    │
 *   └────────────────────────────────────────────────┘
 *
 * Espacements : `gap-6` (24px) entre eyebrow et titre, `gap-6` (24px) entre
 * titre et chapô. Marge basse externe : à gérer par le parent (`mb-12` etc.).
 *
 * Cas d'usage : header de SectionTestimonials, FAQ, KeyFigures, HowItWorks,
 * ProofBar, etc. — tout module CMS avec la triade Surtitre/Titre/Description.
 */
export function VSectionHeader({
  eyebrow,
  title,
  description,
  titleAs = 'h2',
  titleSize = 'page',
  tone = 'default',
  align = 'center',
  maxWidth = 720,
  className,
}: VSectionHeaderProps) {
  const e = typeof eyebrow === 'string' ? eyebrow.trim() : eyebrow
  const hasEyebrow = Boolean(e)
  const hasTitle = title !== undefined && title !== null && title !== ''
  const hasDescription = description !== undefined && description !== null && description !== ''

  if (!hasEyebrow && !hasTitle && !hasDescription) return null

  const descToneClass = tone === 'inverse' ? 'text-white/70' : 'text-v-fg-muted'

  return (
    <header
      className={cn(
        'flex w-full flex-col',
        align === 'center' ? 'items-center text-center' : 'items-start text-left',
        'gap-6',
        className,
      )}
      style={{ maxWidth }}
    >
      {hasEyebrow ? <VEyebrow tone={tone === 'inverse' ? 'inverse' : 'light'}>{e}</VEyebrow> : null}
      {hasTitle ? (
        <VEditorialTitle as={titleAs} size={titleSize} tone={tone} align={align}>
          {title}
        </VEditorialTitle>
      ) : null}
      {hasDescription ? (
        <p
          className={cn(
            'font-ui font-normal text-[18px] leading-[1.55] m-0 max-w-[560px]',
            align === 'center' ? 'text-center' : 'text-left',
            descToneClass,
          )}
        >
          {description}
        </p>
      ) : null}
    </header>
  )
}
