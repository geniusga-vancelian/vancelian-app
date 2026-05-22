import * as React from 'react'
import { cn } from '@/lib/utils'
import { KalaiIcon, type KalaiIconSize } from '@/components/ui/KalaiIcon'

export interface VProductCardFeature {
  /** Texte de la feature (ex. « Rendement actuel jusqu'à 6,44 % »). */
  text: React.ReactNode
  /** Slug Kalai pour l'icône de la puce (défaut : `check`). */
  iconName?: string
}

export interface VProductCardProps {
  /**
   * Slug Kalai pour l'icône principale (32 px) — ex. `wallet`, `bitcoin`,
   * `home-2`, `shield-good`. Si non fourni, l'icône est masquée.
   */
  iconName?: string
  /** Titre — Inter SemiBold 22px. */
  title: React.ReactNode
  /** Description — Inter Regular 14px, lh 1.55, muted. */
  description?: React.ReactNode
  /** Liste de features avec icônes Kalai (par défaut « check »). */
  features?: VProductCardFeature[]
  /** Texte du lien terracotta de bas de carte (ex. « Découvrir l'épargne »). */
  linkText?: React.ReactNode
  /** Href du lien. */
  linkHref?: string
  /** Callback alternatif au href (priorité au href s'il est fourni). */
  onLinkClick?: () => void
  /** Variant chromatique — `default` (warm-grey) ou `warm` (cardWarm). */
  variant?: 'default' | 'warm'
  /** Taille de l'icône principale (défaut 32 px, palier DS strict). */
  iconSize?: KalaiIconSize
  className?: string
}

/**
 * Vancelian — carte produit / écosystème (`product-card`).
 *
 * Spec DS officielle : voir `components/product-card/product-card.css` + `.html`
 * du pack handoff. C'est l'archétype de la carte « feature » dans les sections
 * écosystème, how-it-works, USP en grille 3 colonnes.
 *
 * Structure :
 * - Fond `rgba(26,24,21,.025)` (équivalent du `.tcard`) + bordure 1px `--v-fg-20`
 *   + radius 8px + élévation `subtle` ; au hover : élévation `medium`.
 * - Icône Kalai principale 32px en haut à gauche.
 * - Titre Inter SemiBold 22px / lh 1.3 + description body 14px muted.
 * - Liste de features : icône Kalai 16px (défaut `check`) + texte 13px muted.
 * - Lien terracotta SemiBold 14px avec flèche `→` qui glisse au hover.
 *
 * Grille parente recommandée : `grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch`.
 */
export function VProductCard({
  iconName,
  title,
  description,
  features = [],
  linkText,
  linkHref,
  onLinkClick,
  variant = 'default',
  iconSize = 32,
  className,
}: VProductCardProps) {
  const bgClass = variant === 'warm' ? 'bg-v-card-warm' : 'bg-[rgba(26,24,21,0.025)]'
  const hasLink = Boolean(linkText) && (Boolean(linkHref) || Boolean(onLinkClick))

  return (
    <article
      className={cn(
        'group flex h-full flex-col rounded-v-card border border-v-fg-20 p-v-2xl shadow-v-subtle',
        'transition-shadow duration-v-base ease-v-out hover:shadow-v-medium',
        bgClass,
        className,
      )}
    >
      {iconName ? (
        <KalaiIcon name={iconName} size={iconSize} className="text-v-fg" />
      ) : null}

      <h3
        className={cn(
          'font-ui font-semibold text-[22px] leading-[1.3] tracking-[0] text-v-fg m-0',
          iconName ? 'mt-v-xl' : 'mt-0',
        )}
      >
        {title}
      </h3>

      {description ? (
        <p className="mt-v-md font-ui font-normal text-[14px] leading-[1.55] text-v-fg-muted m-0">
          {description}
        </p>
      ) : null}

      {features.length > 0 ? (
        <ul className="mt-v-xl flex flex-col gap-v-sm list-none p-0 m-0">
          {features.map((feat, i) => (
            <li
              key={i}
              className="flex items-start gap-[10px] font-ui font-normal text-[13px] leading-[1.45] text-v-fg-muted"
            >
              <KalaiIcon
                name={feat.iconName ?? 'check'}
                size={16}
                className="text-v-fg mt-[2px]"
              />
              <span className="min-w-0 flex-1">{feat.text}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {hasLink ? (
        <div className="mt-v-2xl">
          {linkHref ? (
            <a
              href={linkHref}
              onClick={onLinkClick}
              className="inline-flex items-center gap-1 font-ui font-semibold text-[14px] leading-none text-v-terracotta no-underline transition-colors duration-v-fast ease-v-out hover:underline hover:underline-offset-[3px] active:text-v-terracotta-pressed"
            >
              <span>{linkText}</span>
              <span
                aria-hidden="true"
                className="inline-block transition-transform duration-v-base ease-v-out group-hover:translate-x-[3px]"
              >
                →
              </span>
            </a>
          ) : (
            <button
              type="button"
              onClick={onLinkClick}
              className="inline-flex cursor-pointer items-center gap-1 border-0 bg-transparent p-0 font-ui font-semibold text-[14px] leading-none text-v-terracotta transition-colors duration-v-fast ease-v-out hover:underline hover:underline-offset-[3px] active:text-v-terracotta-pressed"
            >
              <span>{linkText}</span>
              <span
                aria-hidden="true"
                className="inline-block transition-transform duration-v-base ease-v-out group-hover:translate-x-[3px]"
              >
                →
              </span>
            </button>
          )}
        </div>
      ) : null}
    </article>
  )
}
