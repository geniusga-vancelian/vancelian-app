'use client'

import { useMemo, useState } from 'react'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import {
  PortalSettingsCard,
  PortalSettingsRow,
} from '@/components/portal/profile/PortalProfileUi'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import type { PortalMarketsNewsItem } from '@/lib/portal/marketsTypes'
import { cn } from '@/lib/utils'

const ALL_TAG = '__all__'

type Props = {
  items: PortalMarketsNewsItem[]
  title?: string
  maxItems?: number
}

function NewsRow({ item }: { item: PortalMarketsNewsItem }) {
  const dateLabel = item.publishedAt
    ? formatArticleDateShort(new Date(item.publishedAt), 'fr')
    : `${item.readingTime} min read`
  const tag = item.tags[0]

  return (
    <PortalSettingsRow
      href={item.href}
      title={item.title}
      subtitle={`${item.authorName} · ${dateLabel}`}
      leading={
        item.coverUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.coverUrl}
            alt=""
            className="h-12 w-12 rounded-v-input object-cover"
          />
        ) : (
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-v-input bg-v-fg-05 font-ui text-[11px] text-v-fg-muted">
            News
          </span>
        )
      }
      trailing={
        tag ? (
          <span className="rounded-v-tag border border-v-fg-10 px-2 py-0.5 font-ui text-[11px] font-medium uppercase tracking-v-wide text-v-fg-muted">
            {tag}
          </span>
        ) : undefined
      }
    />
  )
}

export function PortalMarketsNewsSection({
  items,
  title = 'Latest News',
  maxItems = 5,
}: Props) {
  const [selectedTag, setSelectedTag] = useState(ALL_TAG)

  const tagOptions = useMemo(() => {
    const labels = new Set<string>()
    for (const item of items) {
      for (const tag of item.tags) {
        const normalized = tag.trim()
        if (normalized) labels.add(normalized)
      }
    }
    const sorted = [...labels].sort((a, b) => a.localeCompare(b))
    return [{ id: ALL_TAG, label: 'Tous' }, ...sorted.map((label) => ({ id: label, label }))]
  }, [items])

  const cappedItems = useMemo(
    () => items.slice(0, Math.min(Math.max(maxItems, 1), 10)),
    [items, maxItems],
  )

  const visibleItems = useMemo(() => {
    if (selectedTag === ALL_TAG) return cappedItems
    return cappedItems.filter((item) => item.tags.some((tag) => tag.trim() === selectedTag))
  }, [cappedItems, selectedTag])

  if (items.length === 0) return null

  const showTabs = tagOptions.length > 1

  return (
    <section className="flex flex-col gap-4">
      <PortalSectionHeading title={title} href="/blog" />

      {showTabs ? (
        <div className="flex flex-wrap gap-2">
          {tagOptions.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => setSelectedTag(option.id)}
              className={cn(
                'rounded-v-pill border px-3 py-1.5 font-ui text-[13px] font-medium transition-colors duration-v-fast',
                selectedTag === option.id
                  ? 'border-v-fg bg-v-fg text-white'
                  : 'border-v-fg-10 bg-v-card text-v-fg-body hover:border-v-fg-20',
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      ) : null}

      {visibleItems.length === 0 ? (
        <div className="rounded-v-card border border-v-fg-10 bg-v-card p-5 text-center">
          <p className="m-0 font-ui text-[14px] text-v-fg-muted">No articles in this category.</p>
        </div>
      ) : (
        <PortalSettingsCard>
          {visibleItems.map((item) => (
            <NewsRow key={`${selectedTag}-${item.id}`} item={item} />
          ))}
        </PortalSettingsCard>
      )}
    </section>
  )
}
