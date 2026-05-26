'use client'

import { AppNewsDeck } from '@/components/design-system/app/AppNewsDeck'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalFeaturedArticleCard } from '@/components/portal/PortalFeaturedArticleCard'
import type { PortalNewsItem, PortalNewsWidgetData } from '@/lib/portal/parseTop10NewsWidget'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  data: PortalNewsWidgetData
  minReadLabel?: string
}

function resolveItemMeta(item: PortalNewsItem, minReadLabel: string): string {
  if (item.publishedDate?.trim()) return item.publishedDate.trim()
  return `${item.readingTime} ${minReadLabel}`
}

/** Blog à la une — grille 1→2 colonnes DS preview/26 (Flash & Actu). */
export function PortalNewsWidget({ data, minReadLabel = 'min' }: Props) {
  if (data.items.length === 0) return null

  const headerHref = data.headerHref ?? PORTAL_ROUTES.academy

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title={data.title} moreHref={headerHref} moreLabel="View all articles" />
      <AppNewsDeck>
        {data.items.map((item) => (
          <PortalFeaturedArticleCard
            key={item.id}
            href={item.href}
            title={item.title}
            coverUrl={item.coverUrl}
            meta={resolveItemMeta(item, minReadLabel)}
          />
        ))}
      </AppNewsDeck>
    </section>
  )
}
