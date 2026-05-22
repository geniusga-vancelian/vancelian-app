'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/button'
import { VEditorialTitle } from './VEditorialTitle'

export interface VFinalCtaButton {
  label: React.ReactNode
  onClick?: () => void
  href?: string
  /** `primary` = blanc → texte anthracite. `secondary` = outline blanc. */
  variant?: 'primary' | 'secondary'
}

export interface VFinalCtaProps {
  /** Surtitre éditorial — Inter Medium 11px UPPERCASE, couleur `#8E867A`. */
  eyebrow?: string
  /**
   * Titre éditorial — Inter SemiBold clamp(56–96px), italic Newsreader sur
   * les `<em>`. Accepte aussi du JSX (ex. saut de ligne `<br />`).
   */
  title?: React.ReactNode
  /** Chapô — body 18px / lh 1.55, texte blanc cassé semi-transparent. */
  description?: React.ReactNode
  /** 1 ou 2 boutons CTA. Vide ⇒ aucun bouton. */
  buttons?: VFinalCtaButton[]
  /** Note légale sous les CTA — body 12px, texte allégé. */
  note?: React.ReactNode
  /**
   * Couleur de fond — par défaut `#141208` (Vancelian Dark Olive),
   * spec officielle de `.final-cta` dans `final-cta.css`.
   */
  backgroundColor?: string
  className?: string
}

/**
 * Vancelian — section CTA final dark (`final-cta`).
 *
 * Spec DS officielle : voir `components/final-cta/final-cta.css` + `.html`
 * du pack handoff. C'est la **dernière section** d'une landing page,
 * juste au-dessus du footer global. Toujours en dark.
 *
 * Structure (centrée, max-width 720px) :
 * - Eyebrow `#8E867A` UPPERCASE 11px
 * - Titre éditorial clamp(56→96px) Inter SemiBold, italic Newsreader sur les `<em>`
 * - Chapô 18px blanc cassé 70 %
 * - 1–2 boutons : darkPrimary (blanc) + darkSecondary (outline blanc)
 * - Note légale 12px blanc cassé 50 %
 *
 * Padding vertical : 160px desktop, 128px ≤1024px (cf. final-cta.css).
 */
export function VFinalCta({
  eyebrow,
  title,
  description,
  buttons = [],
  note,
  backgroundColor = '#141208',
  className,
}: VFinalCtaProps) {
  const e = typeof eyebrow === 'string' ? eyebrow.trim() : eyebrow
  const hasEyebrow = Boolean(e)
  const hasTitle = title !== undefined && title !== null && title !== ''
  const hasDescription = description !== undefined && description !== null && description !== ''
  const hasNote = note !== undefined && note !== null && note !== ''
  const visibleButtons = buttons.filter(Boolean)

  if (!hasEyebrow && !hasTitle && !hasDescription && visibleButtons.length === 0) {
    return null
  }

  return (
    <section
      data-nav-surface="dark"
      className={cn(
        'relative w-full overflow-hidden text-[#EDECEC]',
        // Full-bleed background : un fond pleine largeur même si le parent
        // a un padding horizontal (cas du DS où la section vit dans un Container).
        'py-32 lg:py-40',
        className,
      )}
      style={{ backgroundColor }}
    >
      <Container className="relative">
        <div
          data-v-scroll-fade
          className="mx-auto flex max-w-[720px] flex-col items-center text-center"
        >
          {hasEyebrow ? (
            <p className="m-0 font-ui font-medium text-[11px] uppercase tracking-[0.05em] text-[#8E867A]">
              {e}
            </p>
          ) : null}

          {hasTitle ? (
            <VEditorialTitle
              size="display"
              tone="inverse"
              align="center"
              className={cn(hasEyebrow ? 'mt-8' : 'mt-0')}
            >
              {title}
            </VEditorialTitle>
          ) : null}

          {hasDescription ? (
            <p
              className={cn(
                'm-0 max-w-[540px] font-ui font-normal text-[18px] leading-[1.55] text-white/70',
                hasTitle || hasEyebrow ? 'mt-8' : 'mt-0',
              )}
            >
              {description}
            </p>
          ) : null}

          {visibleButtons.length > 0 ? (
            <div className="mt-12 flex flex-wrap justify-center gap-4">
              {visibleButtons.map((btn, i) => {
                const variant: 'darkPrimary' | 'darkSecondary' =
                  btn.variant === 'secondary' ? 'darkSecondary' : 'darkPrimary'
                if (btn.href) {
                  return (
                    <Button key={i} asChild variant={variant} size="default">
                      <a href={btn.href} onClick={btn.onClick}>
                        {btn.label}
                      </a>
                    </Button>
                  )
                }
                return (
                  <Button key={i} variant={variant} size="default" onClick={btn.onClick}>
                    {btn.label}
                  </Button>
                )
              })}
            </div>
          ) : null}

          {hasNote ? (
            <p className="mt-6 m-0 font-ui font-normal text-[12px] leading-[1.5] text-white/50">
              {note}
            </p>
          ) : null}
        </div>
      </Container>
    </section>
  )
}
