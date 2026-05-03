'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { SIMPLE_MARKDOWN_MODULE_TITLE_TYPO } from '@/components/design-system'
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
 * Bloc « Key information » : fond module blanc, titre centré, zébrage blanc / gris clair (#F5F5F5).
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
    <div
      className={cn(
        'w-full bg-white px-0 py-6 md:py-8',
        className,
      )}
    >
      {titleTrim ? (
        <h2 className={SIMPLE_MARKDOWN_MODULE_TITLE_TYPO}>{titleTrim}</h2>
      ) : null}

      <div className={cn('overflow-hidden', titleTrim ? 'mt-16' : '')}>
        {rows.map((row, i) => (
          <div
            key={`${row.label}-${i}`}
            className={cn(
              'flex flex-row items-center justify-between gap-6 px-5 py-4 md:px-8 md:py-5',
              i % 2 === 0 ? 'bg-white' : 'bg-[#F5F5F5]',
            )}
          >
            <span className="font-['Avenir:Heavy',sans-serif] text-[18px] leading-snug text-black">
              {row.label}
            </span>
            <span className="text-right font-['Avenir:Roman',sans-serif] text-[18px] font-normal leading-snug text-black">
              {row.value}
            </span>
          </div>
        ))}
      </div>

      {showCta ? (
        <div className="mt-8 flex justify-center">
          <Link
            href={resolvedCtaHref!}
            className="inline-flex min-h-[44px] items-center justify-center rounded-full bg-black px-10 py-3 font-['Avenir:Heavy',sans-serif] text-xs uppercase tracking-wider text-white transition-opacity hover:opacity-90"
          >
            {ctaLabel}
          </Link>
        </div>
      ) : null}
    </div>
  )
}
