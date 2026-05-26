'use client'

import { AppNewsDeck } from '@/components/design-system/app/AppNewsDeck'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalFeaturedArticleCard } from '@/components/portal/PortalFeaturedArticleCard'
import type { PortalResearchItem } from '@/lib/portal/marketsTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  items: PortalResearchItem[]
  title?: string
  headerHref?: string
  deckColumns?: 2 | 3
}

export function PortalResearchSection({
  items,
  title = 'Research',
  headerHref = PORTAL_ROUTES.academy,
  deckColumns = 2,
}: Props) {
  if (items.length === 0) return null

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title={title} moreHref={headerHref} moreLabel="View all articles" />
      <AppNewsDeck columns={deckColumns}>
        {items.map((item) => (
          <PortalFeaturedArticleCard
            key={item.id}
            href={item.href}
            title={item.title}
            coverUrl={item.coverUrl}
            meta={`${item.readingTime} min`}
          />
        ))}
      </AppNewsDeck>
    </section>
  )
}
