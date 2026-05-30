'use client'

import { useState } from 'react'

import { PortalDsImageCarousel } from '@/components/portal/invest/PortalDsImageCarousel'
import { AppCard } from '@/components/design-system/app/AppCard'
import { AppNewsDeck } from '@/components/design-system/app/AppNewsDeck'
import {
  AppPortfolioAllocationDonut,
  type AppPortfolioAllocationSlice,
} from '@/components/design-system/app/AppPortfolioAllocationDonut'
import { PortalFeaturedArticleCard } from '@/components/portal/PortalFeaturedArticleCard'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import type { VaultModulePublic } from '@/lib/cms/exclusiveOfferVaultPage'
import { readAllocationSlices } from '@/lib/portal/bundleProductFormat'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { portalArticleRoute } from '@/lib/portal/portalArticleRouting'
import {
  extractBlogArticleSlug,
  readBlogArticles,
  readCarouselItems,
  readListItems,
  readMarketingCardItems,
  readPerformanceChartValues,
  readQuoteBlock,
  readTransactionRows,
  readVideoItems,
} from '@/lib/portal/vaultModulePortalFormat'
import { getYouTubeVideoIdFromUrl } from '@/lib/youtubeEmbed'
import { cn } from '@/lib/utils'

function SectionTitle({ title, action }: { title: string; action?: React.ReactNode }) {
  if (action) {
    return (
      <div className="ofd-section__head">
        <h2 className="ofd-section__title">{title}</h2>
        {action}
      </div>
    )
  }
  return <h2 className="ofd-section__title">{title}</h2>
}

function articleMeta(readingTime: number, publishedAt: string | null): string {
  if (publishedAt) {
    try {
      return formatArticleDateShort(new Date(publishedAt), PORTAL_CONTENT_LOCALE)
    } catch {
      /* ignore */
    }
  }
  return `${Math.max(1, Math.round(readingTime))} min read`
}

export function PortalVaultBlogALaUne({ mod }: { mod: VaultModulePublic }) {
  const articles = readBlogArticles(mod.content)
  if (!articles.length) return null

  const title =
    typeof mod.content.title === 'string' && mod.content.title.trim()
      ? mod.content.title.trim()
      : 'Featured stories'

  return (
    <>
      <SectionTitle
        title={title}
        action={
          <a href={PORTAL_ROUTES.academy} className="ofd-section__see">
            View all articles
          </a>
        }
      />
      <AppNewsDeck columns={articles.length > 1 ? 2 : undefined}>
        {articles.map((article) => {
          const slug = extractBlogArticleSlug(article.slug)
          return (
            <PortalFeaturedArticleCard
              key={article.id}
              href={portalArticleRoute(slug)}
              title={article.title}
              coverUrl={article.coverUrl || undefined}
              meta={articleMeta(article.readingTime, article.publishedAt)}
            />
          )
        })}
      </AppNewsDeck>
    </>
  )
}

export function PortalVaultMediaCarousel({ mod }: { mod: VaultModulePublic }) {
  const items = readCarouselItems(mod.content)
  if (!items.length) return null

  const moduleTitle =
    typeof mod.content.moduleTitle === 'string' ? mod.content.moduleTitle.trim() : ''
  const description =
    typeof mod.content.description === 'string' ? mod.content.description.trim() : ''
  const photos = items.map((item) => item.url)
  const ariaLabel =
    moduleTitle ||
    items.find((item) => item.alt?.trim())?.alt?.trim() ||
    'Galerie photos'

  return (
    <>
      {moduleTitle ? <SectionTitle title={moduleTitle} /> : null}
      {description ? <p className="overview__body">{description}</p> : null}
      <PortalDsImageCarousel photos={photos} variant="gallery" ariaLabel={ariaLabel} />
    </>
  )
}

export function PortalVaultAllocation({ mod }: { mod: VaultModulePublic }) {
  const slices: AppPortfolioAllocationSlice[] = readAllocationSlices(mod.content)
  if (!slices.length) return null

  const title = typeof mod.content.title === 'string' ? mod.content.title.trim() : 'Allocation'
  const intro = typeof mod.content.introText === 'string' ? mod.content.introText.trim() : ''

  return (
    <AppPortfolioAllocationDonut
      title={title}
      subtitle={intro || undefined}
      slices={slices}
      centerValue={String(slices.length)}
      centerLabel={slices.length === 1 ? 'asset' : 'assets'}
    />
  )
}

