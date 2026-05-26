'use client'

import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { resolveExclusiveOfferCoverUrl } from '@/lib/portal/exclusiveOfferPlaceholderImages'

export type AppExclusiveOfferChip = {
  key: string
  label: string
  icon?: ReactNode
  /** Affiche une barre de progression dans la pastille (ex. levée de fonds). */
  progressPct?: number
}

export type AppExclusiveOfferCardProps = {
  coverImageUrl?: string | null
  /** Clé stable pour l’image aléatoire si `coverImageUrl` est vide. */
  imageSeed: string
  category: string
  categoryIcon?: ReactNode
  chips?: AppExclusiveOfferChip[]
  title: string
  description?: string
  ctaLabel: string
  href?: string
  onCtaClick?: () => void
  /** Remplace le CTA par défaut (ex. `PortalNavLink`). */
  ctaSlot?: ReactNode
  className?: string
}

function OfferChip({ chip }: { chip: AppExclusiveOfferChip }) {
  const hasProgress = chip.progressPct != null

  return (
    <span
      className={cn(
        'inline-flex h-8 max-w-full items-center gap-1.5 rounded-full bg-white/[0.92] px-3 font-ui text-[12px] font-semibold text-v-fg backdrop-blur-md',
        'tabular-nums whitespace-nowrap',
        hasProgress && 'min-w-0 flex-1 gap-2',
      )}
    >
      {chip.icon ? <span className="inline-flex shrink-0 [&_svg]:h-3.5 [&_svg]:w-3.5">{chip.icon}</span> : null}
      <span className={cn(hasProgress && 'shrink-0')}>{chip.label}</span>
      {hasProgress ? (
        <span className="h-1 min-w-8 flex-1 overflow-hidden rounded-full bg-v-fg-10">
          <span
            className="block h-full rounded-full bg-v-fg"
            style={{ width: `${Math.min(100, Math.max(0, chip.progressPct ?? 0))}%` }}
          />
        </span>
      ) : null}
    </span>
  )
}

function OfferCta({
  label,
  href,
  onClick,
  ctaSlot,
}: {
  label: string
  href?: string
  onClick?: () => void
  ctaSlot?: ReactNode
}) {
  if (ctaSlot) return <>{ctaSlot}</>

  const className =
    'inline-flex h-11 shrink-0 items-center justify-center rounded-full bg-v-fg px-[22px] font-ui text-[14px] font-semibold text-white no-underline transition-opacity hover:opacity-90'

  if (href) {
    return (
      <a href={href} className={className}>
        {label}
      </a>
    )
  }

  return (
    <button type="button" onClick={onClick} className={className}>
      {label}
    </button>
  )
}

/** Carte offre exclusive DS — visuel carré + texte + CTA (`24-card-offre-exclusive`). */
export function AppExclusiveOfferCard({
  coverImageUrl,
  imageSeed,
  category,
  categoryIcon,
  chips = [],
  title,
  description,
  ctaLabel,
  href,
  onCtaClick,
  ctaSlot,
  className,
}: AppExclusiveOfferCardProps) {
  const resolvedCover = resolveExclusiveOfferCoverUrl(coverImageUrl, imageSeed)

  return (
    <article
      className={cn(
        'flex h-full w-full flex-col overflow-hidden rounded-[16px] border border-v-fg-10 bg-white shadow-[0_2px_6px_rgba(26,24,21,0.07)]',
        className,
      )}
    >
      <div className="relative aspect-square overflow-hidden bg-gradient-to-br from-[#B7CFE6] via-[#6C8FB3] to-[#1F3C5C]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={resolvedCover} alt="" className="absolute inset-0 h-full w-full object-cover" />
        <span className="absolute left-4 top-4 inline-flex h-8 max-w-[calc(100%-2rem)] items-center gap-1.5 rounded-full bg-white/[0.92] px-3 font-ui text-[13px] font-semibold text-v-fg backdrop-blur-md">
          {categoryIcon ? (
            <span className="inline-flex shrink-0 [&_svg]:h-3.5 [&_svg]:w-3.5">{categoryIcon}</span>
          ) : null}
          <span className="truncate">{category}</span>
        </span>
        {chips.length > 0 ? (
          <div className="absolute bottom-4 left-4 right-4 flex items-center gap-2">
            {chips.map((chip) => (
              <OfferChip key={chip.key} chip={chip} />
            ))}
          </div>
        ) : null}
      </div>

      <div className="flex items-center gap-4 px-4 pb-5 pt-4">
        <div className="min-w-0 flex-1">
          <h3 className="m-0 line-clamp-2 font-ui text-[17px] font-bold leading-[1.25] text-v-fg">
            {title}
          </h3>
          {description ? (
            <p className="m-0 mt-1 line-clamp-2 font-ui text-[14px] leading-[1.45] text-v-fg-light">
              {description}
            </p>
          ) : null}
        </div>
        <OfferCta label={ctaLabel} href={href} onClick={onCtaClick} ctaSlot={ctaSlot} />
      </div>
    </article>
  )
}
