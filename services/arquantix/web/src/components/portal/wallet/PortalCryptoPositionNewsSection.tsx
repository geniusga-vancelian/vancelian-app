'use client'

import { useMemo } from 'react'
import { AppNewsStackedList } from '@/components/design-system/app/AppNewsStackedList'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import type { PortalMarketsNewsItem } from '@/lib/portal/marketsTypes'

type Props = {
  items: PortalMarketsNewsItem[]
  maxItems?: number
}

/** Related news — handoff Position.html `NewsStackedList` (`.nsl`). */
export function PortalCryptoPositionNewsSection({ items, maxItems = 3 }: Props) {
  const listItems = useMemo(
    () =>
      items.slice(0, maxItems).map((item) => ({
        id: item.id,
        href: item.href,
        title: item.title,
        authorName: item.authorName,
        dateLabel: item.publishedAt
          ? formatArticleDateShort(new Date(item.publishedAt), 'en')
          : `${item.readingTime} min read`,
        categoryLabel: item.tags[0],
        categoryDot: 'terra' as const,
      })),
    [items, maxItems],
  )

  if (listItems.length === 0) return null

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title="Related news" />
      <AppNewsStackedList
        items={listItems}
        rowVariant="full"
        seamless
        linkComponent={PortalNavLink}
      />
    </section>
  )
}