export function PortalVaultPerformanceChart({ mod }: { mod: VaultModulePublic }) {
  const title = typeof mod.content.title === 'string' ? mod.content.title.trim() : 'Performance'
  const values = readPerformanceChartValues(mod.content)
  const first = values[0] ?? 0
  const last = values[values.length - 1] ?? 0
  const positive = values.length < 2 || last >= first

  return (
    <section className="cfd-perf">
      <div className="cfd-perf__head">
        <h2 className="cfd-perf__title">{title}</h2>
        {values.length >= 2 ? (
          <div className="cfd-perf__delta">
            <span className="cfd-perf__delta-k">Trend</span>
            <span className={cn('cfd-perf__delta-v', positive ? 'text-v-green' : 'text-v-error')}>
              {positive ? '+' : '−'}
              {Math.abs(last - first).toLocaleString('en-US', { maximumFractionDigits: 1 })}
            </span>
          </div>
        ) : null}
      </div>
      <div className="cfd-perf__plot">
        {values.length >= 2 ? (
          <div className={cn('h-[200px]', positive ? 'text-v-green' : 'text-v-error')}>
            <PortalPerformanceChart values={values} height={200} tone="light" showEndpoint />
          </div>
        ) : (
          <p className="m-0 py-12 text-center font-ui text-[14px] text-v-fg-muted">
            Performance data will appear here once available.
          </p>
        )}
      </div>
    </section>
  )
}

