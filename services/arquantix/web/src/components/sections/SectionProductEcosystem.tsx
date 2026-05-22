'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'
import { Container } from '@/components/ui/Container'
import { SectionFigmaBlockHeader } from '@/components/sections/SectionFigmaBlockHeader'
import { VProductCard } from '@/components/design-system/vancelian/VProductCard'
import {
  getActiveLocaleFromPathname,
  localizePublicInternalHref,
} from '@/lib/i18n/publicLocalizedRouting'

export interface ProductEcosystemItem {
  iconName?: string
  title?: string
  description?: string
  features?: Array<{ text: string; iconName?: string }>
  linkText?: string
  linkHref?: string
}

export interface SectionProductEcosystemProps {
  eyebrow?: string
  title?: string
  description?: string
  items?: ProductEcosystemItem[]
}

/** Grille écosystème produit (DS `product-card` × 3). */
export function SectionProductEcosystem({
  eyebrow,
  title,
  description,
  items = [],
}: SectionProductEcosystemProps) {
  const pathname = usePathname() ?? ''
  const locale = getActiveLocaleFromPathname(pathname)
  const cards = items.filter((i) => i.title?.trim())
  const hasHeader = Boolean(eyebrow?.trim() || title?.trim() || description?.trim())
  if (cards.length === 0 && !hasHeader) return null

  return (
    <section className="w-full bg-v-bg py-24 lg:py-32">
      <Container>
        {hasHeader ? (
          <div data-v-scroll-fade>
            <SectionFigmaBlockHeader
              eyebrow={eyebrow}
              title={title}
              description={description}
              titleSize="module"
              className="mx-auto mb-16 max-w-[720px]"
            />
          </div>
        ) : null}

        {cards.length > 0 ? (
          <div data-v-scroll-fade className="grid grid-cols-1 items-stretch gap-6 lg:grid-cols-3">
            {cards.map((item, i) => {
              const href = item.linkHref?.trim()
                ? localizePublicInternalHref(item.linkHref.trim(), locale)
                : undefined
              return (
                <VProductCard
                  key={i}
                  iconName={item.iconName}
                  title={item.title}
                  description={item.description}
                  features={item.features}
                  linkText={item.linkText}
                  linkHref={href}
                />
              )
            })}
          </div>
        ) : null}
      </Container>
    </section>
  )
}
