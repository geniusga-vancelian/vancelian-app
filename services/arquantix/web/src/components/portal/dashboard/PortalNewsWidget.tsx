'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalModuleTitleLink } from '@/components/portal/PortalModuleTitleLink'
import type { PortalNewsItem, PortalNewsWidgetData } from '@/lib/portal/parseTop10NewsWidget'

type Props = {
  data: PortalNewsWidgetData
  minReadLabel?: string
}

function NewsCard({ item, minReadLabel }: { item: PortalNewsItem; minReadLabel: string }) {
  const meta = item.publishedDate?.trim() || `${item.readingTime} ${minReadLabel}`

  return (
    <PortalNavLink
      href={item.href}
      className="group block h-full overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle transition-shadow duration-v-fast hover:shadow-v-medium"
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
            Vancelian
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
        <p className="mt-2 mb-0 font-ui text-[12px] text-v-fg-muted">{meta}</p>
      </div>
    </PortalNavLink>
  )
}

/** Module « Vancelian News » — grille responsive 1 / 2 colonnes (équivalent Flutter `BlogALaUne`). */
export function PortalNewsWidget({ data, minReadLabel = 'min read' }: Props) {
  if (data.items.length === 0) return null

  const headerHref = data.headerHref ?? '/blog'

  return (
    <section className="flex flex-col gap-3">
      {headerHref ? (
        <PortalModuleTitleLink href={headerHref} title={data.title} />
      ) : (
        <h2 className="m-0 font-ui text-[18px] font-semibold text-v-fg">{data.title}</h2>
      )}

      <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2">
        {data.items.map((item) => (
          <li key={item.id} className="min-w-0">
            <NewsCard item={item} minReadLabel={minReadLabel} />
          </li>
        ))}
      </ul>
    </section>
  )
}
