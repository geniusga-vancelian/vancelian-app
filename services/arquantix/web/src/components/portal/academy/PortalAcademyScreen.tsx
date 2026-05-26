'use client'

import { AppEyebrow } from '@/components/design-system/app/AppEyebrow'
import { AppNewsDeck } from '@/components/design-system/app/AppNewsDeck'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalFeaturedArticleCard } from '@/components/portal/PortalFeaturedArticleCard'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalAcademySkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalResearchSection } from '@/components/portal/markets/PortalResearchSection'
import { PortalAcademyFeaturedHero } from '@/components/portal/academy/PortalAcademyFeaturedHero'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import type { PortalAcademyArticle, PortalAcademyHubPayload } from '@/lib/portal/academyHubTypes'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { Container } from '@/components/ui/Container'

const ACADEMY_CACHE_KEY = 'portal:academy:v1'

function newsCardMeta(item: PortalAcademyArticle): string {
  if (item.publishedAt) {
    return formatArticleDateShort(new Date(item.publishedAt), 'fr')
  }
  return `${item.readingTime} min read`
}

export function PortalAcademyScreen() {
  const { data, loading, error, refresh } = usePortalCachedScreen<PortalAcademyHubPayload>({
    cacheKey: ACADEMY_CACHE_KEY,
    url: '/api/portal/academy',
    ttlMs: 120_000,
    errorMessage: 'Unable to load Academy.',
  })

  if (loading && !data) return <PortalAcademySkeleton />

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 font-ui text-[15px] text-v-error">{error}</p>
        <button
          type="button"
          onClick={() => void refresh()}
          className="v-text-link border-0 bg-transparent p-0 font-ui text-[14px]"
        >
          Retry
        </button>
      </Container>
    )
  }

  if (!data) return null

  const hasHero = Boolean(data.featured)
  const hasNews = data.news.length > 0

  return (
    <PortalPageContainer>
      <PortalDashboardLayout hideSupport>
        <PortalReveal index={0}>
          <header className="flex flex-col gap-2">
            <AppEyebrow>Academy</AppEyebrow>
            <h1 className="m-0 font-ui text-[28px] font-semibold tracking-v-tight text-v-fg">
              Academy
            </h1>
            <p className="m-0 max-w-2xl font-ui text-[15px] leading-relaxed text-v-fg-muted">
              News, research and educational articles — all in one place.
            </p>
          </header>
        </PortalReveal>

        {hasHero && data.featured ? (
          <PortalReveal index={1}>
            <PortalAcademyFeaturedHero
              featured={data.featured}
              highlighted={data.highlighted}
            />
          </PortalReveal>
        ) : null}

        {hasNews ? (
          <PortalReveal index={2}>
            <section className="flex w-full flex-col gap-3">
              <AppSectionHeader title="Latest News" />
              <AppNewsDeck columns={3}>
                {data.news.map((item) => (
                  <PortalFeaturedArticleCard
                    key={item.id}
                    href={item.href}
                    title={item.title}
                    coverUrl={item.coverUrl}
                    meta={newsCardMeta(item)}
                  />
                ))}
              </AppNewsDeck>
            </section>
          </PortalReveal>
        ) : null}

        {data.research.length > 0 ? (
          <PortalReveal index={3}>
            <PortalResearchSection items={data.research} deckColumns={3} />
          </PortalReveal>
        ) : null}

        {!hasHero && !hasNews && data.research.length === 0 ? (
          <PortalReveal index={1}>
            <div className="card-simple flex min-h-[180px] items-center justify-center p-8 text-center">
              <p className="m-0 font-ui text-[14px] leading-relaxed text-v-fg-muted">
                No articles available yet.
              </p>
            </div>
          </PortalReveal>
        ) : null}
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
