'use client'

import { useMemo, useState } from 'react'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import {
  AppNewsStackedList,
  type AppNewsStackedListItem,
} from '@/components/design-system/app/AppNewsStackedList'
import type { PortalMarketsNewsItem } from '@/lib/portal/marketsTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

const ALL_TAG = '__all__'

type Props = {
  items: PortalMarketsNewsItem[]
  title?: string
  maxItems?: number
  /** Désactivé sur la fiche instrument — contenu déjà filtré par actif. */
  showFilters?: boolean
}

function mapNewsItem(item: PortalMarketsNewsItem): AppNewsStackedListItem {
  const dateLabel = item.publishedAt
    ? formatArticleDateShort(new Date(item.publishedAt), 'fr')
    : `${item.readingTime} min read`

  return {
    id: item.id,
    href: item.href,
    title: item.title,
    authorName: item.authorName,
    dateLabel,
  }
}

export function PortalMarketsNewsSection({
  items,
  title = 'Actualités',
  maxItems = 5,
  showFilters = true,
}: Props) {
  const [selectedTag, setSelectedTag] = useState(ALL_TAG)

  const tagOptions = useMemo(() => {
    if (!showFilters) return []
    const labels = new Set<string>()
    for (const item of items) {
      for (const tag of item.tags) {
        const normalized = tag.trim()
        if (normalized) labels.add(normalized)
      }
    }
    const sorted = [...labels].sort((a, b) => a.localeCompare(b))
    return [{ id: ALL_TAG, label: 'Tous' }, ...sorted.map((label) => ({ id: label, label }))]
  }, [items, showFilters])

  const cappedItems = useMemo(
    () => items.slice(0, Math.min(Math.max(maxItems, 1), 10)),
    [items, maxItems],
  )

  const visibleItems = useMemo(() => {
    if (!showFilters || selectedTag === ALL_TAG) return cappedItems
    return cappedItems.filter((item) => item.tags.some((tag) => tag.trim() === selectedTag))
  }, [cappedItems, selectedTag, showFilters])

  const listItems = useMemo(() => visibleItems.map(mapNewsItem), [visibleItems])

  if (items.length === 0) return null

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader
        title={title}
        moreHref={PORTAL_ROUTES.academy}
        moreLabel="Voir toutes les publications"
      />

      <AppNewsStackedList
        items={listItems}
        filters={showFilters && tagOptions.length > 1 ? tagOptions : undefined}
        selectedFilterId={selectedTag}
        onFilterChange={showFilters ? setSelectedTag : undefined}
        rowVariant="text"
        seamless
      />
    </section>
  )
}
