import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * Étoile Kalai inline (filled, currentColor) — utilisée pour le rating tcard.
 * Source : pack handoff, `tcard.html` (path strictement reproduit).
 */
function VStarIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className="h-[14px] w-[14px] flex-none"
      style={{ opacity: filled ? 1 : 0.2 }}
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M10.098 4.618c.599-1.842 3.205-1.842 3.804 0l1.294 3.983h4.188c1.938 0 2.743 2.48 1.176 3.618l-3.388 2.462 1.294 3.982c.598 1.843-1.51 3.375-3.078 2.236L12 18.438 8.612 20.9c-1.567 1.138-3.676-.394-3.078-2.237l1.295-3.982-3.388-2.462c-1.568-1.139-.762-3.618 1.175-3.618h4.188l1.294-3.983ZM12 5.236 10.706 9.22a2 2 0 0 1-1.902 1.382H4.616l3.388 2.462a2 2 0 0 1 .727 2.236l-1.294 3.98 3.388-2.461a2 2 0 0 1 2.35 0l3.389 2.461-1.294-3.98a2 2 0 0 1 .726-2.236l3.388-2.462h-4.188a2 2 0 0 1-1.902-1.382L12 5.236Z"
      />
    </svg>
  )
}

/** Calcule les initiales (max 2) à partir d'un nom — fallback `••` si vide. */
function nameInitials(name: string): string {
  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
  if (parts.length === 0) return '••'
  return parts.map((p) => p[0]?.toUpperCase() ?? '').join('')
}

export interface VTcardProps {
  /** Citation — affichée en Newsreader Display Light Italic 20px (voix éditoriale). */
  quote: React.ReactNode
  /** Nom de l'auteur. */
  authorName: string
  /** Rôle / lieu sous le nom (ex. « Family office · Paris »). */
  authorRole?: string
  /** URL d'avatar — si absent, génère un avatar initiales sur fond `--v-fg-05`. */
  avatarUrl?: string | null
  /** Note 0–5 (étoiles). Si 0 ou non fourni, la rangée d'étoiles est masquée. */
  rating?: number
  /** Variant chromatique : `default` (warm-grey) ou `warm` (cardWarm). */
  variant?: 'default' | 'warm'
  className?: string
}

/**
 * Vancelian — carte témoignage (`tcard`).
 *
 * Spec DS officielle : voir `components/tcard/tcard.css` + `.html` du pack handoff.
 *
 * Structure :
 * - Fond `rgba(26,24,21,.025)` + bordure 1px `--v-fg-20` + radius 8px + élévation `subtle`.
 * - Étoiles Kalai 14px (couleur `--v-fg`) en haut, alignées à gauche.
 * - Citation Newsreader Display Light Italic 20px / lh 1.5 / couleur `--v-fg`.
 * - Divider horizontal 1px `--v-fg-10`.
 * - Auteur : avatar 40px (initiales sur `--v-fg-05` ou photo) + nom Inter SemiBold 14px
 *   + rôle Inter Regular 12px `--v-fg-muted`.
 *
 * À placer dans une grille `grid-cols-1 md:grid-cols-2 gap-6` (DS : 2 colonnes desktop,
 * pile mobile).
 */
export function VTcard({
  quote,
  authorName,
  authorRole,
  avatarUrl,
  rating = 0,
  variant = 'default',
  className,
}: VTcardProps) {
  const stars = Math.max(0, Math.min(5, Math.round(rating)))
  const showStars = stars > 0
  const initials = nameInitials(authorName)
  const bgClass = variant === 'warm' ? 'bg-v-card-warm' : 'bg-[rgba(26,24,21,0.025)]'

  return (
    <article
      className={cn(
        'flex h-full flex-col rounded-v-card border border-v-fg-20 p-v-2xl shadow-v-subtle',
        'transition-[background-color,border-color,box-shadow] duration-v-base ease-v-in-out',
        bgClass,
        className,
      )}
    >
      {showStars ? (
        <div
          className="inline-flex gap-1 leading-none text-v-fg"
          aria-label={`${stars} étoiles sur 5`}
        >
          {Array.from({ length: 5 }, (_, i) => (
            <VStarIcon key={i} filled={i < stars} />
          ))}
        </div>
      ) : null}

      <p
        className={cn(
          'font-display font-light italic text-[20px] leading-[1.5] text-v-fg m-0 flex-1',
          showStars ? 'mt-v-xl' : 'mt-0',
        )}
      >
        {quote}
      </p>

      <hr className="my-v-xl h-px w-full border-0 bg-v-fg-10" />

      <div className="flex items-center gap-v-md">
        {avatarUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- avatar utilisateur CMS, dimensions fixes
          <img
            src={avatarUrl}
            alt=""
            className="h-10 w-10 flex-none rounded-v-pill object-cover"
            loading="lazy"
            decoding="async"
          />
        ) : (
          <span
            className="inline-flex h-10 w-10 flex-none items-center justify-center rounded-v-pill bg-v-fg-05 font-ui font-semibold text-[13px] leading-none text-v-fg-body"
            aria-hidden="true"
          >
            {initials}
          </span>
        )}
        <div className="min-w-0">
          <p className="m-0 font-ui font-semibold text-[14px] leading-tight text-v-fg">
            {authorName}
          </p>
          {authorRole ? (
            <p className="mt-0.5 font-ui font-normal text-[12px] leading-tight text-v-fg-muted">
              {authorRole}
            </p>
          ) : null}
        </div>
      </div>
    </article>
  )
}
