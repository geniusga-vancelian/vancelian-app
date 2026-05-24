'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import type { PortalResearchItem } from '@/lib/portal/marketsTypes'

type Props = {
  items: PortalResearchItem[]
  title?: string
}

function ResearchCard({ item }: { item: PortalResearchItem }) {
  return (
    <PortalNavLink
      href={item.href}
      className="group block h-full overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle no-underline transition-shadow duration-v-fast hover:shadow-v-medium"
    >
      <div className="relative aspect-[16/10] w-full overflow-hidden bg-v-fg-05">
        {item.coverUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.coverUrl}
            alt=""
            className="h-full w-full object-cover transition-transform duration-v-slow group-hover:scale-[1.02]"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center font-ui text-[13px] text-v-fg-muted">
            Research
          </div>
        )}
        {item.tag ? (
          <span className="absolute left-3 top-3 rounded-v-tag bg-white/95 px-2 py-0.5 font-ui text-[11px] font-medium uppercase tracking-v-wide text-v-fg">
            {item.tag}
          </span>
        ) : null}
      </div>
      <div className="p-4">
        <h3 className="m-0 line-clamp-3 font-ui text-[16px] font-semibold leading-snug text-v-fg">
          {item.title}
        </h3>
        <p className="mt-2 mb-0 font-ui text-[12px] text-v-fg-muted">{item.readingTime} min read</p>
      </div>
    </PortalNavLink>
  )
}

export function PortalResearchSection({ items, title = 'Research' }: Props) {
  if (items.length === 0) return null

  return (
    <section className="flex flex-col gap-4">
      <PortalSectionHeading title={title} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {items.map((item) => (
          <ResearchCard key={item.id} item={item} />
        ))}
      </div>
    </section>
  )
}
