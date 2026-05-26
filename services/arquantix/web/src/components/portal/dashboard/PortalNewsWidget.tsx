'use client'

import { AppActuCard } from '@/components/design-system/app/AppActuCard'
import { AppFlashCard } from '@/components/design-system/app/AppFlashCard'
import { AppNewsDeck } from '@/components/design-system/app/AppNewsDeck'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import type { PortalNewsItem, PortalNewsWidgetData } from '@/lib/portal/parseTop10NewsWidget'

type Props = {
  data: PortalNewsWidgetData
  minReadLabel?: string
}

function resolveItemMeta(item: PortalNewsItem, minReadLabel: string): string {
  if (item.publishedDate?.trim()) return item.publishedDate.trim()
  return `${item.readingTime} ${minReadLabel}`
}

function NewsItemCard({
  item,
  minReadLabel,
}: {
  item: PortalNewsItem
  minReadLabel: string
}) {
  const meta = resolveItemMeta(item, minReadLabel)
  const linkProps = {
    href: item.href,
    title: item.title,
    meta,
    LinkComponent: PortalNavLink,
  }

  if (item.coverUrl?.trim()) {
    return <AppActuCard {...linkProps} imageUrl={item.coverUrl.trim()} />
  }

  return <AppFlashCard {...linkProps} />
}

/** Blog à la une — deck horizontal DS preview/26 (Flash & Actu). */
export function PortalNewsWidget({ data, minReadLabel = 'min' }: Props) {
  if (data.items.length === 0) return null

  const headerHref = data.headerHref ?? '/blog'

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title={data.title} moreHref={headerHref} moreLabel="Voir tout" />
      <AppNewsDeck>
        {data.items.map((item) => (
          <NewsItemCard key={item.id} item={item} minReadLabel={minReadLabel} />
        ))}
      </AppNewsDeck>
    </section>
  )
}
