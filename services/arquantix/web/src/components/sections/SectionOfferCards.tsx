'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'
import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/button'
import { SectionFigmaBlockHeader } from '@/components/sections/SectionFigmaBlockHeader'
import { VOfferCard } from '@/components/design-system/vancelian/VOfferCard'
import {
  getActiveLocaleFromPathname,
  localizePublicInternalHref,
} from '@/lib/i18n/publicLocalizedRouting'

export interface OfferCardItem {
  href?: string
  ariaLabel?: string
  centerText?: string
  barTitle?: string
  barSubtitle?: string
  barRate?: string
  coverMediaId?: string
  coverMediaUrl?: string
  hoverVideoMediaId?: string
  hoverVideoMediaUrl?: string
}

export interface SectionOfferCardsProps {
  eyebrow?: string
  title?: string
  description?: string
  viewAllButtonText?: string
  viewAllButtonHref?: string
  items?: OfferCardItem[]
}

export function SectionOfferCards({
  eyebrow,
  title,
  description,
  viewAllButtonText,
  viewAllButtonHref,
  items = [],
}: SectionOfferCardsProps) {
  const pathname = usePathname() ?? ''
  const locale = getActiveLocaleFromPathname(pathname)
  const cards = items.filter((i) => i.barTitle?.trim() || i.centerText?.trim())
  const hasHeader = Boolean(eyebrow?.trim() || title?.trim() || description?.trim())
  const viewAllHref = viewAllButtonHref?.trim()
    ? localizePublicInternalHref(viewAllButtonHref.trim(), locale)
    : undefined

  if (cards.length === 0 && !hasHeader) return null

  return (
    <section className="w-full bg-v-bg py-24 lg:py-32">
      <Container>
        <div className="flex flex-col items-center gap-10">
          {hasHeader ? (
            <div
              data-v-scroll-fade
              className="flex max-w-[720px] flex-col items-center gap-6 text-center"
            >
              <SectionFigmaBlockHeader
                eyebrow={eyebrow}
                title={title}
                description={description}
                titleSize="module"
              />
              {viewAllHref && viewAllButtonText?.trim() ? (
                <Button asChild variant="secondary" size="default">
                  <a href={viewAllHref}>
                    <span>{viewAllButtonText}</span>
                    <span aria-hidden>→</span>
                  </a>
                </Button>
              ) : null}
            </div>
          ) : null}

          {cards.length > 0 ? (
            <div
              data-v-scroll-fade
              className="grid w-full grid-cols-1 items-center gap-5 md:grid-cols-[1fr_1.1fr_1fr]"
            >
              {cards.map((item, i) => {
                const href = item.href?.trim()
                  ? localizePublicInternalHref(item.href.trim(), locale)
                  : '#'
                return (
                  <VOfferCard
                    key={i}
                    href={href}
                    ariaLabel={item.ariaLabel}
                    centerText={item.centerText}
                    barTitle={item.barTitle}
                    barSubtitle={item.barSubtitle}
                    barRate={item.barRate}
                    coverImageUrl={item.coverMediaUrl}
                    hoverVideoUrl={item.hoverVideoMediaUrl}
                    className={i === 1 ? 'md:z-[2]' : undefined}
                  />
                )
              })}
            </div>
          ) : null}
        </div>
      </Container>
    </section>
  )
}
