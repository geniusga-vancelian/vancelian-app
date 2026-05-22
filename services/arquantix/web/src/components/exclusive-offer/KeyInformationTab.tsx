'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

import {
  SIMPLE_MARKDOWN_MODULE_TITLE_TYPO,
  VAULT_MODULE_CTA_CLASS,
  vaultStripeClass,
} from '@/components/design-system'
import { cn } from '@/lib/utils'
import {
  getActiveLocaleFromPathname,
  localizePublicInternalHref,
  shouldSkipLocalizePublicHref,
} from '@/lib/i18n/publicLocalizedRouting'
import type { KeyInformationRow } from '@/lib/cms/exclusiveOfferTypes'

export type { KeyInformationRow } from '@/lib/cms/exclusiveOfferTypes'

export type KeyInformationTabProps = {
  /** Titre du module (centré). Absent = pas de ligne de titre. */
  title?: string
  rows: KeyInformationRow[]
  className?: string
  /** CTA pill sous le tableau — affiché seulement si les deux sont définis. */
  ctaLabel?: string
  ctaHref?: string
}

/**
 * Bloc « Key information » — tokens Vancelian DS (cartes, typo Inter, zébrage v-card / v-bg-warm).
 */
export function KeyInformationTab({
  title,
  rows,
  className,
  ctaLabel,
  ctaHref,
}: KeyInformationTabProps) {
  const pathname = usePathname() ?? ''
  const loc = getActiveLocaleFromPathname(pathname)
  if (!rows.length) {
    return null
  }

  const titleTrim = title?.trim() ?? ''
  const showCta = Boolean(ctaHref?.trim() && ctaLabel?.trim())
  const resolvedCtaHref = (() => {
    const raw = ctaHref?.trim()
    if (!raw) return raw
    if (shouldSkipLocalizePublicHref(raw)) return raw
    return localizePublicInternalHref(raw, loc)
  })()

  return (
    <div className={cn('w-full px-0 py-6 md:py-8', className)}>
      {titleTrim ? (
        <h2 className={SIMPLE_MARKDOWN_MODULE_TITLE_TYPO}>{titleTrim}</h2>
      ) : null}

      <div className={cn('overflow-hidden rounded-v-card border border-v-fg-10', titleTrim ? 'mt-10' : '')}>
        {rows.map((row, i) => (
          <div
            key={`${row.label}-${i}`}
            className={cn(
              'flex flex-row items-center justify-between gap-6 px-5 py-4 md:px-8 md:py-5',
              vaultStripeClass(i),
            )}
          >
            <span className="font-ui text-[16px] font-semibold leading-snug text-v-fg md:text-[18px]">
              {row.label}
            </span>
            <span className="text-right font-ui text-[16px] font-normal leading-snug text-v-fg-body md:text-[18px]">
              {row.value}
            </span>
          </div>
        ))}
      </div>

      {showCta ? (
        <div className="mt-8 flex justify-center">
          <Link href={resolvedCtaHref!} className={VAULT_MODULE_CTA_CLASS}>
            {ctaLabel}
          </Link>
        </div>
      ) : null}
    </div>
  )
}