export function PortalVaultTransactions({ mod }: { mod: VaultModulePublic }) {
  const title =
    typeof mod.content.title === 'string' ? mod.content.title.trim() : 'Latest transactions'
  const rows = readTransactionRows(mod.content)
  if (!rows.length) return null

  return (
    <>
      <SectionTitle title={title} />
      <div className="docs">
        {rows.map((row, i) => (
          <div className="row" key={`${row.label}-${i}`}>
            <div className="row__avatar" aria-hidden="true">
              <KalaiIcon name="exchange" size={16} />
            </div>
            <div className="row__body">
              <h3 className="row__title">{row.label}</h3>
              {row.date ? <p className="row__sub">{row.date}</p> : null}
            </div>
            {row.amount ? (
              <div className="row__trailing">
                <span className="font-ui text-[15px] font-semibold text-v-fg">{row.amount}</span>
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </>
  )
}

function PortalMarketingCard({
  item,
  portrait,
}: {
  item: ReturnType<typeof readMarketingCardItems>[number]
  portrait?: boolean
}) {
  const inner = (
    <AppCard className="overflow-hidden !p-0">
      <div
        className={cn('w-full overflow-hidden bg-v-fg-05', portrait ? 'aspect-[3/4]' : 'aspect-[16/10]')}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={item.imageUrl} alt="" className="h-full w-full object-cover" loading="lazy" />
      </div>
      {item.title || item.description ? (
        <div className="space-y-2 p-5">
          {item.title ? (
            <h3 className="m-0 font-ui text-[18px] font-semibold leading-snug text-v-fg">{item.title}</h3>
          ) : null}
          {item.description ? (
            <p className="m-0 font-ui text-[15px] leading-relaxed text-v-fg-body">{item.description}</p>
          ) : null}
        </div>
      ) : null}
    </AppCard>
  )

  if (item.href) {
    return (
      <a href={item.href} className="block no-underline transition-opacity hover:opacity-95">
        {inner}
      </a>
    )
  }
  return inner
}

export function PortalVaultMarketingLargePortrait({ mod }: { mod: VaultModulePublic }) {
  const title = typeof mod.content.title === 'string' ? mod.content.title.trim() : ''
  const imageUrl =
    typeof mod.content.imageUrl === 'string'
      ? mod.content.imageUrl.trim()
      : typeof mod.content.imageAssetPath === 'string'
        ? mod.content.imageAssetPath.trim()
        : ''
  if (!imageUrl && !title) return null

  return (
    <>
      {title ? <SectionTitle title={title} /> : null}
      {imageUrl ? (
        <AppCard className="overflow-hidden !p-0">
          <div className="aspect-[3/4] w-full max-w-md overflow-hidden bg-v-fg-05">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={imageUrl} alt="" className="h-full w-full object-cover" loading="lazy" />
          </div>
        </AppCard>
      ) : null}
    </>
  )
}

export function PortalVaultMarketingCards({
  mod,
  portrait,
}: {
  mod: VaultModulePublic
  portrait?: boolean
}) {
  const title = typeof mod.content.title === 'string' ? mod.content.title.trim() : ''
  const items = readMarketingCardItems(mod.content)
  if (!items.length && !title) return null

  return (
    <>
      {title ? <SectionTitle title={title} /> : null}
      <div
        className={cn(
          'grid gap-4',
          portrait ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1 md:grid-cols-2',
        )}
      >
        {items.map((item, i) => (
          <PortalMarketingCard key={`${item.imageUrl}-${i}`} item={item} portrait={portrait} />
        ))}
      </div>
    </>
  )
}

function PortalVideoCard({ item }: { item: ReturnType<typeof readVideoItems>[number] }) {
  const [open, setOpen] = useState(false)
  const videoId = getYouTubeVideoIdFromUrl(item.videoUrl)

  return (
    <AppCard className="overflow-hidden !p-0">
      {open && videoId ? (
        <div className="aspect-video w-full">
          <iframe
            title={item.title || 'Video'}
            src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
            className="h-full w-full border-0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      ) : (
        <button
          type="button"
          className="group relative block w-full text-left"
          onClick={() => setOpen(true)}
          aria-label={item.title ? `Play: ${item.title}` : 'Play video'}
        >
          <div className="relative aspect-video w-full overflow-hidden bg-v-fg-05">
            {item.posterImageUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={item.posterImageUrl}
                alt=""
                className="h-full w-full object-cover transition group-hover:opacity-95"
                loading="lazy"
              />
            ) : null}
            <span className="absolute inset-0 flex items-center justify-center bg-black/25 transition group-hover:bg-black/35">
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white/90 text-v-fg">
                <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" aria-hidden>
                  <path d="M8 5v14l11-7z" />
                </svg>
              </span>
            </span>
          </div>
        </button>
      )}
      {item.title || item.date ? (
        <div className="space-y-1 p-5">
          {item.title ? (
            <h3 className="m-0 font-ui text-[18px] font-semibold text-v-fg">{item.title}</h3>
          ) : null}
          {item.date ? <p className="m-0 font-ui text-[13px] text-v-fg-muted">{item.date}</p> : null}
        </div>
      ) : null}
    </AppCard>
  )
}

export function PortalVaultVideos({ mod }: { mod: VaultModulePublic }) {
  const title = typeof mod.content.title === 'string' ? mod.content.title.trim() : 'Videos'
  const items = readVideoItems(mod.content)
  if (!items.length) return null

  return (
    <>
      <SectionTitle title={title} />
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((item, i) => (
          <PortalVideoCard key={`${item.videoUrl}-${i}`} item={item} />
        ))}
      </div>
    </>
  )
}

export function PortalVaultVirtualVisualization({ mod }: { mod: VaultModulePublic }) {
  const title =
    typeof mod.content.moduleTitle === 'string' ? mod.content.moduleTitle.trim() : 'Virtual tour'
  const description =
    typeof mod.content.description === 'string' ? mod.content.description.trim() : ''
  const url =
    typeof mod.content.visualizationUrl === 'string' ? mod.content.visualizationUrl.trim() : ''
  if (!url && !description) return null

  return (
    <>
      <SectionTitle title={title} />
      {description ? <p className="overview__body">{description}</p> : null}
      {url ? (
        <div className="map-card">
          <div className="map map--embed">
            <iframe
              title={title}
              src={url}
              className="map__iframe"
              style={{ minHeight: 420 }}
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            />
          </div>
        </div>
      ) : null}
    </>
  )
}

export function PortalVaultQuote({ mod }: { mod: VaultModulePublic }) {
  const { text, author } = readQuoteBlock(mod.content)
  if (!text) return null
  return (
    <blockquote className="overview m-0 border-l-4 border-v-terracotta pl-5">
      <p className="overview__body m-0 italic">&ldquo;{text}&rdquo;</p>
      {author ? (
        <footer className="mt-3 font-ui text-[14px] font-semibold text-v-fg-muted">— {author}</footer>
      ) : null}
    </blockquote>
  )
}

export function PortalVaultBulletList({ mod }: { mod: VaultModulePublic }) {
  const items = readListItems(mod.content)
  if (!items.length) return null
  return (
    <ul className="overview__body m-0 list-disc space-y-2 pl-5">
      {items.map((it, i) => (
        <li key={i}>{it}</li>
      ))}
    </ul>
  )
}

export function PortalVaultNumberedList({ mod }: { mod: VaultModulePublic }) {
  const items = readListItems(mod.content)
  if (!items.length) return null
  return (
    <ol className="overview__body m-0 list-decimal space-y-2 pl-5">
      {items.map((it, i) => (
        <li key={i}>{it}</li>
      ))}
    </ol>
  )
}
