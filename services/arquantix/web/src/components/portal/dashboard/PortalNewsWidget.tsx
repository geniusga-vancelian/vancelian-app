'use client'

import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import { Carousel, CarouselContent, CarouselItem } from '@/components/ui/carousel'
import type { PortalNewsItem, PortalNewsWidgetData } from '@/lib/portal/parseTop10NewsWidget'
import { cn } from '@/lib/utils'

type Props = {
  data: PortalNewsWidgetData
  minReadLabel?: string
}

function NewsCard({ item, minReadLabel }: { item: PortalNewsItem; minReadLabel: string }) {
  const meta = item.publishedDate?.trim() || `${item.readingTime} ${minReadLabel}`

  return (
    <Link
      href={item.href}
      className="group block overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle transition-shadow duration-v-fast hover:shadow-v-medium"
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
    </Link>
  )
}

/** Module « Vancelian News » — carrousel horizontal (équivalent Flutter `BlogALaUne`). */
export function PortalNewsWidget({ data, minReadLabel = 'min read' }: Props) {
  if (data.items.length === 0) return null

  const multi = data.items.length > 1
  const headerHref = data.headerHref ?? '/blog'

  return (
    <section className="flex flex-col gap-3">
      {headerHref ? (
        <Link
          href={headerHref}
          className="group flex items-center justify-between gap-2 no-underline"
        >
          <h2 className="m-0 font-ui text-[18px] font-semibold text-v-fg">{data.title}</h2>
          <ChevronRight
            className="h-5 w-5 text-v-fg-muted transition-transform duration-v-fast group-hover:translate-x-0.5 group-hover:text-v-fg"
            aria-hidden
          />
        </Link>
      ) : (
        <h2 className="m-0 font-ui text-[18px] font-semibold text-v-fg">{data.title}</h2>
      )}

      <Carousel
        opts={{
          align: 'start',
          containScroll: 'trimSnaps',
          dragFree: true,
        }}
        className="w-full min-w-0"
      >
        <CarouselContent className={cn(multi ? '-ml-3' : '!ml-0')}>
          {data.items.map((item) => (
            <CarouselItem
              key={item.id}
              className={cn(
                'min-h-0 shrink-0',
                multi ? 'basis-[92%] pl-3 sm:basis-[72%] lg:basis-[340px]' : '!basis-full !pl-0',
              )}
            >
              <NewsCard item={item} minReadLabel={minReadLabel} />
            </CarouselItem>
          ))}
        </CarouselContent>
      </Carousel>
    </section>
  )
}
