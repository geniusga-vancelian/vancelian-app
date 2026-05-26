'use client'

import { AppNewsDeck } from '@/components/design-system/app/AppNewsDeck'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalFeaturedArticleCard } from '@/components/portal/PortalFeaturedArticleCard'
import type { PortalResearchItem } from '@/lib/portal/marketsTypes'

type Props = {
  items: PortalResearchItem[]
  title?: string
  headerHref?: string
}

export function PortalResearchSection({
  items,
  title = 'Research',
  headerHref = '/blog',
}: Props) {
  if (items.length === 0) return null

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title={title} moreHref={headerHref} moreLabel="Voir tout" />
      <AppNewsDeck>
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
